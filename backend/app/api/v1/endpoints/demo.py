"""Demo seed and manual reading injection API — Feature 3 of Emergency Demo Sprint.

Provides:
    POST /demo/seed          — create demo bins, areas, device, calibration & initial readings
    DELETE /demo/reset       — remove demo data (non-destructive to real ops data)
    POST /demo/reading       — inject a manual simulated reading for a demo bin
    GET  /demo/status        — check whether demo data is seeded

Safety guarantee:
    - All demo entities are tagged with bin_id prefix ``BIN-DEMO-`` and area_id ``AREA-DEMO``.
    - The /demo/reset endpoint ONLY deletes rows matching those prefixes.
    - Real operational data (different prefixes) is never touched.

Normative contract: docs/integration.md §4, §6, §7, frontend-guide.md §6.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.bin_latest_state import BinLatestState
from app.models.calibration import SensorConfiguration
from app.models.device import Device
from app.models.device_bin_assignment import DeviceBinAssignment
from app.models.enums import (
    BinStatus,
    BinType,
    DeviceLifecycleState,
    DeviceReportedState,
    FillPriority,
    PredictedPriority,
    SensorHealth,
    TimestampQuality,
)
from app.models.area import Area
from app.models.sensor_reading import SensorReading
from app.models.smart_bin import SmartBin
from app.telemetry.fill_calculation import (
    calculate_fill_percent,
    derive_sensor_health,
    determine_current_priority,
)
from app.models.alert import Alert
from app.models.enums import AlertSeverity, AlertStatus, AlertType

router = APIRouter(prefix="/demo", tags=["demo"])

# ── Constants ─────────────────────────────────────────────────────────────────

DEMO_AREA_ID = "AREA-DEMO-001"
DEMO_BINS: List[Dict[str, Any]] = [
    {
        "bin_id": "BIN-DEMO-001",
        "name": "Main Market North",
        "fill_percent": 92.0,   # HIGH → nearly critical
        "distance_cm": 12.0,
        "description": "High fill — needs collection soon",
    },
    {
        "bin_id": "BIN-DEMO-002",
        "name": "Bus Stand East",
        "fill_percent": 97.5,   # CRITICAL
        "distance_cm": 6.0,
        "description": "Critical fill — immediate action required",
    },
    {
        "bin_id": "BIN-DEMO-003",
        "name": "City Park Entrance",
        "fill_percent": 45.0,   # NORMAL
        "distance_cm": 55.0,
        "description": "Normal fill — no action needed",
    },
    {
        "bin_id": "BIN-DEMO-004",
        "name": "Hospital Road",
        "fill_percent": 78.0,   # MEDIUM
        "distance_cm": 33.0,
        "description": "Medium fill — monitor",
    },
    {
        "bin_id": "BIN-DEMO-005",
        "name": "Old Town Square",
        "fill_percent": None,   # UNKNOWN — simulates sensor fault
        "distance_cm": None,
        "description": "Sensor fault — no valid reading",
    },
]

# Calibration constants for all demo bins:
# empty_distance_cm=100, full_distance_cm=5  ⟹ span=95 cm
DEMO_EMPTY_CM = Decimal("100.00")
DEMO_FULL_CM = Decimal("5.00")


# ── Pydantic shapes ───────────────────────────────────────────────────────────

class SeedResponse(BaseModel):
    seeded: bool
    bins_created: int
    readings_inserted: int
    alerts_created: int
    message: str


class ResetResponse(BaseModel):
    deleted_bins: int
    deleted_devices: int
    deleted_areas: int
    message: str


class ManualReadingRequest(BaseModel):
    bin_id: str = Field(..., description="Demo bin_id string e.g. BIN-DEMO-001")
    distance_cm: Optional[float] = Field(None, ge=1.0, le=400.0, description="Ultrasonic distance reading in cm")
    weight_kg: Optional[float] = Field(None, ge=0.0, description="Load cell weight in kg (optional)")
    temperature_c: Optional[float] = Field(None, description="Ambient temperature °C (optional)")
    humidity_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Humidity % (optional)")
    battery_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Battery % (optional)")


class ManualReadingResponse(BaseModel):
    reading_id: uuid.UUID
    bin_id: str
    fill_percent: Optional[float] = None
    priority: str
    sensor_health: str
    message: str


class DemoStatusResponse(BaseModel):
    seeded: bool
    bin_count: int
    reading_count: int
    bins: List[Dict[str, Any]]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_or_create_demo_area(db: Session) -> Area:
    area = db.query(Area).filter(Area.area_id == DEMO_AREA_ID).first()
    if area is None:
        area = Area(
            id=uuid.uuid4(),
            area_id=DEMO_AREA_ID,
            name="Demo Zone",
            boundary=None,
            active=True,
        )
        db.add(area)
        db.flush()
    return area


def _get_or_create_demo_device(db: Session, suffix: str) -> Device:
    device_id_str = f"ESP32-DEMO-{suffix}"
    device = db.query(Device).filter(Device.device_id == device_id_str).first()
    if device is None:
        device = Device(
            id=uuid.uuid4(),
            device_id=device_id_str,
            lifecycle_state=DeviceLifecycleState.ACTIVE,
            reported_state=DeviceReportedState.ONLINE,
            sensor_health=SensorHealth.OK,
        )
        db.add(device)
        db.flush()
    return device


def _ensure_calibration(db: Session, bin_obj: SmartBin) -> SensorConfiguration:
    calib = (
        db.query(SensorConfiguration)
        .filter(SensorConfiguration.bin_id == bin_obj.id)
        .order_by(SensorConfiguration.calibration_version.desc())
        .first()
    )
    if calib is None:
        calib = SensorConfiguration(
            id=uuid.uuid4(),
            bin_id=bin_obj.id,
            calibration_version=1,
            empty_distance_cm=DEMO_EMPTY_CM,
            full_distance_cm=DEMO_FULL_CM,
            sampling_interval_seconds=60,
            reason="Demo calibration — empty=100cm, full=5cm",
        )
        db.add(calib)
        db.flush()
    return calib


def _insert_reading(
    db: Session,
    bin_obj: SmartBin,
    device: Device,
    calib: SensorConfiguration,
    distance_cm: Optional[float],
    weight_kg: Optional[float] = None,
    temperature_c: Optional[float] = None,
    humidity_percent: Optional[float] = None,
    battery_percent: Optional[float] = None,
    offset_minutes: int = 0,
) -> SensorReading:
    """Insert one SensorReading and update bin_latest_state."""
    boot_id = uuid.UUID("00000000-dead-beef-0000-000000000001")
    seq = int(datetime.now(timezone.utc).timestamp() * 1000) + offset_minutes
    now = datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)

    dist_dec = Decimal(str(distance_cm)) if distance_cm is not None else None

    fill_percent = calculate_fill_percent(
        distance_cm,
        float(calib.empty_distance_cm),
        float(calib.full_distance_cm),
    )
    sensor_faults: List[str] = [] if distance_cm is not None else ["ULTRASONIC_TIMEOUT"]
    sensor_health = derive_sensor_health(distance_cm, sensor_faults)
    current_priority = determine_current_priority(fill_percent)

    reading = SensorReading(
        id=uuid.uuid4(),
        bin_id=bin_obj.id,
        device_id=device.id,
        timestamp=now,
        received_at=now,
        timestamp_quality=TimestampQuality.DEVICE_SYNCED,
        boot_id=boot_id,
        sequence=seq,
        message_id=f"demo-{uuid.uuid4().hex[:8]}",
        calibration_version=calib.calibration_version,
        distance_cm=dist_dec,
        fill_percent=fill_percent,
        weight_kg=Decimal(str(weight_kg)) if weight_kg is not None else None,
        temperature_c=Decimal(str(temperature_c)) if temperature_c is not None else None,
        humidity_percent=Decimal(str(humidity_percent)) if humidity_percent is not None else None,
        battery_percent=Decimal(str(battery_percent)) if battery_percent is not None else None,
        raw_hx711_count=None,
        rssi_dbm=-65,
        sensor_health=sensor_health,
        sensor_faults=sensor_faults,
        quality_flags=[],
        eligible_for_operations=True,
        eligibility_reason=None,
    )
    db.add(reading)
    db.flush()

    # Upsert bin_latest_state
    state = db.query(BinLatestState).filter(BinLatestState.bin_id == bin_obj.id).first()
    if state is None:
        state = BinLatestState(
            bin_id=bin_obj.id,
            latest_reading_id=reading.id,
            latest_event_at=now,
            fill_percent=fill_percent,
            weight_kg=reading.weight_kg,
            priority=current_priority,
            predicted_priority=PredictedPriority.NONE,
            sensor_health=sensor_health,
            device_reported_state=DeviceReportedState.ONLINE,
            is_stale=False,
        )
        db.add(state)
    else:
        state.latest_reading_id = reading.id
        state.latest_event_at = now
        state.fill_percent = fill_percent
        state.weight_kg = reading.weight_kg
        state.priority = current_priority
        state.sensor_health = sensor_health
        state.device_reported_state = DeviceReportedState.ONLINE
        state.is_stale = False

    db.flush()
    return reading


def _create_demo_alert(
    db: Session,
    bin_obj: SmartBin,
    fill_percent: Optional[Decimal],
    priority: FillPriority,
) -> Optional[Alert]:
    """Create a threshold alert for CRITICAL or HIGH priority demo bins."""
    if priority not in (FillPriority.CRITICAL, FillPriority.HIGH):
        return None
    alert_id = f"ALERT-DEMO-{bin_obj.bin_id}"
    existing = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if existing:
        return existing

    if priority == FillPriority.CRITICAL:
        severity = AlertSeverity.CRITICAL
        msg = f"Bin {bin_obj.bin_id} ({bin_obj.name}) is CRITICAL at {fill_percent}% fill. Immediate collection required."
    else:
        severity = AlertSeverity.WARNING
        msg = f"Bin {bin_obj.bin_id} ({bin_obj.name}) is HIGH at {fill_percent}% fill. Schedule collection soon."

    alert = Alert(
        id=uuid.uuid4(),
        alert_id=alert_id,
        type=AlertType.BIN_THRESHOLD,
        severity=severity,
        status=AlertStatus.OPEN,
        bin_id=bin_obj.id,
        message=msg,
        details={"fill_percent": str(fill_percent), "priority": priority.value},
    )
    db.add(alert)
    db.flush()
    return alert


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=DemoStatusResponse, summary="Check demo seed state")
def demo_status(db: Session = Depends(get_db)) -> DemoStatusResponse:
    """Return whether demo data is present and a summary."""
    demo_bins = db.query(SmartBin).filter(SmartBin.bin_id.like("BIN-DEMO-%")).all()
    bin_ids = [b.id for b in demo_bins]
    reading_count = 0
    if bin_ids:
        reading_count = db.query(SensorReading).filter(SensorReading.bin_id.in_(bin_ids)).count()

    bin_summaries = []
    for b in demo_bins:
        state = b.latest_state
        bin_summaries.append({
            "bin_id": b.bin_id,
            "name": b.name,
            "fill_percent": float(state.fill_percent) if state and state.fill_percent is not None else None,
            "priority": state.priority.value if state else "UNKNOWN",
        })

    return DemoStatusResponse(
        seeded=len(demo_bins) > 0,
        bin_count=len(demo_bins),
        reading_count=reading_count,
        bins=bin_summaries,
    )


@router.post("/seed", response_model=SeedResponse, summary="Seed demo bins, devices, calibration, and readings")
def seed_demo(db: Session = Depends(get_db)) -> SeedResponse:
    """Idempotent: safe to call multiple times. Skips already-existing bins.

    Creates:
    - 1 demo area (``AREA-DEMO-001``)
    - 5 demo smart bins (``BIN-DEMO-001`` … ``BIN-DEMO-005``)
    - 1 demo ESP32 device per bin
    - Calibration (empty=100 cm, full=5 cm) per bin
    - 5 historical readings per bin at 15-minute intervals
    - CRITICAL/HIGH threshold alerts for qualifying bins
    """
    area = _get_or_create_demo_area(db)
    bins_created = 0
    readings_inserted = 0
    alerts_created = 0

    for spec in DEMO_BINS:
        bid = spec["bin_id"]
        existing_bin = db.query(SmartBin).filter(SmartBin.bin_id == bid).first()
        if existing_bin is not None:
            continue  # idempotent skip

        bin_obj = SmartBin(
            id=uuid.uuid4(),
            bin_id=bid,
            name=spec["name"],
            bin_type=BinType.MUNICIPAL,
            status=BinStatus.ACTIVE,
            location="POINT(78.9629 20.5937)",  # geographic center of India — placeholder
            area_id=area.id,
            capacity_kg=Decimal("100.00"),
            nominal_full_bin_weight_kg=Decimal("80.00"),
            warning_threshold_pct=Decimal("70.00"),
            critical_threshold_pct=Decimal("95.00"),
        )
        db.add(bin_obj)
        db.flush()
        bins_created += 1

        suffix = bid.split("-")[-1]  # "001", "002", …
        device = _get_or_create_demo_device(db, suffix)

        # Assign device to bin (no existing assignment)
        assignment = DeviceBinAssignment(
            id=uuid.uuid4(),
            device_id=device.id,
            bin_id=bin_obj.id,
            started_at=datetime.now(timezone.utc) - timedelta(days=30),
            ended_at=None,
        )
        db.add(assignment)
        db.flush()

        calib = _ensure_calibration(db, bin_obj)

        dist = spec["distance_cm"]
        # Insert 5 historical readings (most recent last, 15-min apart)
        for i in range(4, -1, -1):
            # Slightly vary distance to make chart interesting
            if dist is not None:
                varied = dist + (i * 2.0)  # older readings were slightly less full
            else:
                varied = None
            r = _insert_reading(
                db, bin_obj, device, calib,
                distance_cm=varied,
                offset_minutes=i * 15,
            )
            readings_inserted += 1

        # Create threshold alerts
        state = db.query(BinLatestState).filter(BinLatestState.bin_id == bin_obj.id).first()
        priority = state.priority if state else FillPriority.UNKNOWN
        fill = state.fill_percent if state else None
        al = _create_demo_alert(db, bin_obj, fill, priority)
        if al is not None:
            alerts_created += 1

    db.commit()

    return SeedResponse(
        seeded=True,
        bins_created=bins_created,
        readings_inserted=readings_inserted,
        alerts_created=alerts_created,
        message=(
            f"Demo data seeded: {bins_created} bins, {readings_inserted} readings, {alerts_created} alerts. "
            "Call GET /api/v1/bins to view them."
        ),
    )


@router.delete("/reset", response_model=ResetResponse, summary="Remove all demo data (non-destructive to real data)")
def reset_demo(db: Session = Depends(get_db)) -> ResetResponse:
    """Delete ONLY rows tagged with DEMO prefixes.

    Real operational data is never touched.
    """
    # Alerts first (FK to bins)
    demo_bins = db.query(SmartBin).filter(SmartBin.bin_id.like("BIN-DEMO-%")).all()
    bin_ids = [b.id for b in demo_bins]

    if bin_ids:
        db.query(Alert).filter(Alert.bin_id.in_(bin_ids)).delete(synchronize_session=False)
        db.query(BinLatestState).filter(BinLatestState.bin_id.in_(bin_ids)).delete(synchronize_session=False)
        db.query(SensorReading).filter(SensorReading.bin_id.in_(bin_ids)).delete(synchronize_session=False)

    # Assignments & calibrations cascade via FK on bin delete, but do it explicitly for safety
    if bin_ids:
        db.query(DeviceBinAssignment).filter(DeviceBinAssignment.bin_id.in_(bin_ids)).delete(synchronize_session=False)
        db.query(SensorConfiguration).filter(SensorConfiguration.bin_id.in_(bin_ids)).delete(synchronize_session=False)

    bin_count = len(bin_ids)
    for b in demo_bins:
        db.delete(b)

    # Demo devices
    demo_devices = db.query(Device).filter(Device.device_id.like("ESP32-DEMO-%")).all()
    device_count = len(demo_devices)
    for d in demo_devices:
        db.delete(d)

    # Demo areas
    demo_areas = db.query(Area).filter(Area.area_id.like("AREA-DEMO-%")).all()
    area_count = len(demo_areas)
    for a in demo_areas:
        db.delete(a)

    db.commit()

    return ResetResponse(
        deleted_bins=bin_count,
        deleted_devices=device_count,
        deleted_areas=area_count,
        message=f"Demo reset complete. Deleted {bin_count} bins, {device_count} devices, {area_count} areas.",
    )


@router.post("/reading", response_model=ManualReadingResponse, summary="Inject a manual simulated reading")
def inject_manual_reading(
    body: ManualReadingRequest,
    db: Session = Depends(get_db),
) -> ManualReadingResponse:
    """Submit a simulated sensor reading for any demo bin.

    Uses the authoritative calibration and fill calculation pipeline.
    Updates ``bin_latest_state`` exactly as real MQTT telemetry does.
    ``distance_cm`` drives fill calculation. Omit it to simulate a sensor fault (UNKNOWN priority).
    """
    if not body.bin_id.startswith("BIN-DEMO-"):
        raise HTTPException(
            400,
            detail="Manual readings can only be injected for demo bins (BIN-DEMO-* prefix). "
                   "Use the MQTT telemetry pipeline for real hardware.",
        )

    bin_obj = (
        db.query(SmartBin)
        .filter(SmartBin.bin_id == body.bin_id)
        .first()
    )
    if bin_obj is None:
        raise HTTPException(
            404,
            detail=f"Bin '{body.bin_id}' not found. Call POST /api/v1/demo/seed first.",
        )

    calib = (
        db.query(SensorConfiguration)
        .filter(SensorConfiguration.bin_id == bin_obj.id)
        .order_by(SensorConfiguration.calibration_version.desc())
        .first()
    )
    if calib is None:
        raise HTTPException(500, detail="No calibration found for demo bin. Re-seed the demo.")

    # Resolve device from assignment
    assignment = (
        db.query(DeviceBinAssignment)
        .filter(DeviceBinAssignment.bin_id == bin_obj.id, DeviceBinAssignment.ended_at.is_(None))
        .first()
    )
    if assignment is None:
        raise HTTPException(500, detail="Demo bin has no active device assignment. Re-seed the demo.")

    device = db.query(Device).filter(Device.id == assignment.device_id).first()
    if device is None:
        raise HTTPException(500, detail="Demo device not found. Re-seed the demo.")

    reading = _insert_reading(
        db, bin_obj, device, calib,
        distance_cm=body.distance_cm,
        weight_kg=body.weight_kg,
        temperature_c=body.temperature_c,
        humidity_percent=body.humidity_percent,
        battery_percent=body.battery_percent,
    )
    db.commit()

    state = db.query(BinLatestState).filter(BinLatestState.bin_id == bin_obj.id).first()
    fill = float(state.fill_percent) if state and state.fill_percent is not None else None
    prio = state.priority.value if state else FillPriority.UNKNOWN.value
    health = state.sensor_health.value if state else SensorHealth.OK.value

    return ManualReadingResponse(
        reading_id=reading.id,
        bin_id=body.bin_id,
        fill_percent=fill,
        priority=prio,
        sensor_health=health,
        message=f"Reading injected for {body.bin_id}. Priority is now {prio}.",
    )

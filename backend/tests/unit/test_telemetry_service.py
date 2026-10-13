"""Unit tests for transactional telemetry persistence, deduplication, and quarantine.

Normative source: docs/integration.md §2, §3, §4, §11, §15; docs/testing.md §2.
"""
from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.area import Area
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
    SensorHealth,
    UserRole,
)
from app.models.rejected_telemetry_event import RejectedTelemetryEvent
from app.models.sensor_reading import SensorReading
from app.models.smart_bin import SmartBin
from app.models.user import User
from app.telemetry.schemas import ProcessingOutcome
from app.telemetry.service import process_status_message, process_telemetry_message


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database session for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def setup_standard_entities(session: Session, device_id: str = "ESP32-A123", bin_status: BinStatus = BinStatus.ACTIVE):
    """Seed test database with an admin user, area, bin, device, active assignment, and calibration."""
    admin = User(
        id=uuid.uuid4(),
        firebase_uid=f"fb_{uuid.uuid4().hex[:8]}",
        email=f"admin_{uuid.uuid4().hex[:6]}@swm-ics.test",
        role=UserRole.SUPER_ADMIN,
    )
    session.add(admin)

    area = Area(
        id=uuid.uuid4(),
        area_id=f"AREA-{uuid.uuid4().hex[:6]}",
        name="Central District",
    )
    session.add(area)

    bin_obj = SmartBin(
        id=uuid.uuid4(),
        bin_id="BIN-001",
        name="Main Square Bin",
        bin_type=BinType.MUNICIPAL,
        status=bin_status,
        location="POINT(75.8577 22.7196)",
        area_id=area.id,
        capacity_kg=Decimal("150.00"),
        warning_threshold_pct=Decimal("70.00"),
        critical_threshold_pct=Decimal("95.00"),
    )
    session.add(bin_obj)

    device = Device(
        id=uuid.uuid4(),
        device_id=device_id,
        lifecycle_state=DeviceLifecycleState.ACTIVE,
        reported_state=DeviceReportedState.ONLINE,
        firmware_version="0.1.0",
    )
    session.add(device)

    assignment = DeviceBinAssignment(
        id=uuid.uuid4(),
        device_id=device.id,
        bin_id=bin_obj.id,
        assigned_by=admin.id,
        reason="Test initial assignment",
    )
    session.add(assignment)

    calib = SensorConfiguration(
        id=uuid.uuid4(),
        bin_id=bin_obj.id,
        calibration_version=1,
        empty_distance_cm=Decimal("100.00"),
        full_distance_cm=Decimal("10.00"),
        sampling_interval_seconds=60,
        created_by=admin.id,
    )
    session.add(calib)

    session.commit()
    return device, bin_obj, calib


def make_payload_bytes(
    device_id: str,
    boot_id: str,
    sequence: int,
    distance_cm: float | None = 55.0,
    timestamp: str | None = "2026-10-12T10:30:00Z",
    time_synced: bool = True,
    weight_kg: float | None = 25.0,
) -> bytes:
    msg = {
        "schema_version": 1,
        "message_id": f"{device_id}:{boot_id}:{sequence}",
        "device_id": device_id,
        "boot_id": boot_id,
        "sequence": sequence,
        "timestamp": timestamp,
        "time_synced": time_synced,
        "firmware_version": "0.1.0",
        "measurements": {
            "distance_cm": distance_cm,
            "weight_kg": weight_kg,
            "temperature_c": 28.0,
            "humidity_percent": 50.0,
        },
        "health": {
            "reported_state": "ONLINE",
            "sensor_faults": [],
            "rssi_dbm": -60,
            "battery_percent": 90.0,
        },
    }
    return json.dumps(msg).encode("utf-8")


def test_valid_telemetry_creates_reading_and_latest_state(db_session):
    device, bin_obj, calib = setup_standard_entities(db_session, "ESP32-A123")
    boot_id = str(uuid.uuid4())
    payload = make_payload_bytes("ESP32-A123", boot_id, 0, distance_cm=55.0)
    topic = "smartwaste/device/ESP32-A123/telemetry"

    res = process_telemetry_message(db_session, topic, payload)

    assert res.outcome == ProcessingOutcome.ACCEPTED
    assert res.reading_id is not None
    assert res.fill_percent == Decimal("50.00")
    assert res.current_priority == FillPriority.NORMAL

    # Verify sensor_readings table
    reading = db_session.query(SensorReading).filter(SensorReading.id == res.reading_id).first()
    assert reading is not None
    assert reading.device_id == device.id
    assert reading.bin_id == bin_obj.id
    assert reading.calibration_version == 1
    assert reading.eligible_for_operations is True

    # Verify bin_latest_state table
    latest = db_session.query(BinLatestState).filter(BinLatestState.bin_id == bin_obj.id).first()
    assert latest is not None
    assert latest.latest_reading_id == reading.id
    assert latest.fill_percent == Decimal("50.00")
    assert latest.current_priority == FillPriority.NORMAL


def test_duplicate_delivery_is_idempotent(db_session):
    setup_standard_entities(db_session, "ESP32-A123")
    boot_id = str(uuid.uuid4())
    payload = make_payload_bytes("ESP32-A123", boot_id, 0, distance_cm=55.0)
    topic = "smartwaste/device/ESP32-A123/telemetry"

    # First publication
    res1 = process_telemetry_message(db_session, topic, payload)
    assert res1.outcome == ProcessingOutcome.ACCEPTED

    # Duplicate delivery with same (device_id, boot_id, sequence)
    res2 = process_telemetry_message(db_session, topic, payload)
    assert res2.outcome == ProcessingOutcome.DUPLICATE
    assert res2.reason_code == "DUPLICATE_MESSAGE"

    # Ensure no second row was inserted
    readings_count = db_session.query(SensorReading).count()
    assert readings_count == 1


def test_unknown_device_is_quarantined(db_session):
    boot_id = str(uuid.uuid4())
    payload = make_payload_bytes("ESP32-UNREGISTERED", boot_id, 0)
    topic = "smartwaste/device/ESP32-UNREGISTERED/telemetry"

    res = process_telemetry_message(db_session, topic, payload)
    assert res.outcome == ProcessingOutcome.REJECTED
    assert res.reason_code == "UNKNOWN_DEVICE"

    # Verify quarantine table
    q_event = db_session.query(RejectedTelemetryEvent).filter(
        RejectedTelemetryEvent.device_id == "ESP32-UNREGISTERED"
    ).first()
    assert q_event is not None
    assert q_event.reason_code == "UNKNOWN_DEVICE"


def test_missing_active_assignment_is_quarantined(db_session):
    # Register device without an active assignment
    device = Device(
        id=uuid.uuid4(),
        device_id="ESP32-ORPHAN",
        lifecycle_state=DeviceLifecycleState.UNPROVISIONED,
        reported_state=DeviceReportedState.ONLINE,
    )
    db_session.add(device)
    db_session.commit()

    boot_id = str(uuid.uuid4())
    payload = make_payload_bytes("ESP32-ORPHAN", boot_id, 0)
    topic = "smartwaste/device/ESP32-ORPHAN/telemetry"

    res = process_telemetry_message(db_session, topic, payload)
    assert res.outcome == ProcessingOutcome.REJECTED
    assert res.reason_code == "ASSIGNMENT_CONFLICT"

    q_event = db_session.query(RejectedTelemetryEvent).filter(
        RejectedTelemetryEvent.device_id == "ESP32-ORPHAN"
    ).first()
    assert q_event is not None
    assert q_event.reason_code == "ASSIGNMENT_CONFLICT"


def test_missing_calibration_preserves_none_fill(db_session):
    admin = User(
        id=uuid.uuid4(),
        firebase_uid="fb_admin_test_nocalib",
        email="admin_nocalib@swm-ics.test",
        role=UserRole.SUPER_ADMIN,
    )
    db_session.add(admin)
    area = Area(id=uuid.uuid4(), area_id="AREA-NOCALIB", name="Area NoCalib")
    db_session.add(area)
    bin_obj = SmartBin(
        id=uuid.uuid4(),
        bin_id="BIN-NOCALIB",
        name="No Calib Bin",
        bin_type=BinType.MUNICIPAL,
        status=BinStatus.ACTIVE,
        location="POINT(75.8577 22.7196)",
        area_id=area.id,
        capacity_kg=Decimal("150.00"),
        warning_threshold_pct=Decimal("70.00"),
        critical_threshold_pct=Decimal("95.00"),
    )
    db_session.add(bin_obj)
    device = Device(
        id=uuid.uuid4(),
        device_id="ESP32-NOCALIB",
        lifecycle_state=DeviceLifecycleState.ACTIVE,
        reported_state=DeviceReportedState.ONLINE,
    )
    db_session.add(device)
    assignment = DeviceBinAssignment(
        id=uuid.uuid4(),
        device_id=device.id,
        bin_id=bin_obj.id,
        assigned_by=admin.id,
    )
    db_session.add(assignment)
    db_session.commit()

    boot_id = str(uuid.uuid4())
    payload = make_payload_bytes("ESP32-NOCALIB", boot_id, 0, distance_cm=55.0)
    topic = "smartwaste/device/ESP32-NOCALIB/telemetry"

    res = process_telemetry_message(db_session, topic, payload)
    assert res.outcome == ProcessingOutcome.ACCEPTED
    assert res.fill_percent is None
    assert res.current_priority == FillPriority.UNKNOWN

    reading = db_session.query(SensorReading).filter(SensorReading.id == res.reading_id).first()
    assert reading.fill_percent is None
    assert "CALIBRATION_MISSING" in reading.quality_flags


def test_draft_bin_readings_not_eligible_for_operations(db_session):
    device, bin_obj, calib = setup_standard_entities(db_session, "ESP32-DRAFT", bin_status=BinStatus.DRAFT)
    boot_id = str(uuid.uuid4())
    payload = make_payload_bytes("ESP32-DRAFT", boot_id, 0, distance_cm=55.0)
    topic = "smartwaste/device/ESP32-DRAFT/telemetry"

    res = process_telemetry_message(db_session, topic, payload)
    assert res.outcome == ProcessingOutcome.ACCEPTED

    reading = db_session.query(SensorReading).filter(SensorReading.id == res.reading_id).first()
    assert reading.eligible_for_operations is False
    assert reading.eligibility_reason == "BIN_NOT_ACTIVE"

    # Ensure draft bin did NOT create or update bin_latest_state
    latest = db_session.query(BinLatestState).filter(BinLatestState.bin_id == bin_obj.id).first()
    assert latest is None


def test_out_of_order_message_does_not_overwrite_latest_state(db_session):
    setup_standard_entities(db_session, "ESP32-A123")
    boot_id = str(uuid.uuid4())
    topic = "smartwaste/device/ESP32-A123/telemetry"

    # Message 1 (newer event): timestamp 10:40:00Z, distance 10 (100% fill)
    payload_new = make_payload_bytes("ESP32-A123", boot_id, 1, distance_cm=10.0, timestamp="2026-10-12T10:40:00Z")
    res1 = process_telemetry_message(db_session, topic, payload_new)
    assert res1.outcome == ProcessingOutcome.ACCEPTED

    latest1 = db_session.query(BinLatestState).first()
    assert latest1.fill_percent == Decimal("100.00")

    # Message 2 (delayed older event): timestamp 10:30:00Z, distance 55 (50% fill)
    payload_old = make_payload_bytes("ESP32-A123", boot_id, 2, distance_cm=55.0, timestamp="2026-10-12T10:30:00Z")
    res2 = process_telemetry_message(db_session, topic, payload_old)
    assert res2.outcome == ProcessingOutcome.ACCEPTED

    # The raw reading was stored:
    assert db_session.query(SensorReading).count() == 2

    # But latest state was NOT overwritten by the older event:
    latest2 = db_session.query(BinLatestState).first()
    assert latest2.fill_percent == Decimal("100.00")
    assert latest2.latest_reading_id == res1.reading_id


def test_status_message_updates_device_state(db_session):
    device, bin_obj, calib = setup_standard_entities(db_session, "ESP32-A123")
    boot_id = str(uuid.uuid4())
    status_payload = {
        "schema_version": 1,
        "device_id": "ESP32-A123",
        "boot_id": boot_id,
        "timestamp": "2026-10-12T11:00:00Z",
        "event": "MAINTENANCE",
        "firmware_version": "0.1.1",
        "sensor_faults": ["LOAD_CELL_NOT_READY"],
        "rssi_dbm": -55,
    }
    payload_bytes = json.dumps(status_payload).encode("utf-8")
    topic = "smartwaste/device/ESP32-A123/status"

    res = process_status_message(db_session, topic, payload_bytes)
    assert res.outcome == ProcessingOutcome.ACCEPTED

    # Check updated device
    d = db_session.query(Device).filter(Device.id == device.id).first()
    assert d.reported_state == DeviceReportedState.MAINTENANCE
    assert d.firmware_version == "0.1.1"
    assert d.last_rssi_dbm == -55
    assert d.sensor_health == SensorHealth.DEGRADED

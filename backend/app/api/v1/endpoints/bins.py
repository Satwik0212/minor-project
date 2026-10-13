"""Smart Bin Monitoring REST API — Feature 1 of Emergency Demo Sprint.

Provides:
    GET  /bins            — paginated list with latest state joined
    GET  /bins/{bin_id}   — single bin detail with state and last 20 readings
    GET  /bins/summary    — aggregate counts per priority (dashboard cards)

Normative contract: docs/integration.md §7, frontend-guide.md.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.bin_latest_state import BinLatestState
from app.models.enums import BinStatus, FillPriority, SensorHealth
from app.models.sensor_reading import SensorReading
from app.models.smart_bin import SmartBin

router = APIRouter(prefix="/bins", tags=["bins"])


# ── Pydantic response shapes ──────────────────────────────────────────────────

class AreaBrief(BaseModel):
    area_id: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class LatestStateOut(BaseModel):
    fill_percent: Optional[float] = None
    weight_kg: Optional[float] = None
    priority: str = "UNKNOWN"
    predicted_priority: str = "NONE"
    sensor_health: str = "OK"
    device_reported_state: str = "OFFLINE"
    is_stale: bool = False
    latest_event_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BinListItem(BaseModel):
    id: uuid.UUID
    bin_id: str
    name: str
    bin_type: str
    status: str
    area: Optional[AreaBrief] = None
    capacity_kg: float
    warning_threshold_pct: float
    critical_threshold_pct: float
    is_simulated: bool = True           # always True for demo bins
    latest_state: Optional[LatestStateOut] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReadingBrief(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    distance_cm: Optional[float] = None
    fill_percent: Optional[float] = None
    weight_kg: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    battery_percent: Optional[float] = None
    sensor_health: str
    sensor_faults: List[Any] = []
    quality_flags: List[Any] = []
    eligible_for_operations: bool = True

    model_config = ConfigDict(from_attributes=True)


class BinDetail(BinListItem):
    recent_readings: List[ReadingBrief] = []


class BinSummary(BaseModel):
    total: int
    by_priority: Dict[str, int]
    by_status: Dict[str, int]
    active_count: int
    simulated_count: int


class BinListResponse(BaseModel):
    items: List[BinListItem]
    total: int
    page: int
    page_size: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _latest_state_out(state: Optional[BinLatestState]) -> Optional[LatestStateOut]:
    if state is None:
        return None
    return LatestStateOut(
        fill_percent=float(state.fill_percent) if state.fill_percent is not None else None,
        weight_kg=float(state.weight_kg) if state.weight_kg is not None else None,
        priority=state.priority.value if hasattr(state.priority, "value") else str(state.priority),
        predicted_priority=state.predicted_priority.value if hasattr(state.predicted_priority, "value") else str(state.predicted_priority),
        sensor_health=state.sensor_health.value if hasattr(state.sensor_health, "value") else str(state.sensor_health),
        device_reported_state=state.device_reported_state.value if hasattr(state.device_reported_state, "value") else str(state.device_reported_state),
        is_stale=bool(state.is_stale),
        latest_event_at=state.latest_event_at,
        updated_at=state.updated_at,
    )


def _bin_list_item(b: SmartBin) -> BinListItem:
    area_brief = None
    if b.area is not None:
        area_brief = AreaBrief(area_id=b.area.area_id, name=b.area.name)
    return BinListItem(
        id=b.id,
        bin_id=b.bin_id,
        name=b.name,
        bin_type=b.bin_type.value if hasattr(b.bin_type, "value") else str(b.bin_type),
        status=b.status.value if hasattr(b.status, "value") else str(b.status),
        area=area_brief,
        capacity_kg=float(b.capacity_kg),
        warning_threshold_pct=float(b.warning_threshold_pct),
        critical_threshold_pct=float(b.critical_threshold_pct),
        is_simulated=b.bin_id.startswith("BIN-DEMO-"),
        latest_state=_latest_state_out(b.latest_state),
        created_at=b.created_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=BinSummary, summary="Bin aggregate summary for dashboard cards")
def get_bin_summary(db: Session = Depends(get_db)) -> BinSummary:
    """Return total counts broken down by priority and status.

    This is the data source for dashboard KPI cards.
    """
    bins = (
        db.query(SmartBin)
        .options(joinedload(SmartBin.latest_state))
        .all()
    )
    by_priority: Dict[str, int] = {p.value: 0 for p in FillPriority}
    by_status: Dict[str, int] = {s.value: 0 for s in BinStatus}
    active_count = 0

    for b in bins:
        status_val = b.status.value if hasattr(b.status, "value") else str(b.status)
        by_status[status_val] = by_status.get(status_val, 0) + 1
        if b.status == BinStatus.ACTIVE:
            active_count += 1
        state = b.latest_state
        if state is not None:
            p_val = state.priority.value if hasattr(state.priority, "value") else str(state.priority)
        else:
            p_val = FillPriority.UNKNOWN.value
        by_priority[p_val] = by_priority.get(p_val, 0) + 1

    return BinSummary(
        total=len(bins),
        by_priority=by_priority,
        by_status=by_status,
        active_count=active_count,
        simulated_count=sum(1 for b in bins if b.bin_id.startswith("BIN-DEMO-")),
    )


@router.get("", response_model=BinListResponse, summary="List all bins with latest state")
def list_bins(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    priority: Optional[str] = Query(None, description="Filter by FillPriority value"),
    status: Optional[str] = Query(None, description="Filter by BinStatus value"),
    area_id: Optional[str] = Query(None, description="Filter by area area_id string"),
    db: Session = Depends(get_db),
) -> BinListResponse:
    """Return paginated list of bins with joined latest state.

    Supports filtering by priority, status, and area. Used by Smart Bin
    Monitoring dashboard (Feature 1) and Collection Priority view (Feature 2).
    """
    q = db.query(SmartBin).options(
        joinedload(SmartBin.latest_state),
        joinedload(SmartBin.area),
    )

    # Apply filters
    if status:
        try:
            status_enum = BinStatus(status.upper())
            q = q.filter(SmartBin.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status value: {status}")

    if area_id:
        from app.models.area import Area
        q = q.join(Area, SmartBin.area_id == Area.id).filter(Area.area_id == area_id)

    if priority:
        try:
            priority_enum = FillPriority(priority.upper())
            q = q.join(BinLatestState, SmartBin.id == BinLatestState.bin_id).filter(
                BinLatestState.priority == priority_enum
            )
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority value: {priority}")

    total = q.count()
    bins = q.offset((page - 1) * page_size).limit(page_size).all()

    return BinListResponse(
        items=[_bin_list_item(b) for b in bins],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{bin_id}", response_model=BinDetail, summary="Get single bin with recent readings")
def get_bin(bin_id: str, db: Session = Depends(get_db)) -> BinDetail:
    """Return detailed bin info including last 20 sensor readings.

    `bin_id` is the human-readable string identifier (e.g. ``BIN-DEMO-001``),
    not the internal UUID primary key.
    """
    b = (
        db.query(SmartBin)
        .options(joinedload(SmartBin.latest_state), joinedload(SmartBin.area))
        .filter(SmartBin.bin_id == bin_id)
        .first()
    )
    if b is None:
        raise HTTPException(status_code=404, detail=f"Bin '{bin_id}' not found")

    readings = (
        db.query(SensorReading)
        .filter(SensorReading.bin_id == b.id)
        .order_by(desc(SensorReading.timestamp))
        .limit(20)
        .all()
    )

    def _r(r: SensorReading) -> ReadingBrief:
        return ReadingBrief(
            id=r.id,
            timestamp=r.timestamp,
            distance_cm=float(r.distance_cm) if r.distance_cm is not None else None,
            fill_percent=float(r.fill_percent) if r.fill_percent is not None else None,
            weight_kg=float(r.weight_kg) if r.weight_kg is not None else None,
            temperature_c=float(r.temperature_c) if r.temperature_c is not None else None,
            humidity_percent=float(r.humidity_percent) if r.humidity_percent is not None else None,
            battery_percent=float(r.battery_percent) if r.battery_percent is not None else None,
            sensor_health=r.sensor_health.value if hasattr(r.sensor_health, "value") else str(r.sensor_health),
            sensor_faults=list(r.sensor_faults or []),
            quality_flags=list(r.quality_flags or []),
            eligible_for_operations=bool(r.eligible_for_operations),
        )

    item = _bin_list_item(b)
    return BinDetail(
        **item.model_dump(),
        recent_readings=[_r(r) for r in readings],
    )

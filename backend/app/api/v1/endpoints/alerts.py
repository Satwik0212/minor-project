"""Collection Priority & Alerts REST API — Feature 2 of Emergency Demo Sprint.

Provides:
    GET  /alerts                — paginated active/open alerts (filterable)
    GET  /alerts/{alert_id}     — single alert detail
    POST /alerts/{alert_id}/acknowledge — acknowledge an alert
    POST /alerts/{alert_id}/resolve     — resolve an alert
    GET  /collection/priority   — bins sorted by operational priority (Feature 2 core)

Normative contract: docs/integration.md §7, §8, frontend-guide.md.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.alert import Alert
from app.models.bin_latest_state import BinLatestState
from app.models.enums import AlertSeverity, AlertStatus, AlertType, FillPriority
from app.models.smart_bin import SmartBin

router = APIRouter(tags=["alerts"])

# ── Pydantic shapes ───────────────────────────────────────────────────────────

PRIORITY_ORDER = {
    FillPriority.CRITICAL: 0,
    FillPriority.HIGH: 1,
    FillPriority.MEDIUM: 2,
    FillPriority.NORMAL: 3,
    FillPriority.UNKNOWN: 4,
}


class AlertOut(BaseModel):
    id: uuid.UUID
    alert_id: str
    type: str
    severity: str
    status: str
    bin_id: Optional[uuid.UUID] = None
    bin_label: Optional[str] = None       # bin.bin_id for quick display
    message: str
    details: Optional[Any] = None
    opened_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    items: List[AlertOut]
    total: int
    page: int
    page_size: int


class AckResolveResponse(BaseModel):
    alert_id: str
    status: str
    message: str


class PriorityBinItem(BaseModel):
    """Bin row as shown in the Collection Priority view."""
    bin_id: str
    name: str
    area_name: Optional[str] = None
    fill_percent: Optional[float] = None
    priority: str
    sensor_health: str
    device_reported_state: str
    is_stale: bool
    latest_event_at: Optional[datetime] = None
    open_alert_count: int = 0


class PriorityListResponse(BaseModel):
    items: List[PriorityBinItem]
    total: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _alert_out(a: Alert) -> AlertOut:
    bin_label = None
    if a.bin is not None:
        bin_label = a.bin.bin_id
    return AlertOut(
        id=a.id,
        alert_id=a.alert_id,
        type=a.type.value if hasattr(a.type, "value") else str(a.type),
        severity=a.severity.value if hasattr(a.severity, "value") else str(a.severity),
        status=a.status.value if hasattr(a.status, "value") else str(a.status),
        bin_id=a.bin_id,
        bin_label=bin_label,
        message=a.message,
        details=a.details,
        opened_at=a.opened_at,
        resolved_at=a.resolved_at,
    )


# ── Alert endpoints ───────────────────────────────────────────────────────────

alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


@alerts_router.get("", response_model=AlertListResponse, summary="List active alerts")
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="OPEN | ACKNOWLEDGED | RESOLVED | DISMISSED"),
    severity: Optional[str] = Query(None, description="INFO | WARNING | ERROR | CRITICAL"),
    bin_id: Optional[str] = Query(None, description="Filter by bin.bin_id string"),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    """Return paginated alert list ordered by severity desc, then opened_at desc.

    Default filter is OPEN alerts only. Pass ``?status=ALL`` to skip status filter.
    """
    q = db.query(Alert).options(joinedload(Alert.bin))

    if status and status.upper() != "ALL":
        try:
            s_enum = AlertStatus(status.upper())
            q = q.filter(Alert.status == s_enum)
        except ValueError:
            raise HTTPException(400, detail=f"Invalid status: {status}")
    elif not status:
        # Default: OPEN alerts
        q = q.filter(Alert.status == AlertStatus.OPEN)

    if severity:
        try:
            sev_enum = AlertSeverity(severity.upper())
            q = q.filter(Alert.severity == sev_enum)
        except ValueError:
            raise HTTPException(400, detail=f"Invalid severity: {severity}")

    if bin_id:
        q = q.join(SmartBin, Alert.bin_id == SmartBin.id).filter(SmartBin.bin_id == bin_id)

    q = q.order_by(desc(Alert.opened_at))
    total = q.count()
    alerts = q.offset((page - 1) * page_size).limit(page_size).all()

    return AlertListResponse(
        items=[_alert_out(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
    )


@alerts_router.get("/{alert_id}", response_model=AlertOut, summary="Single alert detail")
def get_alert(alert_id: str, db: Session = Depends(get_db)) -> AlertOut:
    a = (
        db.query(Alert)
        .options(joinedload(Alert.bin))
        .filter(Alert.alert_id == alert_id)
        .first()
    )
    if a is None:
        raise HTTPException(404, detail=f"Alert '{alert_id}' not found")
    return _alert_out(a)


@alerts_router.post("/{alert_id}/acknowledge", response_model=AckResolveResponse, summary="Acknowledge an alert")
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)) -> AckResolveResponse:
    a = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if a is None:
        raise HTTPException(404, detail=f"Alert '{alert_id}' not found")
    if a.status not in (AlertStatus.OPEN,):
        raise HTTPException(409, detail=f"Alert is already {a.status.value}, cannot acknowledge")
    a.status = AlertStatus.ACKNOWLEDGED
    db.commit()
    return AckResolveResponse(alert_id=alert_id, status="ACKNOWLEDGED", message="Alert acknowledged")


@alerts_router.post("/{alert_id}/resolve", response_model=AckResolveResponse, summary="Resolve an alert")
def resolve_alert(alert_id: str, db: Session = Depends(get_db)) -> AckResolveResponse:
    a = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if a is None:
        raise HTTPException(404, detail=f"Alert '{alert_id}' not found")
    if a.status == AlertStatus.RESOLVED:
        raise HTTPException(409, detail="Alert is already RESOLVED")
    a.status = AlertStatus.RESOLVED
    a.resolved_at = datetime.now()
    db.commit()
    return AckResolveResponse(alert_id=alert_id, status="RESOLVED", message="Alert resolved")


# ── Collection Priority endpoint ──────────────────────────────────────────────

collection_router = APIRouter(prefix="/collection", tags=["collection"])


@collection_router.get("/priority", response_model=PriorityListResponse, summary="Bins sorted by fill priority")
def get_collection_priority(
    priority: Optional[str] = Query(None, description="Filter by FillPriority (CRITICAL|HIGH|MEDIUM|NORMAL|UNKNOWN)"),
    area_id: Optional[str] = Query(None, description="Filter by area.area_id string"),
    exclude_stale: bool = Query(False, description="Exclude bins with stale readings"),
    db: Session = Depends(get_db),
) -> PriorityListResponse:
    """Return bins ordered by operational priority (CRITICAL first).

    Used by Feature 2: Collection Priority & Alerts view.
    Each row includes fill %, priority band, sensor health, area, and open alert count.
    """
    q = db.query(SmartBin).options(
        joinedload(SmartBin.latest_state),
        joinedload(SmartBin.area),
    )

    if area_id:
        from app.models.area import Area
        q = q.join(Area, SmartBin.area_id == Area.id).filter(Area.area_id == area_id)

    if priority:
        try:
            p_enum = FillPriority(priority.upper())
            q = q.join(BinLatestState, SmartBin.id == BinLatestState.bin_id).filter(
                BinLatestState.priority == p_enum
            )
        except ValueError:
            raise HTTPException(400, detail=f"Invalid priority: {priority}")

    if exclude_stale:
        if priority:  # already joined
            q = q.filter(BinLatestState.is_stale == False)  # noqa: E712
        else:
            q = q.join(BinLatestState, SmartBin.id == BinLatestState.bin_id).filter(
                BinLatestState.is_stale == False  # noqa: E712
            )

    bins = q.all()

    # Count open alerts per bin efficiently
    open_alert_counts: Dict[uuid.UUID, int] = {}
    if bins:
        bin_ids = [b.id for b in bins]
        from sqlalchemy import func
        rows = (
            db.query(Alert.bin_id, func.count(Alert.id))
            .filter(Alert.bin_id.in_(bin_ids), Alert.status == AlertStatus.OPEN)
            .group_by(Alert.bin_id)
            .all()
        )
        open_alert_counts = {row[0]: row[1] for row in rows}

    # Build items and sort by priority band
    items: List[PriorityBinItem] = []
    for b in bins:
        state = b.latest_state
        if state is not None:
            p_val = state.priority.value if hasattr(state.priority, "value") else str(state.priority)
            sh_val = state.sensor_health.value if hasattr(state.sensor_health, "value") else str(state.sensor_health)
            drs_val = state.device_reported_state.value if hasattr(state.device_reported_state, "value") else str(state.device_reported_state)
            fill = float(state.fill_percent) if state.fill_percent is not None else None
            stale = bool(state.is_stale)
            latest_event = state.latest_event_at
        else:
            p_val = FillPriority.UNKNOWN.value
            sh_val = "OK"
            drs_val = "OFFLINE"
            fill = None
            stale = False
            latest_event = None

        items.append(PriorityBinItem(
            bin_id=b.bin_id,
            name=b.name,
            area_name=b.area.name if b.area else None,
            fill_percent=fill,
            priority=p_val,
            sensor_health=sh_val,
            device_reported_state=drs_val,
            is_stale=stale,
            latest_event_at=latest_event,
            open_alert_count=open_alert_counts.get(b.id, 0),
        ))

    # Sort: CRITICAL → HIGH → MEDIUM → NORMAL → UNKNOWN, then fill desc within band
    def sort_key(item: PriorityBinItem):
        try:
            p_order = PRIORITY_ORDER.get(FillPriority(item.priority), 99)
        except ValueError:
            p_order = 99
        fill_desc = -(item.fill_percent or 0)
        return (p_order, fill_desc)

    items.sort(key=sort_key)

    return PriorityListResponse(items=items, total=len(items))

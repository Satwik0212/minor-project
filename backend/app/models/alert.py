"""Alert model representing operational anomalies and thresholds.

Normative source: docs/database.md: alerts table, docs/integration.md §7.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_VARIANT, Base
from app.models.enums import AlertSeverity, AlertStatus, AlertType

if TYPE_CHECKING:
    from app.models.collection_job import CollectionJob
    from app.models.device import Device
    from app.models.smart_bin import SmartBin
    from app.models.user import User


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    alert_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    type: Mapped[AlertType] = mapped_column(
        Enum(
            AlertType,
            name="alert_type_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(
            AlertSeverity,
            name="alert_severity_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(
            AlertStatus,
            name="alert_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=AlertStatus.OPEN,
        nullable=False,
    )
    bin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("smart_bins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("collection_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[Any]] = mapped_column(JSON_VARIANT, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    bin: Mapped[Optional["SmartBin"]] = relationship("SmartBin")
    device: Mapped[Optional["Device"]] = relationship("Device")
    job: Mapped[Optional["CollectionJob"]] = relationship("CollectionJob")
    acknowledger: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[acknowledged_by]
    )
    resolver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[resolved_by]
    )

    __table_args__ = (
        Index("idx_alerts_status_severity", "status", "severity"),
    )

    def __repr__(self) -> str:
        return f"<Alert id={self.id} alert_id={self.alert_id} type={self.type} severity={self.severity}>"

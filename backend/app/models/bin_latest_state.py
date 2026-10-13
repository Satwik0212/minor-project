"""Latest state projection table per bin for fast operational queries.

Normative source: docs/database.md: bin_latest_state table, docs/integration.md §7.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    DeviceReportedState,
    FillPriority,
    PredictedPriority,
    SensorHealth,
)

if TYPE_CHECKING:
    from app.models.sensor_reading import SensorReading
    from app.models.smart_bin import SmartBin


class BinLatestState(Base):
    __tablename__ = "bin_latest_state"

    bin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("smart_bins.id", ondelete="CASCADE"),
        primary_key=True,
    )
    latest_reading_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sensor_readings.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_event_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fill_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    priority: Mapped[FillPriority] = mapped_column(
        Enum(
            FillPriority,
            name="fill_priority_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=FillPriority.UNKNOWN,
        nullable=False,
    )
    predicted_priority: Mapped[PredictedPriority] = mapped_column(
        Enum(
            PredictedPriority,
            name="predicted_priority_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=PredictedPriority.NONE,
        nullable=False,
    )
    sensor_health: Mapped[SensorHealth] = mapped_column(
        Enum(
            SensorHealth,
            name="sensor_health_enum",
            create_constraint=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=SensorHealth.OK,
        nullable=False,
    )
    device_reported_state: Mapped[DeviceReportedState] = mapped_column(
        Enum(
            DeviceReportedState,
            name="device_reported_state_enum",
            create_constraint=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=DeviceReportedState.OFFLINE,
        nullable=False,
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    bin: Mapped["SmartBin"] = relationship("SmartBin", back_populates="latest_state")
    latest_reading: Mapped[Optional["SensorReading"]] = relationship(
        "SensorReading"
    )

    @property
    def current_priority(self) -> FillPriority:
        return self.priority

    @current_priority.setter
    def current_priority(self, val: FillPriority) -> None:
        self.priority = val


    __table_args__ = (
        Index("idx_bin_latest_state_priority", "priority"),
    )

    def __repr__(self) -> str:
        return f"<BinLatestState bin_id={self.bin_id} priority={self.priority} fill={self.fill_percent}>"

"""Sensor configuration / bin calibration model with versioning and geometry constraints.

Normative source: docs/database.md: sensor_configurations table, docs/integration.md §4.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.smart_bin import SmartBin
    from app.models.user import User


class SensorConfiguration(Base):
    __tablename__ = "sensor_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("smart_bins.id", ondelete="CASCADE"), nullable=False, index=True
    )
    calibration_version: Mapped[int] = mapped_column(Integer, nullable=False)
    empty_distance_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    full_distance_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    sampling_interval_seconds: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    bin: Mapped["SmartBin"] = relationship("SmartBin", back_populates="sensor_configurations")
    creator: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "bin_id", "calibration_version", name="uq_bin_calibration_version"
        ),
        CheckConstraint(
            "empty_distance_cm > full_distance_cm AND full_distance_cm > 0",
            name="ck_sensor_config_distances",
        ),
        CheckConstraint(
            "sampling_interval_seconds > 0",
            name="ck_sensor_config_sampling_interval",
        ),
    )

    def __repr__(self) -> str:
        return f"<SensorConfiguration bin_id={self.bin_id} version={self.calibration_version}>"


# Canonical alias for calibration
Calibration = SensorConfiguration

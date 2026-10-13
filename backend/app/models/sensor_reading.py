"""Append-only immutable sensor reading model storing raw and calculated telemetry.

Normative source: docs/database.md: sensor_readings table, docs/integration.md §3, §4, §15.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_VARIANT, Base
from app.models.enums import SensorHealth, TimestampQuality

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.smart_bin import SmartBin


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("smart_bins.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    timestamp_quality: Mapped[TimestampQuality] = mapped_column(
        Enum(
            TimestampQuality,
            name="timestamp_quality_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    boot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    calibration_version: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    distance_cm: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    fill_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    raw_hx711_count: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    temperature_c: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    humidity_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    rssi_dbm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    battery_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    sensor_health: Mapped[SensorHealth] = mapped_column(
        Enum(
            SensorHealth,
            name="sensor_health_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=SensorHealth.OK,
        nullable=False,
    )
    sensor_faults: Mapped[List[Any]] = mapped_column(
        JSON_VARIANT, default=list, nullable=False
    )
    quality_flags: Mapped[List[Any]] = mapped_column(
        JSON_VARIANT, default=list, nullable=False
    )
    eligible_for_operations: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    eligibility_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    bin: Mapped["SmartBin"] = relationship("SmartBin", back_populates="readings")
    device: Mapped["Device"] = relationship("Device", back_populates="readings")

    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "boot_id",
            "sequence",
            name="uq_sensor_readings_device_boot_sequence",
        ),
        Index(
            "idx_sensor_readings_bin_timestamp",
            "bin_id",
            text("timestamp DESC"),
        ),
        Index(
            "idx_sensor_readings_device_timestamp",
            "device_id",
            text("timestamp DESC"),
        ),
        CheckConstraint(
            "distance_cm IS NULL OR distance_cm >= 0",
            name="ck_sensor_readings_distance_positive",
        ),
        CheckConstraint(
            "weight_kg IS NULL OR weight_kg >= 0",
            name="ck_sensor_readings_weight_positive",
        ),
        CheckConstraint(
            "fill_percent IS NULL OR (fill_percent >= 0 AND fill_percent <= 100)",
            name="ck_sensor_readings_fill_bounds",
        ),
        CheckConstraint(
            "humidity_percent IS NULL OR (humidity_percent >= 0 AND humidity_percent <= 100)",
            name="ck_sensor_readings_humidity_bounds",
        ),
        CheckConstraint(
            "battery_percent IS NULL OR (battery_percent >= 0 AND battery_percent <= 100)",
            name="ck_sensor_readings_battery_bounds",
        ),
    )

    def __repr__(self) -> str:
        return f"<SensorReading id={self.id} bin_id={self.bin_id} fill_percent={self.fill_percent}>"

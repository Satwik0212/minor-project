"""Device model representing ESP32 IoT hardware units.

Normative source: docs/database.md: devices table, docs/integration.md §2, §6, §7.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DeviceLifecycleState, DeviceReportedState, SensorHealth

if TYPE_CHECKING:
    from app.models.device_bin_assignment import DeviceBinAssignment
    from app.models.sensor_reading import SensorReading


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    lifecycle_state: Mapped[DeviceLifecycleState] = mapped_column(
        Enum(
            DeviceLifecycleState,
            name="device_lifecycle_state_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=DeviceLifecycleState.UNPROVISIONED,
        nullable=False,
    )
    reported_state: Mapped[DeviceReportedState] = mapped_column(
        Enum(
            DeviceReportedState,
            name="device_reported_state_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=DeviceReportedState.OFFLINE,
        nullable=False,
    )
    firmware_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_rssi_dbm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sensor_health: Mapped[SensorHealth] = mapped_column(
        Enum(
            SensorHealth,
            name="sensor_health_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=SensorHealth.OK,
        nullable=False,
    )
    credential_ref: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
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

    assignments: Mapped[List["DeviceBinAssignment"]] = relationship(
        "DeviceBinAssignment", back_populates="device", cascade="all, delete-orphan"
    )
    readings: Mapped[List["SensorReading"]] = relationship(
        "SensorReading", back_populates="device", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Device id={self.id} device_id={self.device_id} state={self.lifecycle_state}>"

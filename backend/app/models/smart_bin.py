"""Smart bin model representing waste containers with geolocation and fill thresholds.

Normative source: docs/database.md: smart_bins table, docs/integration.md §7.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import BinStatus, BinType

if TYPE_CHECKING:
    from app.models.area import Area
    from app.models.bin_latest_state import BinLatestState
    from app.models.calibration import SensorConfiguration
    from app.models.device_bin_assignment import DeviceBinAssignment
    from app.models.sensor_reading import SensorReading


class SmartBin(Base):
    __tablename__ = "smart_bins"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bin_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    bin_type: Mapped[BinType] = mapped_column(
        Enum(BinType, name="bin_type_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=BinType.MUNICIPAL,
        nullable=False,
    )
    status: Mapped[BinStatus] = mapped_column(
        Enum(BinStatus, name="bin_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=BinStatus.DRAFT,
        nullable=False,
    )
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    area_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("areas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    capacity_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    nominal_full_bin_weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    warning_threshold_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("70.00"), nullable=False
    )
    critical_threshold_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("95.00"), nullable=False
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

    area: Mapped[Optional["Area"]] = relationship("Area", back_populates="bins")
    assignments: Mapped[List["DeviceBinAssignment"]] = relationship(
        "DeviceBinAssignment", back_populates="bin", cascade="all, delete-orphan"
    )
    sensor_configurations: Mapped[List["SensorConfiguration"]] = relationship(
        "SensorConfiguration", back_populates="bin", cascade="all, delete-orphan"
    )
    readings: Mapped[List["SensorReading"]] = relationship(
        "SensorReading", back_populates="bin", cascade="all, delete-orphan"
    )
    latest_state: Mapped[Optional["BinLatestState"]] = relationship(
        "BinLatestState", back_populates="bin", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "capacity_kg >= 0",
            name="ck_smart_bins_capacity_kg_positive",
        ),
        CheckConstraint(
            "nominal_full_bin_weight_kg IS NULL OR nominal_full_bin_weight_kg >= 0",
            name="ck_smart_bins_nominal_weight_positive",
        ),
        CheckConstraint(
            "warning_threshold_pct >= 0 AND warning_threshold_pct < critical_threshold_pct AND critical_threshold_pct <= 100",
            name="ck_smart_bins_thresholds",
        ),
        Index("idx_smart_bins_location", "location", postgresql_using="gist"),
    )

    def __repr__(self) -> str:
        return f"<SmartBin id={self.id} bin_id={self.bin_id} status={self.status}>"

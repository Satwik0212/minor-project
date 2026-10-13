"""Vehicle model representing waste collection fleet units.

Normative source: docs/database.md: vehicles table, docs/integration.md §9.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import VehicleStatus, VehicleType

if TYPE_CHECKING:
    from app.models.route import Route


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vehicle_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(
            VehicleType,
            name="vehicle_type_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=VehicleType.TRUCK,
        nullable=False,
    )
    capacity_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(
            VehicleStatus,
            name="vehicle_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=VehicleStatus.ACTIVE,
        nullable=False,
    )
    registration_no: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
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

    routes: Mapped[List["Route"]] = relationship(
        "Route", back_populates="vehicle"
    )

    __table_args__ = (
        CheckConstraint(
            "capacity_kg > 0",
            name="ck_vehicles_capacity_kg_positive",
        ),
    )

    def __repr__(self) -> str:
        return f"<Vehicle id={self.id} vehicle_id={self.vehicle_id} capacity={self.capacity_kg}>"

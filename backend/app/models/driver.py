"""Driver and DriverLocationPoint models.

Normative source: docs/database.md: drivers & driver_location_points tables, docs/integration.md §10.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geography
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DriverStatus

if TYPE_CHECKING:
    from app.models.route import Route
    from app.models.user import User


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    license_no: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    status: Mapped[DriverStatus] = mapped_column(
        Enum(
            DriverStatus,
            name="driver_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=DriverStatus.ACTIVE,
        nullable=False,
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

    user: Mapped["User"] = relationship("User", back_populates="driver")
    routes: Mapped[List["Route"]] = relationship(
        "Route", back_populates="driver"
    )
    location_points: Mapped[List["DriverLocationPoint"]] = relationship(
        "DriverLocationPoint", back_populates="driver", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Driver id={self.id} driver_id={self.driver_id} status={self.status}>"


class DriverLocationPoint(Base):
    __tablename__ = "driver_location_points"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    route_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("routes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(32), default="GPS", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    driver: Mapped["Driver"] = relationship(
        "Driver", back_populates="location_points"
    )

    __table_args__ = (
        Index(
            "idx_driver_location_points_location",
            "location",
            postgresql_using="gist",
        ),
        Index(
            "idx_driver_location_points_captured",
            "driver_id",
            text("captured_at DESC"),
        ),
    )

    def __repr__(self) -> str:
        return f"<DriverLocationPoint driver_id={self.driver_id} captured_at={self.captured_at}>"

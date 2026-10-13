"""Route model representing planned waste collection vehicle routes.

Normative source: docs/database.md: routes table, docs/integration.md §9.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RouteObjective, RouteStatus

if TYPE_CHECKING:
    from app.models.depot import Depot
    from app.models.driver import Driver
    from app.models.route_stop import RouteStop
    from app.models.user import User
    from app.models.vehicle import Vehicle


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    route_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    depot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("depots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[RouteStatus] = mapped_column(
        Enum(
            RouteStatus,
            name="route_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=RouteStatus.DRAFT,
        nullable=False,
    )
    objective: Mapped[RouteObjective] = mapped_column(
        Enum(
            RouteObjective,
            name="route_objective_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=RouteObjective.MIN_DISTANCE,
        nullable=False,
    )
    distance_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    duration_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    capacity_safety_factor: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.90"), nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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

    depot: Mapped["Depot"] = relationship("Depot", back_populates="routes")
    vehicle: Mapped[Optional["Vehicle"]] = relationship(
        "Vehicle", back_populates="routes"
    )
    driver: Mapped[Optional["Driver"]] = relationship(
        "Driver", back_populates="routes"
    )
    approver: Mapped[Optional["User"]] = relationship("User")
    stops: Mapped[List["RouteStop"]] = relationship(
        "RouteStop",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteStop.sequence_no",
    )

    __table_args__ = (
        CheckConstraint(
            "capacity_safety_factor > 0 AND capacity_safety_factor <= 1.0",
            name="ck_routes_safety_factor",
        ),
    )

    def __repr__(self) -> str:
        return f"<Route id={self.id} route_id={self.route_id} status={self.status}>"

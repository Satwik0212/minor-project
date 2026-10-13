"""RouteStop model representing sequential collection stops along a route.

Normative source: docs/database.md: route_stops table, docs/integration.md §9.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.collection_job import CollectionJob
    from app.models.route import Route
    from app.models.smart_bin import SmartBin


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collection_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("collection_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("smart_bins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_arrival_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_arrival_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    distance_from_previous_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    route: Mapped["Route"] = relationship("Route", back_populates="stops")
    collection_job: Mapped["CollectionJob"] = relationship(
        "CollectionJob", back_populates="route_stop"
    )
    bin: Mapped["SmartBin"] = relationship("SmartBin")

    __table_args__ = (
        UniqueConstraint("route_id", "sequence_no", name="uq_route_stops_route_sequence"),
    )

    def __repr__(self) -> str:
        return f"<RouteStop route_id={self.route_id} seq={self.sequence_no} bin_id={self.bin_id}>"

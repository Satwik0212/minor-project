"""Depot model representing collection fleet stations and route origin/destination.

Normative source: docs/database.md: depots table.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.route import Route


class Depot(Base):
    __tablename__ = "depots"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    depot_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
        "Route", back_populates="depot"
    )

    __table_args__ = (
        Index("idx_depots_location", "location", postgresql_using="gist"),
    )

    def __repr__(self) -> str:
        return f"<Depot id={self.id} depot_id={self.depot_id} name={self.name}>"

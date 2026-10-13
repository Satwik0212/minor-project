"""Area model representing service zones with PostGIS boundary polygons.

Normative source: docs/database.md: areas table.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.smart_bin import SmartBin


class Area(Base):
    __tablename__ = "areas"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    area_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    boundary: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=True,
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

    bins: Mapped[List["SmartBin"]] = relationship(
        "SmartBin", back_populates="area"
    )

    __table_args__ = (
        Index("idx_areas_boundary", "boundary", postgresql_using="gist"),
    )

    def __repr__(self) -> str:
        return f"<Area id={self.id} area_id={self.area_id} name={self.name}>"

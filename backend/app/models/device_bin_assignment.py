"""Device-to-bin assignment model with partial unique indexes enforcing active pairing.

Normative source: docs/database.md: device_bin_assignments table, docs/integration.md §2.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.smart_bin import SmartBin
    from app.models.user import User


class DeviceBinAssignment(Base):
    __tablename__ = "device_bin_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("smart_bins.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="assignments")
    bin: Mapped["SmartBin"] = relationship("SmartBin", back_populates="assignments")
    assigner: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        Index(
            "uq_active_device_assignment",
            "device_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index(
            "uq_active_bin_assignment",
            "bin_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<DeviceBinAssignment id={self.id} device_id={self.device_id} bin_id={self.bin_id} active={self.ended_at is None}>"

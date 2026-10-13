"""Runtime system settings model for dynamic configuration authority.

Normative source: docs/database.md: system_settings table, docs/integration.md §10.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_VARIANT, Base

if TYPE_CHECKING:
    from app.models.user import User


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON_VARIANT, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    validation: Mapped[Optional[Any]] = mapped_column(JSON_VARIANT, nullable=True)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    updater: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<SystemSetting key={self.key} unit={self.unit}>"

"""AuditEvent model tracking privileged actions, configuration changes and overrides.

Normative source: docs/database.md: audit_logs table, docs/integration.md §4, §8, §10.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_VARIANT, Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    before_diff: Mapped[Optional[Any]] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    after_diff: Mapped[Optional[Any]] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )

    actor: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        Index("idx_audit_events_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.id} action={self.action} entity={self.entity_type}:{self.entity_id}>"

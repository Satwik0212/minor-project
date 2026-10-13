"""IdempotencyRecord model ensuring idempotent REST mutations per actor.

Normative source: docs/database.md: idempotency_keys table, docs/integration.md §1.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_VARIANT, Base

if TYPE_CHECKING:
    from app.models.user import User


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[Optional[Any]] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actor: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "actor_id", "key", name="uq_idempotency_records_actor_key"
        ),
    )

    def __repr__(self) -> str:
        return f"<IdempotencyRecord actor={self.actor_id} key={self.key} status={self.response_status}>"

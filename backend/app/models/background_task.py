"""BackgroundTask model tracking asynchronous optimization and training jobs.

Normative source: docs/database.md: background_jobs table, docs/integration.md §9, §12.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_VARIANT, Base
from app.models.enums import BackgroundTaskStatus

if TYPE_CHECKING:
    from app.models.user import User


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[BackgroundTaskStatus] = mapped_column(
        Enum(
            BackgroundTaskStatus,
            name="background_task_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=BackgroundTaskStatus.QUEUED,
        nullable=False,
    )
    progress: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), nullable=False
    )
    result_ref: Mapped[Optional[Any]] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
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

    creator: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<BackgroundTask id={self.id} task_id={self.task_id} status={self.status}>"

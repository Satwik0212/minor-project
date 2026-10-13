"""Quarantined rejected telemetry events model.

Normative source: docs/database.md: rejected_telemetry_events table, docs/integration.md §11, §15.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_VARIANT, Base


class RejectedTelemetryEvent(Base):
    __tablename__ = "rejected_telemetry_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    payload_redacted: Mapped[Optional[Any]] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    request_trace_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )

    def __repr__(self) -> str:
        return f"<RejectedTelemetryEvent id={self.id} reason={self.reason_code} topic={self.topic}>"

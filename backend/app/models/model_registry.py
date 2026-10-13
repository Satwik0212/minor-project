"""ModelRegistry model tracking trained machine learning model artifacts and evaluation metrics.

Normative source: docs/database.md: model_registry table.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_VARIANT, Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_version: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    data_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    data_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metrics: Mapped[Optional[Any]] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    artifact_uri: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="ACTIVE", nullable=False
    )

    def __repr__(self) -> str:
        return f"<ModelRegistry version={self.model_version} algorithm={self.algorithm}>"

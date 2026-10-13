"""Prediction model for forecast horizon fill predictions.

Normative source: docs/database.md: predictions table, docs/integration.md §7.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PredictedPriority

if TYPE_CHECKING:
    from app.models.smart_bin import SmartBin


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("smart_bins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    horizon_minutes: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    predicted_fill_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    predicted_priority: Mapped[PredictedPriority] = mapped_column(
        Enum(
            PredictedPriority,
            name="predicted_priority_enum",
            create_constraint=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=PredictedPriority.NONE,
        nullable=False,
    )
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="AVAILABLE", nullable=False
    )

    bin: Mapped["SmartBin"] = relationship("SmartBin")

    def __repr__(self) -> str:
        return f"<Prediction bin_id={self.bin_id} fill={self.predicted_fill_percent} priority={self.predicted_priority}>"

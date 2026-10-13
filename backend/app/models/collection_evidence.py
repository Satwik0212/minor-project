"""CollectionVerification model storing sensor evidence and audit trails for pickups.

Normative source: docs/database.md: collection_verifications table, docs/integration.md §8, §12.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_VARIANT, Base
from app.models.enums import VerificationOutcome

if TYPE_CHECKING:
    from app.models.collection_job import CollectionJob
    from app.models.sensor_reading import SensorReading
    from app.models.user import User


class CollectionVerification(Base):
    __tablename__ = "collection_verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("collection_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    before_reading_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sensor_readings.id", ondelete="SET NULL"),
        nullable=True,
    )
    after_reading_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sensor_readings.id", ondelete="SET NULL"),
        nullable=True,
    )
    otp_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    arrival_lat: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    arrival_lon: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    finish_lat: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    finish_lon: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    verify_lat: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    verify_lon: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    fill_before_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    fill_after_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    weight_before_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    weight_after_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    outcome: Mapped[VerificationOutcome] = mapped_column(
        Enum(
            VerificationOutcome,
            name="verification_outcome_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    reason_codes: Mapped[List[Any]] = mapped_column(
        JSON_VARIANT, default=list, nullable=False
    )
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[Optional[uuid.UUID]] = mapped_column(
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

    job: Mapped["CollectionJob"] = relationship(
        "CollectionJob", back_populates="verification"
    )
    before_reading: Mapped[Optional["SensorReading"]] = relationship(
        "SensorReading", foreign_keys=[before_reading_id]
    )
    after_reading: Mapped[Optional["SensorReading"]] = relationship(
        "SensorReading", foreign_keys=[after_reading_id]
    )
    overrider: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[overridden_by]
    )

    def __repr__(self) -> str:
        return f"<CollectionVerification job_id={self.job_id} outcome={self.outcome}>"

"""CollectionJob model representing waste collection tasks and lifecycle states.

Normative source: docs/database.md: collection_jobs table, docs/integration.md §8.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import FillPriority, JobSource, JobStatus

if TYPE_CHECKING:
    from app.models.collection_evidence import CollectionVerification
    from app.models.route_stop import RouteStop
    from app.models.smart_bin import SmartBin
    from app.models.user import User


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("smart_bins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[JobSource] = mapped_column(
        Enum(
            JobSource,
            name="job_source_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=JobSource.THRESHOLD,
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus,
            name="job_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=JobStatus.PENDING,
        nullable=False,
    )
    priority: Mapped[FillPriority] = mapped_column(
        Enum(
            FillPriority,
            name="fill_priority_enum",
            create_constraint=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=FillPriority.NORMAL,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    en_route_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    arrived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    collecting_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pickup_finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    bin: Mapped["SmartBin"] = relationship("SmartBin")
    creator: Mapped[Optional["User"]] = relationship("User")
    route_stop: Mapped[Optional["RouteStop"]] = relationship(
        "RouteStop",
        back_populates="collection_job",
        uselist=False,
        cascade="all, delete-orphan",
    )
    verification: Mapped[Optional["CollectionVerification"]] = relationship(
        "CollectionVerification",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_collection_jobs_status_priority", "status", "priority"),
    )

    def __repr__(self) -> str:
        return f"<CollectionJob id={self.id} job_id={self.job_id} status={self.status}>"

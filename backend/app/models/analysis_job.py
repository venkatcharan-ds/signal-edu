from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.capability_profile import CapabilityProfile

_STATUSES = (
    "queued",
    "github_fetch",
    "evidence_extract",
    "ai_analysis",
    "scoring",
    "complete",
    "failed",
)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint(
            f"status IN {_STATUSES}",
            name="ck_analysis_jobs_status",
        ),
        Index("idx_analysis_jobs_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Pipeline progress
    status:       Mapped[str]       = mapped_column(String(50),  nullable=False, server_default="queued")
    current_step: Mapped[str | None] = mapped_column(String(100))
    progress_pct: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")

    # Populated on failure
    error_message: Mapped[str | None] = mapped_column(Text)

    started_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User]                            = relationship(back_populates="analysis_jobs")
    capability_profiles: Mapped[list[CapabilityProfile]] = relationship(back_populates="job")

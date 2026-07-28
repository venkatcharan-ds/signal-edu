from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    Index, Integer, Numeric, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.analysis_job import AnalysisJob
    from app.models.role_template import GapAnalysis

_DIM_CHECK = "dimension IN ('technical_execution','problem_complexity','communication_quality')"


class CapabilityProfile(Base):
    """
    One row per analysis run. is_current=True marks the active profile.
    Previous profiles are retained for progress tracking.
    """
    __tablename__ = "capability_profiles"
    __table_args__ = (
        # Score range enforcement — matches the 1.0–9.0 SIGNAL scale
        CheckConstraint("technical_execution   BETWEEN 1.0 AND 9.0", name="ck_cp_te"),
        CheckConstraint("problem_complexity    BETWEEN 1.0 AND 9.0", name="ck_cp_pc"),
        CheckConstraint("communication_quality BETWEEN 1.0 AND 9.0", name="ck_cp_cq"),
        # Partial index — fast lookup for the single current profile per user
        Index("idx_capability_profiles_user_current", "user_id", "is_current"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id:  Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_jobs.id")
    )

    # Exactly one profile per user has is_current=True;
    # the pipeline flips previous profiles to False before inserting the new one
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # ── Three SIGNAL dimensions (Numeric 3,1 → 1.0–9.0) ──────────────────────
    technical_execution:   Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    problem_complexity:    Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    communication_quality: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))

    # Model confidence per dimension (0.00–1.00)
    te_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    pc_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    cq_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    # Percentile within the SIGNAL user cohort (1–99)
    te_percentile: Mapped[int | None] = mapped_column(Integer)
    pc_percentile: Mapped[int | None] = mapped_column(Integer)
    cq_percentile: Mapped[int | None] = mapped_column(Integer)

    # Raw objective signals from Stage 1–2 (stored for auditability and replay)
    objective_signals: Mapped[dict | None] = mapped_column(JSONB)

    # List[str] of capability strings verified by the AI (e.g. "Production deployment on Raspberry Pi")
    verified_capabilities: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    # Full Claude response — retained so scores can be re-derived without re-calling the API
    raw_ai_response: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user:             Mapped[User]                  = relationship(back_populates="capability_profiles")
    job:              Mapped[AnalysisJob | None]     = relationship(back_populates="capability_profiles")
    evidence_citations: Mapped[list[EvidenceCitation]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    gap_analyses:     Mapped[list[GapAnalysis]]     = relationship(back_populates="profile", cascade="all, delete-orphan")


class EvidenceCitation(Base):
    """
    One row per citable piece of evidence supporting a dimension score.
    Every score change must be traceable to at least one citation (anti-hallucination rule).
    """
    __tablename__ = "evidence_citations"
    __table_args__ = (
        CheckConstraint(_DIM_CHECK, name="ck_evidence_citations_dimension"),
        Index("idx_evidence_citations_profile", "profile_id"),
    )

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capability_profiles.id", ondelete="CASCADE"), nullable=False
    )

    # Which of the three SIGNAL dimensions this citation supports
    dimension: Mapped[str] = mapped_column(nullable=False)  # type: String inferred

    # The citable fact — must reference a specific artifact, repo, or commit
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Source classification: "github_repo" | "pdf" | "link" | "readme" | "commit_history"
    artifact_type: Mapped[str | None] = mapped_column()

    # Identifier that locates the source (repo full_name, artifact UUID, URL, etc.)
    artifact_ref: Mapped[str | None] = mapped_column(Text)

    # How much this citation contributed to the final dimension score (informational)
    score_contribution: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profile: Mapped[CapabilityProfile] = relationship(back_populates="evidence_citations")

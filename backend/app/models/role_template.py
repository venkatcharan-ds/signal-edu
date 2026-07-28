from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.capability_profile import CapabilityProfile
    from app.models.user import User

_DIM_CHECK = "dimension IN ('technical_execution','problem_complexity','communication_quality')"


class RoleTemplate(Base):
    """
    Pre-seeded role definitions with TE/PC/CQ thresholds.
    10 roles defined in database/seeds/role_templates.sql.
    Read-only in production; never updated by user actions.
    """
    __tablename__ = "role_templates"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_role_templates_slug"),
    )

    id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug:  Mapped[str]       = mapped_column(String(100), nullable=False)  # e.g. "ml-engineer"
    title: Mapped[str]       = mapped_column(String(255), nullable=False)  # e.g. "ML Engineer"

    # Minimum scores required to be considered "ready" for this role
    te_threshold: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    pc_threshold: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    cq_threshold: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)

    # Optional list of specific signal types that must be present (e.g. ["has_ci", "has_tests"])
    required_signals: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")

    description: Mapped[str | None] = mapped_column(Text)

    gap_analyses: Mapped[list[GapAnalysis]] = relationship(back_populates="role")


class GapAnalysis(Base):
    """
    Result of comparing a CapabilityProfile against a RoleTemplate.
    Gaps are positive numbers (how much the student is below threshold);
    negative gaps mean they exceed the threshold for that dimension.
    overall_ready=True when all three gaps are ≤ 0.
    """
    __tablename__ = "gap_analyses"
    __table_args__ = (
        Index("idx_gap_analyses_profile", "profile_id"),
    )

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capability_profiles.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("role_templates.id"), nullable=False
    )

    # Gap = threshold − score  (positive = below threshold, negative = exceeds)
    te_gap: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    pc_gap: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    cq_gap: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))

    overall_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profile:         Mapped[CapabilityProfile]     = relationship(back_populates="gap_analyses")
    role:            Mapped[RoleTemplate]           = relationship(back_populates="gap_analyses")
    recommendations: Mapped[list[Recommendation]]  = relationship(back_populates="gap_analysis", cascade="all, delete-orphan")


class Recommendation(Base):
    """
    One of exactly 3 actionable recommendations produced by Claude Haiku
    for a specific GapAnalysis. Always references a concrete evidence type —
    never a generic "learn X" suggestion.
    """
    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(_DIM_CHECK, name="ck_recommendations_dimension"),
        CheckConstraint("priority BETWEEN 1 AND 3",  name="ck_recommendations_priority"),
        Index("idx_recommendations_gap", "gap_analysis_id"),
    )

    id:             Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gap_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gap_analyses.id", ondelete="CASCADE"), nullable=False
    )

    dimension: Mapped[str] = mapped_column(String(50),  nullable=False)
    priority:  Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = most important

    # Short action title shown in the UI card
    title:       Mapped[str] = mapped_column(String(500), nullable=False)
    # Detailed description with specific, citable action steps
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Evidence type the student should produce: "github_repo" | "pdf" | "link" | "readme"
    evidence_type: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    gap_analysis: Mapped[GapAnalysis] = relationship(back_populates="recommendations")


class ProfileView(Base):
    """
    Append-only log of public profile views for analytics.
    Used by the admin /metrics endpoint (Phase 5).
    """
    __tablename__ = "profile_views"
    __table_args__ = (
        Index("idx_profile_views_user_time", "user_id", "viewed_at"),
    )

    id:           Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:      Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    viewer_ip:    Mapped[str | None] = mapped_column(String(45))
    is_logged_in: Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    viewed_at:    Mapped[datetime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="profile_views")

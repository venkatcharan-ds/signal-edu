from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.artifact import Artifact
    from app.models.analysis_job import AnalysisJob
    from app.models.capability_profile import CapabilityProfile
    from app.models.role_template import ProfileView


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("github_id",       name="uq_users_github_id"),
        UniqueConstraint("github_username", name="uq_users_github_username"),
        Index("idx_users_github_username",  "github_username"),
    )

    # Primary key is the Supabase user UUID (matches the JWT `sub` claim)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # GitHub identity — populated from Supabase user_metadata on first sign-in
    github_id:       Mapped[int]        = mapped_column(BigInteger, nullable=False)
    github_username: Mapped[str]        = mapped_column(String(255), nullable=False)
    github_email:    Mapped[str | None] = mapped_column(String(255))
    github_avatar:   Mapped[str | None] = mapped_column(String(500))

    # User-editable fields
    full_name:   Mapped[str | None] = mapped_column(String(255))
    institution: Mapped[str | None] = mapped_column(String(255))

    # GitHub OAuth token captured at login — used by the analysis pipeline
    # to call the GitHub API on the user's behalf (public repos, 5000 req/hr)
    github_access_token: Mapped[str | None] = mapped_column(Text)

    # Self-reported skills list used by the gap-reveal feature
    resume_skills: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Kept current by the set_updated_at trigger (migration 0002)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    repositories:        Mapped[list[Repository]]        = relationship(back_populates="user", cascade="all, delete-orphan")
    artifacts:           Mapped[list[Artifact]]           = relationship(back_populates="user", cascade="all, delete-orphan")
    analysis_jobs:       Mapped[list[AnalysisJob]]        = relationship(back_populates="user", cascade="all, delete-orphan")
    capability_profiles: Mapped[list[CapabilityProfile]]  = relationship(back_populates="user", cascade="all, delete-orphan")
    profile_views:       Mapped[list[ProfileView]]        = relationship(back_populates="user", cascade="all, delete-orphan")

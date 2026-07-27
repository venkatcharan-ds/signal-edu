from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Index, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("github_repo_id", name="uq_repositories_github_repo_id"),
        Index("idx_repositories_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # FK defined in migration; avoid redundant DDL in SQLAlchemy for async
        nullable=False,
        index=False,  # covered by idx_repositories_user above
    )

    # GitHub metadata
    github_repo_id: Mapped[int]         = mapped_column(BigInteger, nullable=False)
    name:           Mapped[str]         = mapped_column(String(255), nullable=False)
    full_name:      Mapped[str]         = mapped_column(String(255), nullable=False)
    description:    Mapped[str | None]  = mapped_column(Text)
    url:            Mapped[str]         = mapped_column(Text, nullable=False)
    is_fork:        Mapped[bool]        = mapped_column(Boolean, nullable=False, server_default="false")
    stars:          Mapped[int]         = mapped_column(Integer, nullable=False, server_default="0")

    # Language composition — {"Python": 12340, "Shell": 450}
    languages: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Commit signals (populated by GitHub Engine — Stage 1)
    commit_count:   Mapped[int]              = mapped_column(Integer, nullable=False, server_default="0")
    last_commit_at: Mapped[datetime | None]  = mapped_column(DateTime(timezone=True))

    # Evidence signals (populated by Evidence Engine — Stage 2)
    has_readme:           Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    readme_content:       Mapped[str | None] = mapped_column(Text)
    readme_word_count:    Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    has_tests:            Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    has_ci:               Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    has_deployment_config: Mapped[bool]      = mapped_column(Boolean, nullable=False, server_default="false")

    # Raw API response stored for reprocessing without extra API calls
    raw_github_data: Mapped[dict | None] = mapped_column(JSONB)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="repositories")

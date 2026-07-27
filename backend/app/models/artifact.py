from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User

_ARTIFACT_TYPES = ("pdf", "link", "certificate", "project_report")


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        CheckConstraint(
            f"artifact_type IN {_ARTIFACT_TYPES}",
            name="ck_artifacts_type",
        ),
        Index("idx_artifacts_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # "pdf" | "link" | "certificate" | "project_report"
    artifact_type: Mapped[str]        = mapped_column(String(50), nullable=False)
    title:         Mapped[str | None] = mapped_column(String(500))

    # For links: the source URL; for PDFs: the Supabase Storage object path
    source_url:   Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)  # Supabase Storage key

    # Text content extracted by PyMuPDF (PDF) or BeautifulSoup (link)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    word_count:     Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="artifacts")

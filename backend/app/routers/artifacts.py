"""
Artifacts router — PDF uploads and external URL evidence.
Full implementation in Phase 5 (PyMuPDF + BeautifulSoup).
"""
from __future__ import annotations

import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User

log = structlog.get_logger()
router = APIRouter()

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_CONTENT_TYPES = {"application/pdf"}


@router.post("/upload")
async def upload_artifact(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Upload a PDF artifact (research paper, report, certificate).
    Max 10 MB. Text extraction via PyMuPDF in Phase 5.
    """
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    # Phase 5: extract text, store artifact, upload to Supabase Storage
    raise HTTPException(status_code=501, detail="PDF extraction coming in Phase 5")


@router.post("/link")
async def add_link(
    url: str,
    title: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Submit a portfolio or external link as evidence (scraped in Phase 5)."""
    if not url.startswith(("https://", "http://")):
        raise HTTPException(status_code=422, detail="url must be a valid HTTP/HTTPS URL")
    # Phase 5: fetch page, extract text, store artifact
    raise HTTPException(status_code=501, detail="URL evidence coming in Phase 5")


@router.get("/")
async def list_artifacts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    """List all uploaded artifacts for the current user."""
    # Phase 5
    return []


@router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Delete an artifact and its Supabase Storage object."""
    # Phase 5
    raise HTTPException(status_code=501, detail="Delete coming in Phase 5")

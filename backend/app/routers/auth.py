"""
Auth router — post-OAuth user synchronisation.

Flow:
  1. Frontend completes Supabase GitHub OAuth (supabase.auth.signInWithOAuth)
  2. Frontend receives session; provider_token is the GitHub OAuth token
  3. Frontend calls POST /v1/auth/sync with Authorization: Bearer <access_token>
     and body: { "provider_token": "<github_oauth_token>" }
  4. We upsert the User row and store the GitHub token for pipeline use
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User

log = structlog.get_logger()
router = APIRouter()


class SyncRequest(BaseModel):
    provider_token: str | None = None


class SyncResponse(BaseModel):
    id: str
    github_username: str
    full_name: str | None
    avatar: str | None
    email: str | None
    institution: str | None


@router.post("/sync", response_model=SyncResponse)
async def sync_user(
    body: SyncRequest = SyncRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SyncResponse:
    """
    Called by the frontend immediately after OAuth completes.
    Upserts the User row (via get_current_user) and stores the GitHub token.
    Idempotent — safe to call multiple times.
    """
    if body.provider_token and user.github_access_token != body.provider_token:
        user.github_access_token = body.provider_token
        await db.flush()
        log.info("user.token_stored", username=user.github_username)

    return SyncResponse(
        id=str(user.id),
        github_username=user.github_username,
        full_name=user.full_name,
        avatar=user.github_avatar,
        email=user.github_email,
        institution=user.institution,
    )


@router.post("/logout")
async def logout(user: User = Depends(get_current_user)) -> dict:
    """Client-side logout — Supabase session invalidation is done by the SDK."""
    log.info("user.logout", username=user.github_username)
    return {"ok": True}

"""
FastAPI dependencies shared across routers.

`get_current_user` is the primary auth gate — inject it into any
protected endpoint. On first call it upserts the User row from the
Supabase JWT so the database stays in sync with the identity provider.
"""
from __future__ import annotations

import uuid
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, verify_supabase_jwt
from app.database import get_db
from app.models.user import User

log = structlog.get_logger()
_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Verify the Bearer token, then return (or lazily create) the User row.
    Upserts name/avatar/email each request so profile data stays fresh.
    """
    token_data: TokenPayload = verify_supabase_jwt(credentials.credentials)
    supabase_uuid = uuid.UUID(token_data.sub)

    result = await db.execute(select(User).where(User.id == supabase_uuid))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        # First sign-in — create the row
        if not token_data.github_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub username not found in token. Re-authenticate.",
            )
        user = User(
            id=supabase_uuid,
            github_id=token_data.github_id or 0,
            github_username=token_data.github_username,
            github_email=token_data.email,
            github_avatar=token_data.github_avatar,
            full_name=token_data.full_name,
        )
        db.add(user)
        await db.flush()
        log.info("user.created", username=user.github_username, id=str(user.id))
    else:
        # Refresh mutable fields without a round-trip on every request
        dirty = False
        if token_data.github_avatar and user.github_avatar != token_data.github_avatar:
            user.github_avatar = token_data.github_avatar
            dirty = True
        if token_data.full_name and user.full_name != token_data.full_name:
            user.full_name = token_data.full_name
            dirty = True
        if dirty:
            await db.flush()

    return user

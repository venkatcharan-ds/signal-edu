"""
JWT verification for Supabase-issued tokens.

Supabase issues HS256 JWTs signed with SUPABASE_JWT_SECRET.
The `sub` claim is the Supabase user UUID; `app_metadata.provider` is "github".
GitHub identity lives in `user_metadata` (login, avatar_url, user_name, email).
"""
from __future__ import annotations

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException, status
from app.config import get_settings

_ALGORITHM = "HS256"
_AUDIENCE = "authenticated"


class TokenPayload:
    __slots__ = ("sub", "email", "github_id", "github_username", "github_avatar", "full_name")

    def __init__(
        self,
        sub: str,
        email: str | None,
        github_id: int | None,
        github_username: str | None,
        github_avatar: str | None,
        full_name: str | None,
    ) -> None:
        self.sub = sub
        self.email = email
        self.github_id = github_id
        self.github_username = github_username
        self.github_avatar = github_avatar
        self.full_name = full_name


def verify_supabase_jwt(token: str) -> TokenPayload:
    """
    Decode and verify a Supabase access token.
    Raises HTTP 401 on any verification failure.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[_ALGORITHM],
            audience=_AUDIENCE,
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub: str | None = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_meta: dict = payload.get("user_metadata", {})
    # Supabase stores GitHub identity under user_metadata
    github_id_raw = user_meta.get("provider_id") or user_meta.get("sub")
    try:
        github_id = int(github_id_raw) if github_id_raw else None
    except (TypeError, ValueError):
        github_id = None

    return TokenPayload(
        sub=sub,
        email=payload.get("email") or user_meta.get("email"),
        github_id=github_id,
        github_username=user_meta.get("user_name") or user_meta.get("preferred_username"),
        github_avatar=user_meta.get("avatar_url"),
        full_name=user_meta.get("full_name") or user_meta.get("name"),
    )

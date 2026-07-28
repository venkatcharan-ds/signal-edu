"""
JWT verification for Supabase-issued tokens.

Supabase issues JWTs signed with either:
  - ES256: asymmetric ECDSA (user access tokens — current default)
  - HS256: symmetric HMAC  (legacy anon/service tokens)

For ES256, the public key is fetched from the Supabase JWKS endpoint and
cached in-process for _JWKS_TTL seconds. An unknown kid triggers an immediate
re-fetch before raising an error, so key rotations are handled automatically.
"""
from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from jwt.algorithms import ECAlgorithm
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException, status
import structlog

from app.config import get_settings

log = structlog.get_logger()

_AUDIENCE = "authenticated"
_JWKS_TTL = 3600  # re-fetch public keys at most once per hour

# In-process JWKS cache  {kid: public_key_object}
_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0


# ── JWKS helpers ──────────────────────────────────────────────────────────────

def _jwks_url() -> str:
    return get_settings().supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"


def _issuer() -> str:
    return get_settings().supabase_url.rstrip("/") + "/auth/v1"


def _refresh_jwks() -> None:
    """Fetch JWKS and repopulate _jwks_cache. Swallows network errors."""
    global _jwks_fetched_at
    url = _jwks_url()
    try:
        resp = httpx.get(url, timeout=5)
        resp.raise_for_status()
        new_keys: dict[str, Any] = {}
        for key_data in resp.json().get("keys", []):
            kid = key_data.get("kid")
            alg = key_data.get("alg", "")
            if kid and alg in ("ES256", "RS256"):
                new_keys[kid] = ECAlgorithm.from_jwk(key_data)
        _jwks_cache.clear()
        _jwks_cache.update(new_keys)
        _jwks_fetched_at = time.monotonic()
        log.info("jwks.refreshed", key_count=len(_jwks_cache))
    except Exception as exc:
        log.warning("jwks.fetch_failed", url=url, error=str(exc))


def _get_public_key(kid: str) -> Any | None:
    """Return cached public key for kid, refreshing if stale or if kid unknown."""
    if (time.monotonic() - _jwks_fetched_at) > _JWKS_TTL or kid not in _jwks_cache:
        _refresh_jwks()
    # If kid still missing after refresh the key is genuinely unknown
    return _jwks_cache.get(kid)


# ── Token payload ─────────────────────────────────────────────────────────────

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


# ── Verification ──────────────────────────────────────────────────────────────

def verify_supabase_jwt(token: str) -> TokenPayload:
    """
    Decode and verify a Supabase access token.

    Dispatch rules:
      ES256 + kid  → verify against JWKS public key (user access tokens)
      HS256        → verify against SUPABASE_JWT_SECRET   (legacy tokens)
      anything else → reject immediately

    Both paths enforce audience="authenticated" and issuer matching
    the configured Supabase URL. Raises HTTP 401 on any failure.
    """
    settings = get_settings()

    # Peek at the unverified header to choose the verification path.
    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        log.warning("jwt.malformed_header", error=str(exc))
        _raise_401(exc)

    alg: str = header.get("alg", "")
    kid: str | None = header.get("kid")

    try:
        if alg == "ES256":
            if not kid:
                raise InvalidTokenError("ES256 token is missing the kid header")
            public_key = _get_public_key(kid)
            if public_key is None:
                raise InvalidTokenError(f"Unknown key id: {kid!r}")
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["ES256"],
                audience=_AUDIENCE,
                issuer=_issuer(),
            )

        elif alg == "HS256":
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=_AUDIENCE,
                issuer=_issuer(),
            )

        else:
            raise InvalidTokenError(f"Unsupported algorithm: {alg!r}")

    except InvalidTokenError as exc:
        log.warning("jwt.verification_failed", alg=alg, kid=kid, error=str(exc))
        _raise_401(exc)

    sub: str | None = payload.get("sub")
    if not sub:
        log.warning("jwt.missing_sub_claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_meta: dict = payload.get("user_metadata", {})
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


def _raise_401(exc: Exception) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid token: {exc}",
        headers={"WWW-Authenticate": "Bearer"},
    ) from exc

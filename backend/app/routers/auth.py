"""
Auth router — post-OAuth user synchronisation + MCP OAuth callback.

Flows
─────
Frontend sync
  1. Frontend completes Supabase GitHub OAuth (supabase.auth.signInWithOAuth)
  2. Frontend receives session; provider_token is the GitHub OAuth token
  3. Frontend calls POST /v1/auth/sync with Authorization: Bearer <access_token>
     and body: { "provider_token": "<github_oauth_token>" }
  4. We upsert the User row and store the GitHub token for pipeline use

MCP OAuth (GET /v1/auth/mcp-callback)
  1. MCP /authorize redirects the user's browser to GitHub OAuth
  2. GitHub redirects here with code + state
  3. We exchange the code for a GitHub access token, fetch the user profile,
     look up / create the SIGNAL user, then issue an MCP authorization code
     and redirect to Claude's redirect_uri.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.config import get_settings
from app.core.deps import get_current_user
from app.database import get_db
from app.mcp.oauth import MCP_GITHUB_REDIRECT_URI, signal_oauth_provider
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


@router.get("/mcp-callback", response_model=None)
async def mcp_github_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse | HTMLResponse:
    """
    GitHub OAuth callback for MCP authentication.

    GitHub redirects here after the user authorises the SIGNAL GitHub OAuth App
    during an MCP sign-in flow.  We exchange the code, look up / create the
    SIGNAL user, issue an MCP authorization code, and redirect back to Claude.
    """
    if error:
        log.warning("mcp.oauth.github_error", error=error, description=error_description)
        return HTMLResponse(
            f"<h2>GitHub authorisation failed</h2><p>{error}: {error_description}</p>",
            status_code=400,
        )

    if not code or not state:
        return HTMLResponse("<h2>Missing code or state</h2>", status_code=400)

    settings = get_settings()

    # Exchange GitHub code for an access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": MCP_GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_data = token_resp.json()

    github_token = token_data.get("access_token")
    if not github_token:
        log.warning("mcp.oauth.no_github_token", response=token_data)
        return HTMLResponse("<h2>GitHub token exchange failed</h2>", status_code=400)

    # Fetch the GitHub user profile
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )
        gh_user = user_resp.json()

    github_username = gh_user.get("login")
    if not github_username:
        return HTMLResponse("<h2>Could not fetch GitHub user</h2>", status_code=400)

    # Look up or create the SIGNAL user
    result = await db.execute(
        select(User).where(User.github_username == github_username)
    )
    signal_user = result.scalar_one_or_none()
    if signal_user is None:
        signal_user = User(
            github_username=github_username,
            full_name=gh_user.get("name"),
            github_email=gh_user.get("email"),
            github_avatar=gh_user.get("avatar_url"),
            github_access_token=github_token,
        )
        db.add(signal_user)
        await db.flush()
        log.info("mcp.oauth.user_created", username=github_username)
    else:
        signal_user.github_access_token = github_token
        await db.flush()

    # Issue the MCP authorization code and get the redirect URL
    redirect_url = signal_oauth_provider.complete_authorization(
        github_state=state,
        github_username=github_username,
    )
    if redirect_url is None:
        log.warning("mcp.oauth.unknown_state", state=state)
        return HTMLResponse(
            "<h2>OAuth state expired or unknown</h2>"
            "<p>Please return to Claude and try connecting again.</p>",
            status_code=400,
        )

    log.info("mcp.oauth.complete", username=github_username)
    return RedirectResponse(redirect_url, status_code=302)

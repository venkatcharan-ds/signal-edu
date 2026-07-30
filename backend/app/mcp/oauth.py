"""
OAuth 2.1 Authorization Server for SIGNAL MCP.

Claude's Remote MCP connector requires OAuth 2.1 (MCP spec 2025-03-26).
This module provides a minimal standards-compliant implementation backed by
SIGNAL's existing GitHub OAuth app.

Flow
────
  1. Claude  →  GET /mcp/authorize?client_id=…&redirect_uri=…&state=…&code_challenge=…
  2. We store the pending MCP params, redirect to GitHub OAuth.
  3. GitHub  →  GET /v1/auth/mcp-callback?code=<github_code>&state=<github_state>
  4. We exchange the GitHub code for user info, look up / create the SIGNAL
     user, issue an MCP authorization code, and redirect back to Claude's
     redirect_uri with that code.
  5. Claude  →  POST /mcp/token  →  receives Bearer access token.
  6. Claude uses the Bearer token on all subsequent MCP requests.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

MCP_GITHUB_REDIRECT_URI = "https://signal-edu.onrender.com/v1/auth/mcp-callback"
_TOKEN_TTL = 3600 * 8  # 8 hours


# ── Data classes that extend the mcp base models ──────────────────────────────

@dataclass
class _MCPAuthCode(AuthorizationCode):
    pass


@dataclass
class _MCPAccessToken(AccessToken):
    pass


# ── Pending correlation between GitHub OAuth state and MCP request params ─────

@dataclass
class _Pending:
    client: OAuthClientInformationFull
    params: AuthorizationParams


# ── Provider ──────────────────────────────────────────────────────────────────

class SignalOAuthProvider(
    OAuthAuthorizationServerProvider[_MCPAuthCode, _MCPAccessToken, Any]
):
    """
    In-memory OAuth 2.1 AS.  State is lost on restart, which is fine — MCP
    sessions are short-lived and Claude will re-authenticate automatically.
    """

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._pending: dict[str, _Pending] = {}    # github_state → pending MCP auth
        self._codes: dict[str, _MCPAuthCode] = {}  # mcp_code → auth code
        self._tokens: dict[str, _MCPAccessToken] = {}  # token → access token

    # ── Dynamic client registration ───────────────────────────────────────────

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    async def get_client(
        self, client_id: str
    ) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    # ── Authorization ─────────────────────────────────────────────────────────

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """Return a URL to redirect the user's browser to."""
        from app.config import get_settings
        settings = get_settings()

        github_state = secrets.token_urlsafe(32)
        self._pending[github_state] = _Pending(client=client, params=params)

        return (
            "https://github.com/login/oauth/authorize"
            f"?client_id={settings.github_client_id}"
            f"&redirect_uri={MCP_GITHUB_REDIRECT_URI}"
            f"&scope=read%3Auser"
            f"&state={github_state}"
        )

    def complete_authorization(
        self, github_state: str, github_username: str
    ) -> str | None:
        """
        Called by the GitHub callback endpoint after the user authenticates.

        Looks up the pending MCP auth request for this github_state, issues an
        MCP authorization code, and returns the full redirect URL to send the
        browser to (Claude's redirect_uri with code + state appended).

        Returns None if the state is unknown or already consumed.
        """
        pending = self._pending.pop(github_state, None)
        if pending is None:
            return None

        mcp_code = secrets.token_urlsafe(32)
        self._codes[mcp_code] = _MCPAuthCode(
            code=mcp_code,
            scopes=pending.params.scopes or ["mcp"],
            expires_at=time.time() + 600,  # 10 minutes to exchange
            client_id=pending.client.client_id,
            code_challenge=pending.params.code_challenge,
            redirect_uri=pending.params.redirect_uri,
            redirect_uri_provided_explicitly=pending.params.redirect_uri_provided_explicitly,
            subject=github_username,
        )

        redirect_uri = str(pending.params.redirect_uri)
        sep = "&" if "?" in redirect_uri else "?"
        url = f"{redirect_uri}{sep}code={mcp_code}"
        if pending.params.state:
            url += f"&state={pending.params.state}"
        return url

    # ── Code / token lifecycle ────────────────────────────────────────────────

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> _MCPAuthCode | None:
        code = self._codes.get(authorization_code)
        if code is None or code.client_id != client.client_id:
            return None
        if code.expires_at < time.time():
            self._codes.pop(authorization_code, None)
            return None
        return code

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: _MCPAuthCode,
    ) -> OAuthToken:
        self._codes.pop(authorization_code.code, None)
        token = secrets.token_urlsafe(48)
        self._tokens[token] = _MCPAccessToken(
            token=token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + _TOKEN_TTL,
            subject=authorization_code.subject,
        )
        return OAuthToken(
            access_token=token,
            token_type="Bearer",
            expires_in=_TOKEN_TTL,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_access_token(self, token: str) -> _MCPAccessToken | None:
        at = self._tokens.get(token)
        if at is None:
            return None
        if at.expires_at and at.expires_at < time.time():
            self._tokens.pop(token, None)
            return None
        return at

    # ── Refresh tokens (not supported) ───────────────────────────────────────

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> None:
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: Any,
        scopes: list[str],
    ) -> OAuthToken:
        raise NotImplementedError("Refresh tokens are not supported.")

    async def revoke_token(
        self, token: _MCPAccessToken | Any
    ) -> None:
        t = token.token if hasattr(token, "token") else str(token)
        self._tokens.pop(t, None)
        self._codes.pop(t, None)


# ── Singleton shared between server.py and the callback router ────────────────
signal_oauth_provider = SignalOAuthProvider()

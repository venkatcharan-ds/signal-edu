"""
SIGNAL MCP server with OAuth 2.1 authentication.

Claude's Remote MCP connector requires OAuth 2.1 (MCP spec 2025-03-26).
The authorization flow is backed by GitHub OAuth — users authenticate with
GitHub and receive a short-lived Bearer token scoped to MCP requests.

Transport:  SSE (Server-Sent Events)
  GET  /mcp/sse         — Claude connects here
  POST /mcp/messages/   — message endpoint

OAuth endpoints (added automatically by the mcp library):
  GET  /mcp/.well-known/oauth-authorization-server  — discovery
  POST /mcp/register                                — dynamic client reg
  GET  /mcp/authorize                               — start auth flow
  POST /mcp/token                                   — exchange code for token

The root-level discovery redirect is in main.py:
  GET  /.well-known/oauth-authorization-server  → /mcp/.well-known/...
"""
from __future__ import annotations

from mcp.server import MCPServer
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from pydantic import AnyHttpUrl

from app.mcp import tools as t
from app.mcp.oauth import signal_oauth_provider

# ── Base URL ──────────────────────────────────────────────────────────────────
# issuer_url must equal the prefix where OAuth routes are served.
# With app.mount("/mcp", mcp_asgi_app), all OAuth routes live under /mcp.
_BASE = "https://signal-edu.onrender.com"
_MCP_URL = f"{_BASE}/mcp"

# ── Auth settings ─────────────────────────────────────────────────────────────
_auth = AuthSettings(
    issuer_url=AnyHttpUrl(_MCP_URL),
    client_registration_options=ClientRegistrationOptions(
        enabled=True,
        valid_scopes=["mcp"],
        default_scopes=["mcp"],
    ),
    resource_server_url=AnyHttpUrl(_MCP_URL),
)

# ── Server instance ───────────────────────────────────────────────────────────
mcp_server = MCPServer(
    name="signal-edu",
    title="SIGNAL EDU",
    instructions=(
        "SIGNAL is a capability-assessment platform that analyses a developer's "
        "public GitHub repositories and produces an evidence-based score across "
        "three dimensions: Technical Execution (TE), Problem Complexity (PC), and "
        "Communication Quality (CQ) on a 1.0–9.0 scale. "
        "Use these tools to retrieve profiles, inspect gap analyses against role "
        "templates, track analysis jobs, compare users, and trigger new analyses."
    ),
    version="1.0.0",
    auth=_auth,
    auth_server_provider=signal_oauth_provider,
)

# ── Tool registration ─────────────────────────────────────────────────────────
mcp_server.tool()(t.get_profile)
mcp_server.tool()(t.get_gap_analysis)
mcp_server.tool()(t.get_analysis_status)
mcp_server.tool()(t.list_analysis_jobs)
mcp_server.tool()(t.start_analysis)
mcp_server.tool()(t.compare_profiles)
mcp_server.tool()(t.get_role_templates)
mcp_server.tool()(t.get_repositories)

# ── ASGI app ──────────────────────────────────────────────────────────────────
# host='0.0.0.0' is required — the default '127.0.0.1' rejects external
# connections and would make the endpoint unreachable on Render.
mcp_asgi_app = mcp_server.sse_app(host="0.0.0.0")

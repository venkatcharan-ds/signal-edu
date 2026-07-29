"""
SIGNAL MCP server.

Creates a FastMCP instance and registers all tools defined in tools.py.
The SSE ASGI app (mcp_asgi_app) is mounted into the main FastAPI app in main.py.

Transport: SSE (Server-Sent Events)
  • Claude connects to  GET  /mcp/sse
  • Messages are posted  POST /mcp/messages/

To add a new tool: define the async function in tools.py, then call
mcp_server.tool()(your_function) at the bottom of this file.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp import tools as t

# ── Server instance ───────────────────────────────────────────────────────────

mcp_server = FastMCP(
    name="SIGNAL EDU",
    instructions=(
        "SIGNAL is a capability-assessment platform that analyses a developer's "
        "public GitHub repositories and produces an evidence-based score across "
        "three dimensions: Technical Execution (TE), Problem Complexity (PC), and "
        "Communication Quality (CQ) on a 1.0–9.0 scale. "
        "Use these tools to retrieve profiles, inspect gap analyses against role "
        "templates, track analysis jobs, compare users, and trigger new analyses."
    ),
)

# ── Tool registration ─────────────────────────────────────────────────────────
# Each call wraps the async function from tools.py — no logic lives here.

mcp_server.tool()(t.get_profile)
mcp_server.tool()(t.get_gap_analysis)
mcp_server.tool()(t.get_analysis_status)
mcp_server.tool()(t.list_analysis_jobs)
mcp_server.tool()(t.start_analysis)
mcp_server.tool()(t.compare_profiles)
mcp_server.tool()(t.get_role_templates)
mcp_server.tool()(t.get_repositories)

# ── ASGI app ──────────────────────────────────────────────────────────────────
# Exposed for mounting in main.py:
#   app.mount("/mcp", mcp_asgi_app)
#
# The SSE app adds two sub-routes:
#   GET  /sse        — event stream (Claude connects here)
#   POST /messages/  — message endpoint (Claude posts here)
#
# With the /mcp mount prefix these become:
#   GET  /mcp/sse
#   POST /mcp/messages/

mcp_asgi_app = mcp_server.sse_app()

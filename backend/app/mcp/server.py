"""
SIGNAL MCP server.

Uses MCPServer (mcp>=2.0.0) — the successor to FastMCP — and registers all
tools defined in tools.py.  The SSE ASGI app (mcp_asgi_app) is mounted into
the main FastAPI app in main.py.

Transport: SSE (Server-Sent Events)
  • Claude connects to  GET  /mcp/sse
  • Messages are posted  POST /mcp/messages/

To add a new tool: define the async function in tools.py, then register it
with mcp_server.tool()(your_function) at the bottom of this file.
"""
from __future__ import annotations

from mcp.server import MCPServer

from app.mcp import tools as t

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
)

# ── Tool registration ─────────────────────────────────────────────────────────
# mcp_server.tool() returns a decorator; wrapping the function registers it.

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
#
# The SSE app adds two sub-routes:
#   GET  /sse        — event stream (Claude connects here)
#   POST /messages/  — message posting endpoint
#
# With the /mcp mount prefix these become:
#   GET  /mcp/sse
#   POST /mcp/messages/

mcp_asgi_app = mcp_server.sse_app(host="0.0.0.0")

# MCP sub-package — exposes the ASGI app for mounting in main.py.
from app.mcp.server import mcp_asgi_app, mcp_server

__all__ = ["mcp_asgi_app", "mcp_server"]

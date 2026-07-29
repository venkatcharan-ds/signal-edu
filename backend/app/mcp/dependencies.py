"""
MCP dependency helpers.

FastMCP tools cannot use FastAPI's Depends() injection — they are plain async
functions. This module provides a context-manager-based DB session that tools
use directly, mirroring the pattern inside the pipeline orchestrator.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal


@asynccontextmanager
async def mcp_db_session():
    """
    Async context manager that yields a committed AsyncSession.

    Usage in a tool:
        async with mcp_db_session() as db:
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session

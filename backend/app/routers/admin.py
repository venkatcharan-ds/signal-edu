"""
Admin router — internal metrics for the SIGNAL competition dashboard.
Protected by a static API key (X-Admin-Key header).
Full implementation in Phase 5.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db

log = structlog.get_logger()
router = APIRouter()


def _verify_admin(x_admin_key: str = Header(...)) -> None:
    settings = get_settings()
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/metrics", dependencies=[Depends(_verify_admin)])
async def get_metrics(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Impact analytics for the competition dashboard.
    Returns: student count, capabilities extracted, avg gap scores,
    profile views, and capability-multiplier ratio.
    Full implementation in Phase 5.
    """
    raise HTTPException(status_code=501, detail="Coming in Phase 5")

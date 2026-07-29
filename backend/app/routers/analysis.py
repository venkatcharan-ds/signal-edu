"""
Analysis router — triggers the 5-stage capability pipeline and streams progress.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.models.analysis_job import AnalysisJob
from app.models.user import User
from app.pipeline.orchestrator import run_analysis
from app.schemas.analysis import AnalysisJobResponse, AnalysisProgressEvent, QuotaResponse

log = structlog.get_logger()
router = APIRouter()

# Statuses that indicate a job is actively running (blocks a new start)
_ACTIVE_STATUSES = ("queued", "github_fetch", "evidence_extract", "ai_analysis", "scoring")

# SSE tuning
_POLL_INTERVAL_S = 1.5
_MAX_STREAM_S = 600


# ── Quota helpers ─────────────────────────────────────────────────────────────

def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def _get_quota(db: AsyncSession, user: User) -> QuotaResponse:
    settings = get_settings()
    today = _today_start_utc()

    used_result = await db.execute(
        select(func.count(AnalysisJob.id)).where(
            AnalysisJob.user_id == user.id,
            AnalysisJob.started_at >= today,
        )
    )
    used_today = used_result.scalar_one()

    active_result = await db.execute(
        select(AnalysisJob.id)
        .where(
            AnalysisJob.user_id == user.id,
            AnalysisJob.status.in_(_ACTIVE_STATUSES),
        )
        .limit(1)
    )
    has_active = active_result.scalar_one_or_none() is not None

    limit = settings.daily_analysis_limit
    remaining = max(0, limit - used_today)

    return QuotaResponse(
        used_today=used_today,
        limit=limit,
        remaining=remaining,
        has_active_job=has_active,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuotaResponse:
    """Return the current user's daily analysis quota status."""
    return await _get_quota(db, user)


@router.post("/start", response_model=AnalysisJobResponse)
async def start_analysis(
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisJob:
    """
    Create an AnalysisJob, enqueue the pipeline as a background task, and
    return the job ID immediately.  Poll /status/{job_id} for real-time progress.

    Rate limits:
      - Only one concurrent analysis per user at a time.
      - Maximum daily_analysis_limit analyses per user per calendar day (UTC).
    """
    settings = get_settings()

    if not user.github_access_token:
        raise HTTPException(
            status_code=422,
            detail="No GitHub token on file. Please sign out and sign in again.",
        )

    # ── Check for an already-active job ────────────────────────────────────
    active_result = await db.execute(
        select(AnalysisJob.id)
        .where(
            AnalysisJob.user_id == user.id,
            AnalysisJob.status.in_(_ACTIVE_STATUSES),
        )
        .limit(1)
    )
    if active_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=429,
            detail="An analysis is already running. Wait for it to complete before starting another.",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(settings.daily_analysis_limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    # ── Check daily quota ────────────────────────────────────────────────────
    today = _today_start_utc()
    used_result = await db.execute(
        select(func.count(AnalysisJob.id)).where(
            AnalysisJob.user_id == user.id,
            AnalysisJob.started_at >= today,
        )
    )
    used_today = used_result.scalar_one()
    limit = settings.daily_analysis_limit

    if used_today >= limit:
        tomorrow = today + timedelta(days=1)
        retry_after = int((tomorrow - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=f"Daily analysis limit reached ({limit}/day). Quota resets at midnight UTC.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(tomorrow.timestamp())),
            },
        )

    # ── Create and enqueue the job ───────────────────────────────────────────
    job = AnalysisJob(
        user_id=user.id,
        status="queued",
        current_step="Queued — waiting to start",
        progress_pct=0,
    )
    db.add(job)
    await db.flush()
    # Commit NOW so the row is visible to the background task's separate session.
    # BackgroundTasks run after the HTTP response is sent but before get_db's
    # post-yield commit() fires — without this explicit commit the background
    # task opens a new READ COMMITTED connection and finds no row.
    await db.commit()
    log.info("analysis.queued", job_id=str(job.id), user=user.github_username)

    # Attach quota headers to the 202 response
    remaining_after = max(0, limit - (used_today + 1))
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining_after)

    # Schedule the pipeline — it opens its own session via AsyncSessionLocal
    background_tasks.add_task(run_analysis, job.id, AsyncSessionLocal)

    return job


@router.get("/status/{job_id}")
async def analysis_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Server-Sent Events stream of analysis pipeline progress.
    Polls the DB every _POLL_INTERVAL_S seconds until the job is terminal.
    """
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id,
            AnalysisJob.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    async def event_stream():
        elapsed = 0.0
        last_pct = -1

        while elapsed < _MAX_STREAM_S:
            async with AsyncSessionLocal() as poll_db:
                row = await poll_db.get(AnalysisJob, job_id)

            if row is None:
                yield _sse(AnalysisProgressEvent(
                    step="failed",
                    label="Job disappeared unexpectedly",
                    progress=0,
                ))
                break

            if row.progress_pct != last_pct:
                last_pct = row.progress_pct
                event = AnalysisProgressEvent(
                    step=row.status,
                    label=row.current_step or row.status,
                    progress=row.progress_pct,
                    error=row.error_message if row.status == "failed" else None,
                )
                yield _sse(event)

            if row.status in ("complete", "failed"):
                break

            await asyncio.sleep(_POLL_INTERVAL_S)
            elapsed += _POLL_INTERVAL_S

        if elapsed >= _MAX_STREAM_S:
            yield _sse(AnalysisProgressEvent(
                step="failed",
                label="Analysis timed out",
                progress=0,
            ))

        yield _sse_close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=list[AnalysisJobResponse])
async def analysis_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AnalysisJob]:
    """Return all past analysis jobs for the current user, newest first."""
    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.user_id == user.id)
        .order_by(AnalysisJob.started_at.desc())
        .limit(20)
    )
    return list(result.scalars().all())


# ── helpers ──────────────────────────────────────────────────────────────────

def _sse(event: AnalysisProgressEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


def _sse_close() -> str:
    return "data: [DONE]\n\n"

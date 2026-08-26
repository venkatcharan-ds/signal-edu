"""
Analysis router — enqueues pipeline jobs and streams progress.
Job execution is handled exclusively by the background worker service.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.models.analysis_job import AnalysisJob
from app.models.user import User
from app.schemas.analysis import AnalysisJobResponse, AnalysisProgressEvent, QuotaResponse

log = structlog.get_logger()
router = APIRouter()

# Active statuses — any of these means the user already has a job in flight
_ACTIVE_STATUSES = ("queued", "claimed", "github_fetch", "evidence_extract", "ai_analysis", "scoring")

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
            AnalysisJob.is_test == False,  # noqa: E712
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
    test: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisJob:
    """
    Create an AnalysisJob and enqueue it for the background worker.
    Returns the job ID immediately — poll /status/{job_id} for progress.

    Rate limits:
      - Only one concurrent analysis per user at a time (queued, claimed, or running).
      - Maximum daily_analysis_limit analyses per user per calendar day (UTC).
        Test runs (test=true) are exempt from the daily quota but require
        is_super_admin=true on the user account.
    """
    settings = get_settings()

    if not user.github_access_token:
        raise HTTPException(
            status_code=422,
            detail="No GitHub token on file. Please sign out and sign in again.",
        )

    # ── Gate test mode to super-admins only (backend-enforced) ──────────────
    if test and not user.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Developer test mode is not authorized for this account.",
        )

    # ── Check for an already-active job (applies to all runs, including test) ─
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

    # ── Check daily quota (skipped for authorised test runs) ─────────────────
    today = _today_start_utc()
    limit = settings.daily_analysis_limit
    used_today = 0

    if not test:
        used_result = await db.execute(
            select(func.count(AnalysisJob.id)).where(
                AnalysisJob.user_id == user.id,
                AnalysisJob.started_at >= today,
                AnalysisJob.is_test == False,  # noqa: E712
            )
        )
        used_today = used_result.scalar_one()

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
        current_step="Queued — waiting for a worker",
        progress_pct=0,
        is_test=test,
    )
    db.add(job)
    await db.flush()
    # Commit NOW so the worker's separate session can see the row immediately.
    await db.commit()
    log.info(
        "analysis.queued",
        job_id=str(job.id),
        user=user.github_username,
        test=test,
    )

    # Attach quota headers to the response (reflects real-quota state only)
    remaining_after = max(0, limit - (used_today + (0 if test else 1)))
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining_after)

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
    Includes queue_position when the job is waiting to be picked up.
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

            queue_position = 0
            if row.status == "queued":
                async with AsyncSessionLocal() as pos_db:
                    pos_result = await pos_db.execute(
                        select(func.count(AnalysisJob.id)).where(
                            AnalysisJob.status == "queued",
                            AnalysisJob.next_retry_at <= datetime.now(timezone.utc),
                            AnalysisJob.started_at < row.started_at,
                        )
                    )
                    queue_position = pos_result.scalar_one() + 1

            if row.progress_pct != last_pct or queue_position > 0:
                last_pct = row.progress_pct

                if row.status == "queued":
                    label = f"Waiting — position {queue_position} in queue"
                else:
                    label = row.current_step or row.status

                event = AnalysisProgressEvent(
                    step=row.status,
                    label=label,
                    progress=row.progress_pct,
                    queue_position=queue_position,
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

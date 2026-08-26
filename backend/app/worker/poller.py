"""
PostgreSQL-backed job poller for the SIGNAL analysis queue.

Uses SELECT ... FOR UPDATE SKIP LOCKED to atomically claim jobs without
race conditions, even across multiple worker processes.

Concurrency model:
  - One poll loop per worker process
  - Up to settings.max_concurrent_jobs pipelines run simultaneously per process
  - Active tasks are tracked in a set; the loop checks len(active) < max before claiming
  - Claimed jobs that exceed settings.job_claim_timeout_seconds are recovered on
    startup and periodically (worker crash / Render restart recovery)
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.analysis_job import AnalysisJob
from app.pipeline.orchestrator import run_analysis

log = structlog.get_logger()

# How often to run the stale-job recovery sweep (in addition to startup)
_RECOVERY_INTERVAL_S = 300  # 5 minutes


async def try_claim_job(
    session_factory: async_sessionmaker[AsyncSession],
    worker_id: str,
) -> uuid.UUID | None:
    """
    Atomically claim one queued job using FOR UPDATE SKIP LOCKED.
    Returns the job_id if a job was claimed, None if the queue is empty.
    Two concurrent callers will never receive the same job_id.
    """
    now = datetime.now(timezone.utc)
    async with session_factory() as db:
        async with db.begin():
            result = await db.execute(
                select(AnalysisJob.id)
                .where(
                    AnalysisJob.status == "queued",
                    AnalysisJob.next_retry_at <= now,
                )
                .order_by(AnalysisJob.started_at.asc())  # FIFO — no test-job priority
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            row = result.one_or_none()
            if row is None:
                return None

            job_id: uuid.UUID = row[0]
            await db.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == job_id)
                .values(
                    status="claimed",
                    claimed_at=now,
                    worker_id=worker_id,
                )
            )
            return job_id


async def recover_stale_jobs(
    session_factory: async_sessionmaker[AsyncSession],
    claim_timeout_seconds: int,
) -> int:
    """
    Re-queue jobs that were claimed by a worker that died without completing them.
    Increments retry_count so eventually-unrecoverable jobs still reach max retries.
    Returns the number of jobs recovered.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=claim_timeout_seconds)
    async with session_factory() as db:
        async with db.begin():
            result = await db.execute(
                update(AnalysisJob)
                .where(
                    AnalysisJob.status == "claimed",
                    AnalysisJob.claimed_at < cutoff,
                )
                .values(
                    status="queued",
                    current_step="Recovered after worker restart — will retry shortly",
                    claimed_at=None,
                    worker_id=None,
                    retry_count=AnalysisJob.retry_count + 1,
                    next_retry_at=datetime.now(timezone.utc) + timedelta(seconds=60),
                )
                .returning(AnalysisJob.id)
            )
            recovered = result.fetchall()
    return len(recovered)


async def poll_loop(
    session_factory: async_sessionmaker[AsyncSession],
    worker_id: str,
    max_concurrent_jobs: int,
    poll_interval_seconds: float,
    claim_timeout_seconds: int,
) -> None:
    """
    Main worker poll loop. Runs indefinitely until cancelled.
    Tracks active pipeline tasks and claims new jobs when capacity allows.
    """
    bound = log.bind(worker_id=worker_id)

    # Recover stale jobs on startup before processing anything new
    recovered = await recover_stale_jobs(session_factory, claim_timeout_seconds)
    if recovered:
        bound.info("worker.recovered_stale_jobs_on_startup", count=recovered)

    active: set[asyncio.Task] = set()
    last_recovery = asyncio.get_event_loop().time()

    while True:
        # Periodic stale-job sweep (handles workers that crash between sweeps)
        now_monotonic = asyncio.get_event_loop().time()
        if now_monotonic - last_recovery >= _RECOVERY_INTERVAL_S:
            recovered = await recover_stale_jobs(session_factory, claim_timeout_seconds)
            if recovered:
                bound.info("worker.recovered_stale_jobs_periodic", count=recovered)
            last_recovery = now_monotonic

        # Prune completed/cancelled tasks
        active = {t for t in active if not t.done()}

        if len(active) < max_concurrent_jobs:
            job_id = await try_claim_job(session_factory, worker_id)
            if job_id is not None:
                bound.info("worker.job_claimed", job_id=str(job_id))
                task = asyncio.create_task(
                    run_analysis(job_id, session_factory),
                    name=f"pipeline-{job_id}",
                )
                active.add(task)
                # Immediately loop back to try claiming another if capacity allows
                continue

        await asyncio.sleep(poll_interval_seconds)

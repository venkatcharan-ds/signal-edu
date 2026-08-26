"""
Worker entry point.

Start with:
  python -m app.worker.main

Or via the Render Background Worker start command.
"""
from __future__ import annotations

import asyncio
import uuid

import structlog

from app.config import get_settings
from app.core.logging import configure_logging
from app.database import AsyncSessionLocal
from app.worker.poller import poll_loop

configure_logging()
log = structlog.get_logger()


async def main() -> None:
    settings = get_settings()
    worker_id = str(uuid.uuid4())

    log.info(
        "worker.start",
        worker_id=worker_id,
        max_concurrent_jobs=settings.max_concurrent_jobs,
        max_job_retries=settings.max_job_retries,
        poll_interval_s=settings.worker_poll_interval_seconds,
        claim_timeout_s=settings.job_claim_timeout_seconds,
    )

    await poll_loop(
        session_factory=AsyncSessionLocal,
        worker_id=worker_id,
        max_concurrent_jobs=settings.max_concurrent_jobs,
        poll_interval_seconds=settings.worker_poll_interval_seconds,
        claim_timeout_seconds=settings.job_claim_timeout_seconds,
    )


if __name__ == "__main__":
    asyncio.run(main())

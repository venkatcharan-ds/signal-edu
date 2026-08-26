"""Add durable queue fields to analysis_jobs.

Enables PostgreSQL-backed job queue with atomic claiming (FOR UPDATE SKIP LOCKED),
retry tracking with exponential backoff, and stale-job recovery after worker crashes.

New columns:
  claimed_at     — timestamp when a worker claimed the job; NULL = unclaimed
  worker_id      — UUID string of the worker that claimed the job
  retry_count    — number of previous execution attempts (0 = never run)
  next_retry_at  — earliest time the job may be claimed again (used for backoff)

Status 'claimed' is added to the check constraint — it represents a job that
has been atomically claimed by a worker and is being dispatched but not yet
executing a named pipeline stage.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision     = "0007"
down_revision = "0006"
branch_labels = None
depends_on    = None

_NEW_STATUSES = (
    "queued", "claimed", "github_fetch", "evidence_extract",
    "ai_analysis", "scoring", "complete", "failed",
)


def upgrade() -> None:
    op.add_column("analysis_jobs", sa.Column("claimed_at",    sa.DateTime(timezone=True), nullable=True))
    op.add_column("analysis_jobs", sa.Column("worker_id",     sa.String(100),             nullable=True))
    op.add_column("analysis_jobs", sa.Column("retry_count",   sa.Integer(),               nullable=False, server_default="0"))
    op.add_column("analysis_jobs", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))

    # Widen the status check constraint to include 'claimed'
    op.drop_constraint("ck_analysis_jobs_status", "analysis_jobs", type_="check")
    op.create_check_constraint(
        "ck_analysis_jobs_status",
        "analysis_jobs",
        f"status IN {_NEW_STATUSES}",
    )

    # Partial index to make the worker poll query fast
    op.create_index(
        "idx_analysis_jobs_queue_poll",
        "analysis_jobs",
        ["next_retry_at", "started_at"],
        postgresql_where=sa.text("status = 'queued'"),
    )


def downgrade() -> None:
    op.drop_index("idx_analysis_jobs_queue_poll", table_name="analysis_jobs")

    op.drop_constraint("ck_analysis_jobs_status", "analysis_jobs", type_="check")
    _OLD_STATUSES = (
        "queued", "github_fetch", "evidence_extract",
        "ai_analysis", "scoring", "complete", "failed",
    )
    op.create_check_constraint(
        "ck_analysis_jobs_status",
        "analysis_jobs",
        f"status IN {_OLD_STATUSES}",
    )

    op.drop_column("analysis_jobs", "next_retry_at")
    op.drop_column("analysis_jobs", "retry_count")
    op.drop_column("analysis_jobs", "worker_id")
    op.drop_column("analysis_jobs", "claimed_at")

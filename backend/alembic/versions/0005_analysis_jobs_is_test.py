"""Add is_test flag to analysis_jobs.

Allows developer/admin accounts to run test analyses that do not consume
the normal daily quota.  Normal analyses default to is_test=FALSE.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision     = "0005"
down_revision = "0004"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "is_test",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "is_test")

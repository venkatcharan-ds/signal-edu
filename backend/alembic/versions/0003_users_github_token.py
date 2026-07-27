"""Add github_access_token to users table.

The GitHub provider token captured at OAuth time is stored here so the
analysis pipeline can call the GitHub API on the user's behalf without
requiring them to be online.

In production this column should be encrypted at rest (e.g. pgcrypto).

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-24
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision     = "0003"
down_revision = "0002"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("github_access_token", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "github_access_token")

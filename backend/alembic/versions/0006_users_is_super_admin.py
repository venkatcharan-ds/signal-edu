"""Add is_super_admin flag to public.users.

Enables backend-enforced developer test mode — only accounts with
is_super_admin=TRUE can invoke POST /analysis/start?test=true.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision     = "0006"
down_revision = "0005"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_super_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_super_admin")

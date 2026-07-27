"""Add updated_at trigger and performance indexes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-23
"""
from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── updated_at auto-trigger ────────────────────────────────────────────────
    # Shared trigger function — reusable for any table with an updated_at column
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    # ── JSONB GIN indexes (enables fast @> containment queries) ───────────────
    # e.g. SELECT * FROM users WHERE resume_skills @> '["Python"]'
    op.execute("""
        CREATE INDEX idx_users_resume_skills_gin
        ON users USING GIN (resume_skills);
    """)

    # e.g. SELECT * FROM repositories WHERE languages @> '{"Python": 1}'
    op.execute("""
        CREATE INDEX idx_repositories_languages_gin
        ON repositories USING GIN (languages);
    """)

    # ── Partial index — only the current profile per user ─────────────────────
    # Replaces the composite index from 0001 with a smaller, faster partial index
    op.execute("""
        DROP INDEX IF EXISTS idx_capability_profiles_user_current;
    """)
    op.execute("""
        CREATE UNIQUE INDEX idx_capability_profiles_current_per_user
        ON capability_profiles (user_id)
        WHERE is_current = TRUE;
    """)

    # ── Recommendations lookup by gap_analysis ────────────────────────────────
    op.create_index(
        "idx_recommendations_gap",
        "recommendations",
        ["gap_analysis_id"],
    )

    # ── Artifacts lookup by user + type ───────────────────────────────────────
    op.create_index(
        "idx_artifacts_user_type",
        "artifacts",
        ["user_id", "artifact_type"],
    )

    # ── Role templates slug lookup ────────────────────────────────────────────
    op.create_index(
        "idx_role_templates_slug",
        "role_templates",
        ["slug"],
    )


def downgrade() -> None:
    op.drop_index("idx_role_templates_slug",   table_name="role_templates")
    op.drop_index("idx_artifacts_user_type",   table_name="artifacts")
    op.drop_index("idx_recommendations_gap",   table_name="recommendations")

    op.execute("DROP INDEX IF EXISTS idx_capability_profiles_current_per_user;")
    op.execute("""
        CREATE INDEX idx_capability_profiles_user_current
        ON capability_profiles (user_id, is_current);
    """)

    op.execute("DROP INDEX IF EXISTS idx_repositories_languages_gin;")
    op.execute("DROP INDEX IF EXISTS idx_users_resume_skills_gin;")
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users;")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at;")

"""Initial schema — all SIGNAL tables.

Revision ID: 0001
Revises:
Create Date: 2026-06-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("github_id",       sa.BigInteger(), nullable=False),
        sa.Column("github_username", sa.String(255),  nullable=False),
        sa.Column("github_email",    sa.String(255)),
        sa.Column("github_avatar",   sa.String(500)),
        sa.Column("full_name",       sa.String(255)),
        sa.Column("institution",     sa.String(255)),
        sa.Column("resume_skills",   postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("github_id",       name="uq_users_github_id"),
        sa.UniqueConstraint("github_username", name="uq_users_github_username"),
    )

    # ── repositories ──────────────────────────────────────────────────────────
    op.create_table(
        "repositories",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",             postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("github_repo_id",      sa.BigInteger(), nullable=False),
        sa.Column("name",                sa.String(255),  nullable=False),
        sa.Column("full_name",           sa.String(255),  nullable=False),
        sa.Column("description",         sa.Text()),
        sa.Column("url",                 sa.Text(),       nullable=False),
        sa.Column("languages",           postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("commit_count",        sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("last_commit_at",      sa.DateTime(timezone=True)),
        sa.Column("has_readme",          sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("readme_content",      sa.Text()),
        sa.Column("readme_word_count",   sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("has_tests",           sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("has_ci",              sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("has_deployment_config", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_fork",             sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("stars",               sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("raw_github_data",     postgresql.JSONB()),
        sa.Column("fetched_at",          sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("github_repo_id", name="uq_repositories_github_repo_id"),
    )
    op.create_index("idx_repositories_user", "repositories", ["user_id"])

    # ── artifacts ─────────────────────────────────────────────────────────────
    op.create_table(
        "artifacts",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(50),  nullable=False),
        sa.Column("title",         sa.String(500)),
        sa.Column("source_url",    sa.Text()),
        sa.Column("storage_path",  sa.Text()),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("word_count",    sa.Integer(), server_default="0"),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "artifact_type IN ('pdf','link','certificate','project_report')",
            name="ck_artifacts_type",
        ),
    )
    op.create_index("idx_artifacts_user", "artifacts", ["user_id"])

    # ── analysis_jobs ─────────────────────────────────────────────────────────
    op.create_table(
        "analysis_jobs",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status",        sa.String(50), nullable=False, server_default="queued"),
        sa.Column("current_step",  sa.String(100)),
        sa.Column("progress_pct",  sa.Integer(),  nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at",  sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('queued','github_fetch','evidence_extract','ai_analysis','scoring','complete','failed')",
            name="ck_analysis_jobs_status",
        ),
    )
    op.create_index("idx_analysis_jobs_user_status", "analysis_jobs", ["user_id", "status"])

    # ── capability_profiles ───────────────────────────────────────────────────
    op.create_table(
        "capability_profiles",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",               postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",                postgresql.UUID(as_uuid=True)),
        sa.Column("is_current",            sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("technical_execution",   sa.Numeric(3, 1)),
        sa.Column("problem_complexity",    sa.Numeric(3, 1)),
        sa.Column("communication_quality", sa.Numeric(3, 1)),
        sa.Column("te_confidence",         sa.Numeric(3, 2)),
        sa.Column("pc_confidence",         sa.Numeric(3, 2)),
        sa.Column("cq_confidence",         sa.Numeric(3, 2)),
        sa.Column("te_percentile",         sa.Integer()),
        sa.Column("pc_percentile",         sa.Integer()),
        sa.Column("cq_percentile",         sa.Integer()),
        sa.Column("objective_signals",     postgresql.JSONB()),
        sa.Column("verified_capabilities", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("raw_ai_response",       postgresql.JSONB()),
        sa.Column("created_at",            sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"],  ["analysis_jobs.id"]),
        sa.CheckConstraint("technical_execution   BETWEEN 1.0 AND 9.0", name="ck_cp_te"),
        sa.CheckConstraint("problem_complexity    BETWEEN 1.0 AND 9.0", name="ck_cp_pc"),
        sa.CheckConstraint("communication_quality BETWEEN 1.0 AND 9.0", name="ck_cp_cq"),
    )
    op.create_index("idx_capability_profiles_user_current", "capability_profiles", ["user_id", "is_current"])

    # ── evidence_citations ────────────────────────────────────────────────────
    op.create_table(
        "evidence_citations",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension",         sa.String(50),  nullable=False),
        sa.Column("citation_text",     sa.Text(),      nullable=False),
        sa.Column("artifact_type",     sa.String(50)),
        sa.Column("artifact_ref",      sa.Text()),
        sa.Column("score_contribution", sa.Numeric(3, 1)),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["profile_id"], ["capability_profiles.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "dimension IN ('technical_execution','problem_complexity','communication_quality')",
            name="ck_evidence_citations_dimension",
        ),
    )
    op.create_index("idx_evidence_citations_profile", "evidence_citations", ["profile_id"])

    # ── role_templates ────────────────────────────────────────────────────────
    op.create_table(
        "role_templates",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug",             sa.String(100), nullable=False),
        sa.Column("title",            sa.String(255), nullable=False),
        sa.Column("te_threshold",     sa.Numeric(3, 1), nullable=False),
        sa.Column("pc_threshold",     sa.Numeric(3, 1), nullable=False),
        sa.Column("cq_threshold",     sa.Numeric(3, 1), nullable=False),
        sa.Column("required_signals", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("description",      sa.Text()),
        sa.UniqueConstraint("slug", name="uq_role_templates_slug"),
    )

    # ── gap_analyses ──────────────────────────────────────────────────────────
    op.create_table(
        "gap_analyses",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("te_gap",        sa.Numeric(3, 1)),
        sa.Column("pc_gap",        sa.Numeric(3, 1)),
        sa.Column("cq_gap",        sa.Numeric(3, 1)),
        sa.Column("overall_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["profile_id"], ["capability_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"],    ["role_templates.id"]),
    )
    op.create_index("idx_gap_analyses_profile", "gap_analyses", ["profile_id"])

    # ── recommendations ───────────────────────────────────────────────────────
    op.create_table(
        "recommendations",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("gap_analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension",       sa.String(50),  nullable=False),
        sa.Column("priority",        sa.Integer(),   nullable=False),
        sa.Column("title",           sa.String(500), nullable=False),
        sa.Column("description",     sa.Text(),      nullable=False),
        sa.Column("evidence_type",   sa.String(100)),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["gap_analysis_id"], ["gap_analyses.id"], ondelete="CASCADE"),
    )

    # ── profile_views ─────────────────────────────────────────────────────────
    op.create_table(
        "profile_views",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("viewer_ip",    sa.String(45)),
        sa.Column("is_logged_in", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("viewed_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_profile_views_user_time", "profile_views", ["user_id", "viewed_at"])


def downgrade() -> None:
    op.drop_table("profile_views")
    op.drop_table("recommendations")
    op.drop_table("gap_analyses")
    op.drop_table("role_templates")
    op.drop_table("evidence_citations")
    op.drop_table("capability_profiles")
    op.drop_table("analysis_jobs")
    op.drop_table("artifacts")
    op.drop_table("repositories")
    op.drop_table("users")

"""Seed role_templates with 10 industry roles.

Uses INSERT … ON CONFLICT (slug) DO UPDATE so the migration is safe to run
against a database that already has partial seed data — it refreshes
thresholds and descriptions without touching FK-linked rows.

Deterministic UUIDs (10000000-0000-4000-8000-0000000000XX) ensure:
  - downgrade() can identify and delete exactly these rows
  - re-running upgrade() never creates duplicates

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision     = "0004"
down_revision = "0003"
branch_labels = None
depends_on    = None

# ── Role data ─────────────────────────────────────────────────────────────────
# Keep in sync with app/db/seed.py.  Duplicated here intentionally so the
# migration has no runtime import dependency on application code.

_ROLES = [
    {
        "id":               "10000000-0000-4000-8000-000000000001",
        "slug":             "data-scientist",
        "title":            "Data Scientist",
        "te_threshold":     5.5,
        "pc_threshold":     6.5,
        "cq_threshold":     5.5,
        "required_signals": '["has_readme","has_tests"]',
        "description": (
            "Transforms raw data into actionable insight through statistical "
            "modelling, hypothesis testing, and clear communication of findings. "
            "Requires Python or R proficiency, reproducible analysis workflows, "
            "and the ability to explain complex results to non-technical audiences."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-000000000002",
        "slug":             "ml-engineer",
        "title":            "Machine Learning Engineer",
        "te_threshold":     6.5,
        "pc_threshold":     6.5,
        "cq_threshold":     5.0,
        "required_signals": '["has_tests","has_ci","has_deployment_config"]',
        "description": (
            "Designs, trains, and ships machine learning models to production at "
            "scale. Requires strong software engineering foundations, MLOps "
            "practices (versioning, monitoring, CI), and experience with "
            "distributed training frameworks such as PyTorch or JAX."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-000000000003",
        "slug":             "ai-engineer",
        "title":            "AI Engineer",
        "te_threshold":     6.0,
        "pc_threshold":     5.5,
        "cq_threshold":     5.5,
        "required_signals": '["has_readme","has_tests"]',
        "description": (
            "Builds AI-powered products by integrating LLMs, embedding models, "
            "and retrieval systems into production applications. Requires API "
            "design skills, prompt engineering discipline, evaluation frameworks, "
            "and the ability to document AI behaviour and limitations clearly."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-000000000004",
        "slug":             "data-analyst",
        "title":            "Data Analyst",
        "te_threshold":     4.0,
        "pc_threshold":     4.5,
        "cq_threshold":     6.0,
        "required_signals": '["has_readme"]',
        "description": (
            "Extracts insight from structured data using SQL, Python or R, and "
            "BI tooling. Communication quality is the primary differentiator: "
            "dashboards, reports, and data stories must be clear, accurate, and "
            "targeted at business stakeholders."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-000000000005",
        "slug":             "backend-engineer",
        "title":            "Backend Engineer",
        "te_threshold":     6.5,
        "pc_threshold":     5.5,
        "cq_threshold":     4.5,
        "required_signals": '["has_tests","has_ci"]',
        "description": (
            "Designs and operates server-side systems: REST/gRPC APIs, relational "
            "databases, message queues, and caching layers. Requires test-driven "
            "development, CI pipelines, and the ability to reason about "
            "performance, reliability, and security under production load."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-000000000006",
        "slug":             "full-stack-developer",
        "title":            "Full Stack Developer",
        "te_threshold":     5.5,
        "pc_threshold":     5.0,
        "cq_threshold":     5.0,
        "required_signals": '["has_readme","has_deployment_config"]',
        "description": (
            "Delivers end-to-end web features across frontend (React/Vue/Svelte) "
            "and backend (Node/Python/Go). Breadth is the expectation: ability to "
            "ship a complete user-facing feature from database schema to deployed "
            "UI without handing off at layer boundaries."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-000000000007",
        "slug":             "devops-engineer",
        "title":            "DevOps Engineer",
        "te_threshold":     6.5,
        "pc_threshold":     5.5,
        "cq_threshold":     5.5,
        "required_signals": '["has_ci","has_deployment_config"]',
        "description": (
            "Builds and operates the infrastructure that lets engineering teams "
            "ship safely and quickly. Core competencies: container orchestration "
            "(Docker/Kubernetes), CI/CD pipelines, infrastructure-as-code "
            "(Terraform/Pulumi), and incident runbook authoring."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-000000000008",
        "slug":             "product-manager",
        "title":            "Product Manager",
        "te_threshold":     3.0,
        "pc_threshold":     4.5,
        "cq_threshold":     7.0,
        "required_signals": '["has_readme"]',
        "description": (
            "Defines what gets built and why. Technical literacy enables credible "
            "conversations with engineers, but Communication Quality is the primary "
            "signal: PRDs, user-research docs, roadmaps, and stakeholder updates "
            "must be precise, structured, and persuasive."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-000000000009",
        "slug":             "research-engineer",
        "title":            "Research Engineer",
        "te_threshold":     7.0,
        "pc_threshold":     7.5,
        "cq_threshold":     6.0,
        "required_signals": '["has_tests","has_readme"]',
        "description": (
            "Implements novel algorithms and systems at the boundary between "
            "research and engineering. Requires advanced programming skills "
            "(low-level systems or high-performance computing), the ability to "
            "tackle genuinely open problems, and paper-quality written communication "
            "of methods and results."
        ),
    },
    {
        "id":               "10000000-0000-4000-8000-00000000000a",
        "slug":             "software-engineer",
        "title":            "Software Engineer",
        "te_threshold":     5.0,
        "pc_threshold":     4.5,
        "cq_threshold":     4.5,
        "required_signals": '["has_tests"]',
        "description": (
            "The generalist entry point for professional software development. "
            "Requires solid programming fundamentals, data structure and algorithm "
            "knowledge, readable code with tests, and the ability to collaborate "
            "effectively through pull requests and code review."
        ),
    },
]

_SLUGS = [r["slug"] for r in _ROLES]


def upgrade() -> None:
    conn = op.get_bind()

    for role in _ROLES:
        conn.execute(
            sa.text(
                """
                INSERT INTO role_templates
                    (id, slug, title,
                     te_threshold, pc_threshold, cq_threshold,
                     required_signals, description)
                VALUES
                    (:id, :slug, :title,
                     :te, :pc, :cq,
                     CAST(:signals AS jsonb), :description)
                ON CONFLICT (slug) DO UPDATE SET
                    title            = EXCLUDED.title,
                    te_threshold     = EXCLUDED.te_threshold,
                    pc_threshold     = EXCLUDED.pc_threshold,
                    cq_threshold     = EXCLUDED.cq_threshold,
                    required_signals = EXCLUDED.required_signals,
                    description      = EXCLUDED.description
                """
            ),
            {
                "id":          role["id"],
                "slug":        role["slug"],
                "title":       role["title"],
                "te":          role["te_threshold"],
                "pc":          role["pc_threshold"],
                "cq":          role["cq_threshold"],
                "signals":     role["required_signals"],
                "description": role["description"],
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM role_templates WHERE slug = ANY(:slugs)"),
        {"slugs": _SLUGS},
    )

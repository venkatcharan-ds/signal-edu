"""
SIGNAL role template seed data — single source of truth.

Every deliverable (Alembic migration, startup seeder, standalone script,
SQL file) derives its data from ROLE_TEMPLATES defined here.

Threshold design rationale (1.0 – 9.0 scale):
  TE  Technical Execution   — code quality, tooling, deployment practice
  PC  Problem Complexity    — scope and depth of problems solved
  CQ  Communication Quality — documentation, README, project clarity

Scores above 7.0 require genuinely exceptional GitHub signals and strong
Claude AI analysis.  Scores below 3.5 indicate early-career / adjacent roles.

required_signals values map to GitHubEngine detection results:
  "has_tests"             — test suite detected via file-path patterns
  "has_ci"                — CI workflow detected (.github/workflows etc.)
  "has_deployment_config" — Dockerfile / fly.toml / Procfile etc. found
  "has_readme"            — README present in repository
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role_template import RoleTemplate

log = structlog.get_logger()

# ── Deterministic UUIDs ───────────────────────────────────────────────────────
# Using fixed UUIDs so the migration downgrade can target rows by primary key
# and so re-seeding never creates duplicates.

ROLE_TEMPLATES: list[dict] = [
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000001"),
        "slug":             "data-scientist",
        "title":            "Data Scientist",
        "te_threshold":     Decimal("5.5"),
        "pc_threshold":     Decimal("6.5"),
        "cq_threshold":     Decimal("5.5"),
        "required_signals": ["has_readme", "has_tests"],
        "description": (
            "Transforms raw data into actionable insight through statistical "
            "modelling, hypothesis testing, and clear communication of findings. "
            "Requires Python or R proficiency, reproducible analysis workflows, "
            "and the ability to explain complex results to non-technical audiences."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000002"),
        "slug":             "ml-engineer",
        "title":            "Machine Learning Engineer",
        "te_threshold":     Decimal("6.5"),
        "pc_threshold":     Decimal("6.5"),
        "cq_threshold":     Decimal("5.0"),
        "required_signals": ["has_tests", "has_ci", "has_deployment_config"],
        "description": (
            "Designs, trains, and ships machine learning models to production at "
            "scale. Requires strong software engineering foundations, MLOps "
            "practices (versioning, monitoring, CI), and experience with "
            "distributed training frameworks such as PyTorch or JAX."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000003"),
        "slug":             "ai-engineer",
        "title":            "AI Engineer",
        "te_threshold":     Decimal("6.0"),
        "pc_threshold":     Decimal("5.5"),
        "cq_threshold":     Decimal("5.5"),
        "required_signals": ["has_readme", "has_tests"],
        "description": (
            "Builds AI-powered products by integrating LLMs, embedding models, "
            "and retrieval systems into production applications. Requires API "
            "design skills, prompt engineering discipline, evaluation frameworks, "
            "and the ability to document AI behaviour and limitations clearly."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000004"),
        "slug":             "data-analyst",
        "title":            "Data Analyst",
        "te_threshold":     Decimal("4.0"),
        "pc_threshold":     Decimal("4.5"),
        "cq_threshold":     Decimal("6.0"),
        "required_signals": ["has_readme"],
        "description": (
            "Extracts insight from structured data using SQL, Python or R, and "
            "BI tooling. Communication quality is the primary differentiator: "
            "dashboards, reports, and data stories must be clear, accurate, and "
            "targeted at business stakeholders."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000005"),
        "slug":             "backend-engineer",
        "title":            "Backend Engineer",
        "te_threshold":     Decimal("6.5"),
        "pc_threshold":     Decimal("5.5"),
        "cq_threshold":     Decimal("4.5"),
        "required_signals": ["has_tests", "has_ci"],
        "description": (
            "Designs and operates server-side systems: REST/gRPC APIs, relational "
            "databases, message queues, and caching layers. Requires test-driven "
            "development, CI pipelines, and the ability to reason about "
            "performance, reliability, and security under production load."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000006"),
        "slug":             "full-stack-developer",
        "title":            "Full Stack Developer",
        "te_threshold":     Decimal("5.5"),
        "pc_threshold":     Decimal("5.0"),
        "cq_threshold":     Decimal("5.0"),
        "required_signals": ["has_readme", "has_deployment_config"],
        "description": (
            "Delivers end-to-end web features across frontend (React/Vue/Svelte) "
            "and backend (Node/Python/Go). Breadth is the expectation: ability to "
            "ship a complete user-facing feature from database schema to deployed "
            "UI without handing off at layer boundaries."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000007"),
        "slug":             "devops-engineer",
        "title":            "DevOps Engineer",
        "te_threshold":     Decimal("6.5"),
        "pc_threshold":     Decimal("5.5"),
        "cq_threshold":     Decimal("5.5"),
        "required_signals": ["has_ci", "has_deployment_config"],
        "description": (
            "Builds and operates the infrastructure that lets engineering teams "
            "ship safely and quickly. Core competencies: container orchestration "
            "(Docker/Kubernetes), CI/CD pipelines, infrastructure-as-code "
            "(Terraform/Pulumi), and incident runbook authoring."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000008"),
        "slug":             "product-manager",
        "title":            "Product Manager",
        "te_threshold":     Decimal("3.0"),
        "pc_threshold":     Decimal("4.5"),
        "cq_threshold":     Decimal("7.0"),
        "required_signals": ["has_readme"],
        "description": (
            "Defines what gets built and why. Technical literacy enables credible "
            "conversations with engineers, but Communication Quality is the primary "
            "signal: PRDs, user-research docs, roadmaps, and stakeholder updates "
            "must be precise, structured, and persuasive."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-000000000009"),
        "slug":             "research-engineer",
        "title":            "Research Engineer",
        "te_threshold":     Decimal("7.0"),
        "pc_threshold":     Decimal("7.5"),
        "cq_threshold":     Decimal("6.0"),
        "required_signals": ["has_tests", "has_readme"],
        "description": (
            "Implements novel algorithms and systems at the boundary between "
            "research and engineering. Requires advanced programming skills "
            "(low-level systems or high-performance computing), the ability to "
            "tackle genuinely open problems, and paper-quality written communication "
            "of methods and results."
        ),
    },
    {
        "id":               uuid.UUID("10000000-0000-4000-8000-00000000000a"),
        "slug":             "software-engineer",
        "title":            "Software Engineer",
        "te_threshold":     Decimal("5.0"),
        "pc_threshold":     Decimal("4.5"),
        "cq_threshold":     Decimal("4.5"),
        "required_signals": ["has_tests"],
        "description": (
            "The generalist entry point for professional software development. "
            "Requires solid programming fundamentals, data structure and algorithm "
            "knowledge, readable code with tests, and the ability to collaborate "
            "effectively through pull requests and code review."
        ),
    },
]


# ── Async seeder ──────────────────────────────────────────────────────────────

async def seed_roles_if_empty(db: AsyncSession) -> int:
    """
    Upsert all ROLE_TEMPLATES rows if the table is empty.

    Uses INSERT … ON CONFLICT (slug) DO UPDATE so:
    - First run: inserts all 10 rows
    - Subsequent runs: refreshes thresholds/descriptions without touching
      existing gap_analyses or recommendations rows that reference these roles

    Returns the number of rows affected (0 if table was already populated
    with all 10 slugs).
    """
    existing_count_result = await db.execute(
        select(func.count()).select_from(RoleTemplate)
    )
    existing_count: int = existing_count_result.scalar_one()

    if existing_count >= len(ROLE_TEMPLATES):
        log.debug("seed.roles_already_present", count=existing_count)
        return 0

    inserted = 0
    for row in ROLE_TEMPLATES:
        existing = await db.execute(
            select(RoleTemplate).where(RoleTemplate.slug == row["slug"])
        )
        if existing.scalar_one_or_none() is not None:
            continue

        db.add(RoleTemplate(
            id=row["id"],
            slug=row["slug"],
            title=row["title"],
            te_threshold=row["te_threshold"],
            pc_threshold=row["pc_threshold"],
            cq_threshold=row["cq_threshold"],
            required_signals=row["required_signals"],
            description=row["description"],
        ))
        inserted += 1

    if inserted:
        await db.flush()
        log.info("seed.roles_inserted", count=inserted)

    return inserted

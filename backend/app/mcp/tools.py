"""
SIGNAL MCP tools.

Each tool is a thin wrapper that opens its own DB session, queries the same
ORM models the REST routers use, and returns plain-text / JSON-serialisable
data.  No business logic is duplicated — heavy lifting stays in the pipeline.

Tools exposed
─────────────
  get_profile          — capability scores + narratives for any GitHub user
  get_gap_analysis     — gap vs role templates + ranked recommendations
  get_analysis_status  — live status of one analysis job by UUID
  list_analysis_jobs   — full job history for a GitHub user
  start_analysis       — trigger a new analysis (requires stored GitHub token)
  compare_profiles     — side-by-side score comparison of two users
  get_role_templates   — all seeded role definitions with thresholds
  get_repositories     — repos collected from the last analysis
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.mcp.dependencies import mcp_db_session
from app.models.analysis_job import AnalysisJob
from app.models.capability_profile import CapabilityProfile
from app.models.repository import Repository
from app.models.role_template import GapAnalysis, RoleTemplate
from app.models.user import User
from app.pipeline.orchestrator import run_analysis

log = structlog.get_logger()


# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt_decimal(value: Decimal | None) -> str | None:
    return f"{float(value):.1f}" if value is not None else None


def _user_not_found(username: str) -> str:
    return json.dumps({"error": f"No user found with GitHub username '{username}'."})


def _profile_not_found(username: str) -> str:
    return json.dumps({
        "error": f"No capability profile found for '{username}'. "
                 "They need to run an analysis first."
    })


async def _get_user(db, github_username: str) -> User | None:
    result = await db.execute(
        select(User).where(User.github_username == github_username)
    )
    return result.scalar_one_or_none()


async def _get_current_profile(db, user_id: uuid.UUID) -> CapabilityProfile | None:
    result = await db.execute(
        select(CapabilityProfile)
        .where(
            CapabilityProfile.user_id == user_id,
            CapabilityProfile.is_current == True,  # noqa: E712
        )
        .options(selectinload(CapabilityProfile.evidence_citations))
        .order_by(CapabilityProfile.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── tools ─────────────────────────────────────────────────────────────────────

async def get_profile(github_username: str) -> str:
    """
    Return the current SIGNAL capability profile for a GitHub user.

    Includes the three dimension scores (Technical Execution, Problem Complexity,
    Communication Quality) on the 1.0–9.0 scale, AI-generated narratives, and
    the list of verified capabilities extracted from their repositories.

    Args:
        github_username: The GitHub username (e.g. "torvalds").
    """
    async with mcp_db_session() as db:
        user = await _get_user(db, github_username)
        if user is None:
            return _user_not_found(github_username)

        profile = await _get_current_profile(db, user.id)
        if profile is None:
            return _profile_not_found(github_username)

        raw = profile.raw_ai_response or {}

        result: dict[str, Any] = {
            "github_username": github_username,
            "full_name": user.full_name,
            "profile_id": str(profile.id),
            "generated_at": profile.created_at.isoformat(),
            "scores": {
                "technical_execution": _fmt_decimal(profile.technical_execution),
                "problem_complexity": _fmt_decimal(profile.problem_complexity),
                "communication_quality": _fmt_decimal(profile.communication_quality),
            },
            "confidence": {
                "technical_execution": _fmt_decimal(profile.te_confidence),
                "problem_complexity": _fmt_decimal(profile.pc_confidence),
                "communication_quality": _fmt_decimal(profile.cq_confidence),
            },
            "narratives": {
                "technical_execution": (raw.get("technical_execution") or {}).get("narrative"),
                "problem_complexity": (raw.get("problem_complexity") or {}).get("narrative"),
                "communication_quality": (raw.get("communication_quality") or {}).get("narrative"),
            },
            "verified_capabilities": profile.verified_capabilities,
            "objective_signals": profile.objective_signals,
            "evidence_citation_count": len(profile.evidence_citations),
        }
        return json.dumps(result, indent=2, default=str)


async def get_gap_analysis(github_username: str, role_slug: str = "") -> str:
    """
    Return the gap analysis for a GitHub user against SIGNAL role templates.

    Shows how far the user is from each role's score thresholds and includes
    the top-priority recommendations for closing those gaps.

    Args:
        github_username: The GitHub username.
        role_slug: Optional role slug to filter to a single role (e.g. "ml-engineer").
                   Leave empty to return gaps for all roles.
    """
    async with mcp_db_session() as db:
        user = await _get_user(db, github_username)
        if user is None:
            return _user_not_found(github_username)

        cp_result = await db.execute(
            select(CapabilityProfile.id)
            .where(
                CapabilityProfile.user_id == user.id,
                CapabilityProfile.is_current == True,  # noqa: E712
            )
            .limit(1)
        )
        profile_id = cp_result.scalar_one_or_none()
        if profile_id is None:
            return _profile_not_found(github_username)

        query = (
            select(GapAnalysis)
            .where(GapAnalysis.profile_id == profile_id)
            .options(
                selectinload(GapAnalysis.role),
                selectinload(GapAnalysis.recommendations),
            )
            .order_by(GapAnalysis.overall_ready.desc())
        )
        gap_result = await db.execute(query)
        gaps = list(gap_result.scalars().all())

        if role_slug:
            gaps = [g for g in gaps if g.role.slug == role_slug]
            if not gaps:
                return json.dumps({
                    "error": f"No gap analysis found for role '{role_slug}'."
                })

        output = []
        for gap in gaps:
            recs = sorted(gap.recommendations, key=lambda r: r.priority)
            output.append({
                "role_slug": gap.role.slug,
                "role_title": gap.role.title,
                "overall_ready": gap.overall_ready,
                "gaps": {
                    "technical_execution": _fmt_decimal(gap.te_gap),
                    "problem_complexity": _fmt_decimal(gap.pc_gap),
                    "communication_quality": _fmt_decimal(gap.cq_gap),
                },
                "recommendations": [
                    {
                        "priority": r.priority,
                        "dimension": r.dimension,
                        "title": r.title,
                        "description": r.description,
                        "evidence_type": r.evidence_type,
                    }
                    for r in recs
                ],
            })

        return json.dumps({
            "github_username": github_username,
            "gap_analyses": output,
            "roles_ready": sum(1 for g in gaps if g.overall_ready),
            "total_roles": len(output),
        }, indent=2, default=str)


async def get_analysis_status(job_id: str) -> str:
    """
    Return the current status of an analysis job.

    Args:
        job_id: The UUID of the analysis job (returned by start_analysis or
                list_analysis_jobs).
    """
    try:
        parsed_id = uuid.UUID(job_id)
    except ValueError:
        return json.dumps({"error": f"'{job_id}' is not a valid UUID."})

    async with mcp_db_session() as db:
        job = await db.get(AnalysisJob, parsed_id)
        if job is None:
            return json.dumps({"error": f"Analysis job '{job_id}' not found."})

        return json.dumps({
            "job_id": str(job.id),
            "status": job.status,
            "current_step": job.current_step,
            "progress_pct": job.progress_pct,
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }, indent=2)


async def list_analysis_jobs(github_username: str) -> str:
    """
    List all analysis jobs for a GitHub user, newest first.

    Args:
        github_username: The GitHub username.
    """
    async with mcp_db_session() as db:
        user = await _get_user(db, github_username)
        if user is None:
            return _user_not_found(github_username)

        result = await db.execute(
            select(AnalysisJob)
            .where(AnalysisJob.user_id == user.id)
            .order_by(AnalysisJob.started_at.desc())
            .limit(20)
        )
        jobs = list(result.scalars().all())

        return json.dumps({
            "github_username": github_username,
            "total": len(jobs),
            "jobs": [
                {
                    "job_id": str(j.id),
                    "status": j.status,
                    "current_step": j.current_step,
                    "progress_pct": j.progress_pct,
                    "error_message": j.error_message,
                    "started_at": j.started_at.isoformat() if j.started_at else None,
                    "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                }
                for j in jobs
            ],
        }, indent=2)


async def start_analysis(github_username: str) -> str:
    """
    Trigger a new SIGNAL capability analysis for a GitHub user.

    The user must have previously signed in through the SIGNAL app so that their
    GitHub OAuth token is stored.  The analysis runs asynchronously — use
    get_analysis_status(job_id) to poll progress.

    Args:
        github_username: The GitHub username whose repositories will be analysed.
    """
    async with AsyncSessionLocal() as db:
        async with db.begin():
            user_result = await db.execute(
                select(User).where(User.github_username == github_username)
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                return _user_not_found(github_username)

            if not user.github_access_token:
                return json.dumps({
                    "error": (
                        f"No GitHub token stored for '{github_username}'. "
                        "The user must sign in through the SIGNAL app first."
                    )
                })

            # Check for an already-running job
            active_result = await db.execute(
                select(AnalysisJob.id)
                .where(
                    AnalysisJob.user_id == user.id,
                    AnalysisJob.status.in_(
                        ("queued", "github_fetch", "evidence_extract", "ai_analysis", "scoring")
                    ),
                )
                .limit(1)
            )
            active_id = active_result.scalar_one_or_none()
            if active_id is not None:
                return json.dumps({
                    "error": "An analysis is already running for this user.",
                    "active_job_id": str(active_id),
                })

            # Create the job row and commit so the background task can see it
            job = AnalysisJob(
                user_id=user.id,
                status="queued",
                current_step="Queued — waiting to start",
                progress_pct=0,
            )
            db.add(job)
            await db.flush()
            job_id = job.id
            # db.begin().__aexit__ commits here

    # Schedule the pipeline in the running asyncio event loop
    asyncio.create_task(
        run_analysis(job_id, AsyncSessionLocal),
        name=f"analysis-{job_id}",
    )
    log.info("mcp.analysis_started", job_id=str(job_id), username=github_username)

    return json.dumps({
        "job_id": str(job_id),
        "status": "queued",
        "message": (
            f"Analysis started for '{github_username}'. "
            f"Poll get_analysis_status('{job_id}') for progress."
        ),
    }, indent=2)


async def compare_profiles(username_a: str, username_b: str) -> str:
    """
    Compare the SIGNAL capability profiles of two GitHub users side by side.

    Returns a structured comparison of their three dimension scores and
    highlights which user leads in each dimension.

    Args:
        username_a: First GitHub username.
        username_b: Second GitHub username.
    """
    async with mcp_db_session() as db:
        profiles: dict[str, dict] = {}

        for username in (username_a, username_b):
            user = await _get_user(db, username)
            if user is None:
                return _user_not_found(username)
            profile = await _get_current_profile(db, user.id)
            if profile is None:
                return _profile_not_found(username)
            profiles[username] = {
                "full_name": user.full_name,
                "technical_execution": profile.technical_execution,
                "problem_complexity": profile.problem_complexity,
                "communication_quality": profile.communication_quality,
                "verified_capability_count": len(profile.verified_capabilities),
                "generated_at": profile.created_at.isoformat(),
            }

    dimensions = ("technical_execution", "problem_complexity", "communication_quality")
    comparison = {}
    for dim in dimensions:
        a_val = profiles[username_a][dim]
        b_val = profiles[username_b][dim]
        if a_val is not None and b_val is not None:
            if a_val > b_val:
                leader = username_a
            elif b_val > a_val:
                leader = username_b
            else:
                leader = "tie"
        else:
            leader = "insufficient data"
        comparison[dim] = {
            username_a: _fmt_decimal(a_val),
            username_b: _fmt_decimal(b_val),
            "leader": leader,
        }

    return json.dumps({
        "comparison": comparison,
        "verified_capabilities": {
            username_a: profiles[username_a]["verified_capability_count"],
            username_b: profiles[username_b]["verified_capability_count"],
        },
        "profiles_generated": {
            username_a: profiles[username_a]["generated_at"],
            username_b: profiles[username_b]["generated_at"],
        },
    }, indent=2)


async def get_role_templates() -> str:
    """
    Return all SIGNAL role templates with their score thresholds.

    Each role defines the minimum Technical Execution, Problem Complexity, and
    Communication Quality scores a student needs to be considered ready for that role.
    """
    async with mcp_db_session() as db:
        result = await db.execute(
            select(RoleTemplate).order_by(RoleTemplate.title)
        )
        roles = list(result.scalars().all())

        return json.dumps({
            "role_count": len(roles),
            "roles": [
                {
                    "slug": r.slug,
                    "title": r.title,
                    "thresholds": {
                        "technical_execution": _fmt_decimal(r.te_threshold),
                        "problem_complexity": _fmt_decimal(r.pc_threshold),
                        "communication_quality": _fmt_decimal(r.cq_threshold),
                    },
                    "description": r.description,
                }
                for r in roles
            ],
        }, indent=2, default=str)


async def get_repositories(github_username: str) -> str:
    """
    Return the repositories collected during the last analysis for a GitHub user.

    Shows objective signals: language breakdown, test/CI/deployment presence,
    commit count, and stars.

    Args:
        github_username: The GitHub username.
    """
    async with mcp_db_session() as db:
        user = await _get_user(db, github_username)
        if user is None:
            return _user_not_found(github_username)

        result = await db.execute(
            select(Repository)
            .where(Repository.user_id == user.id)
            .order_by(Repository.stars.desc())
        )
        repos = list(result.scalars().all())

        if not repos:
            return json.dumps({
                "error": (
                    f"No repositories found for '{github_username}'. "
                    "They need to run an analysis first."
                )
            })

        return json.dumps({
            "github_username": github_username,
            "repository_count": len(repos),
            "repositories": [
                {
                    "name": r.name,
                    "full_name": r.full_name,
                    "description": r.description,
                    "stars": r.stars,
                    "languages": r.languages,
                    "commit_count": r.commit_count,
                    "has_tests": r.has_tests,
                    "has_ci": r.has_ci,
                    "has_deployment_config": r.has_deployment_config,
                    "readme_word_count": r.readme_word_count,
                    "is_fork": r.is_fork,
                    "last_commit_at": r.last_commit_at.isoformat() if r.last_commit_at else None,
                }
                for r in repos
            ],
        }, indent=2, default=str)

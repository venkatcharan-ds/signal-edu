"""
SIGNAL pipeline orchestrator.

Runs all five analysis stages as a single coroutine.
Stage progress is written to analysis_jobs so the SSE endpoint can stream
real-time status to the frontend.

Stage map:
  Stage 1 — GitHub Engine      (github_fetch,      5–40 %)
  Stage 2 — Evidence Engine    (evidence_extract,  40–55 %)  [stub — Phase 10]
  Stage 3 — Capability Engine  (ai_analysis,       55–80 %)
  Stage 4 — Gap Engine         (scoring,           80–90 %)  [deterministic]
  Stage 5 — Recommendation     (scoring,           90–100 %)

Retry model:
  Retryable exceptions (Gemini 429, network timeouts, asyncio.TimeoutError)
  are retried up to settings.max_job_retries times with exponential backoff.
  Non-retryable exceptions (bad input, auth failures) fail immediately.
  After max retries the job is marked failed.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from google import genai
import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.models.analysis_job import AnalysisJob
from app.models.user import User
from app.pipeline.capability_engine import CapabilityEngine
from app.pipeline.evidence_engine import ArtifactText
from app.pipeline.gap_engine import GapEngine
from app.pipeline.github_engine import GitHubEngine, UserSignals
from app.pipeline.profile_builder import build_profile
from app.pipeline.recommendation_engine import RecommendationEngine
from app.pipeline.storage import upsert_repositories

log = structlog.get_logger()


# ── Retry helpers ──────────────────────────────────────────────────────────────

def _is_retryable(exc: Exception) -> bool:
    """True for transient errors that warrant a retry (Gemini 429, timeouts, network)."""
    if isinstance(exc, asyncio.TimeoutError):
        return True
    msg = str(exc).lower()
    return any(
        keyword in msg
        for keyword in (
            "429",
            "resource exhausted",
            "quota",
            "rate limit",
            "rateerror",
            "timeout",
            "connection",
            "network",
            "unavailable",
            "503",
            "502",
        )
    )


def _backoff_seconds(retry_count: int) -> int:
    """Exponential backoff: 30s, 60s, 120s for attempts 0, 1, 2."""
    return 30 * (2 ** retry_count)


# ── Public entry point ─────────────────────────────────────────────────────────

async def run_analysis(
    job_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """
    Entry point called by the background worker.
    Opens its own DB session — does NOT share the request session.
    Handles retry logic and stale-job cleanup.
    """
    settings = get_settings()
    bound = log.bind(job_id=str(job_id))
    bound.info("pipeline.start")

    failure_exc: Exception | None = None

    # No outer transaction — _set_status() commits each stage update so the
    # SSE poller (a separate DB session) can see live progress in real time.
    async with session_factory() as db:
        try:
            await asyncio.wait_for(
                _run(job_id, db, bound),
                timeout=settings.analysis_timeout_seconds,
            )
        except Exception as exc:
            bound.exception("pipeline.failed", error=str(exc))
            failure_exc = exc
        # Session closes here; any uncommitted autobegin transaction is rolled back.

    if failure_exc is not None:
        try:
            async with session_factory() as db2:
                job = await db2.get(AnalysisJob, job_id)
                retry_count = job.retry_count if job else settings.max_job_retries

                if _is_retryable(failure_exc) and retry_count < settings.max_job_retries:
                    backoff = _backoff_seconds(retry_count)
                    next_retry = datetime.now(timezone.utc) + timedelta(seconds=backoff)
                    bound.warning(
                        "pipeline.retry_scheduled",
                        attempt=retry_count + 1,
                        max=settings.max_job_retries,
                        backoff_s=backoff,
                    )
                    await db2.execute(
                        update(AnalysisJob)
                        .where(AnalysisJob.id == job_id)
                        .values(
                            status="queued",
                            current_step=f"Retrying (attempt {retry_count + 1} of {settings.max_job_retries})…",
                            progress_pct=0,
                            claimed_at=None,
                            worker_id=None,
                            retry_count=retry_count + 1,
                            next_retry_at=next_retry,
                        )
                    )
                    await db2.commit()
                else:
                    bound.error("pipeline.final_failure", retries=retry_count)
                    await db2.execute(
                        update(AnalysisJob)
                        .where(AnalysisJob.id == job_id)
                        .values(
                            status="failed",
                            current_step=str(failure_exc)[:100],
                            progress_pct=0,
                            error_message=str(failure_exc),
                            claimed_at=None,
                            worker_id=None,
                            completed_at=datetime.now(timezone.utc),
                        )
                    )
                    await db2.commit()
        except Exception as db_exc:
            bound.exception("pipeline.status_update_failed", error=str(db_exc))


# ── Internal pipeline ──────────────────────────────────────────────────────────

async def _run(
    job_id: uuid.UUID,
    db: AsyncSession,
    bound: structlog.BoundLogger,
) -> None:
    settings = get_settings()

    # ── Load job + user ────────────────────────────────────────────────────
    job = await db.get(AnalysisJob, job_id)
    if job is None:
        raise ValueError(f"AnalysisJob {job_id} not found")

    user = await db.get(User, job.user_id)
    if user is None:
        raise ValueError(f"User {job.user_id} not found")

    if not user.github_access_token:
        raise ValueError("No GitHub token stored — user must sign in again")

    gemini_client = genai.Client(api_key=settings.gemini_api_key)

    # ── Stage 1: GitHub Engine ─────────────────────────────────────────────
    await _set_status(db, job_id, "github_fetch", "Fetching GitHub repositories", 5)

    github_engine = GitHubEngine(
        github_token=user.github_access_token,
        max_concurrency=5,
    )
    signals: UserSignals = await github_engine.extract(
        username=user.github_username,
        max_repos=settings.max_repos_to_analyze,
    )

    await _set_status(db, job_id, "github_fetch", "Storing repository signals", 30)
    await upsert_repositories(db, user.id, signals)
    await _set_status(db, job_id, "github_fetch", "GitHub data collected", 40)

    bound.info("stage1_complete", repos=len(signals.repos))

    # ── Stage 2: Evidence Engine (stub — Phase 10) ─────────────────────────
    await _set_status(db, job_id, "evidence_extract", "Processing additional evidence", 45)
    artifacts: list[ArtifactText] = []
    await _set_status(db, job_id, "evidence_extract", "Evidence ready", 55)

    # ── Stage 3: Capability Engine ─────────────────────────────────────────
    await _set_status(db, job_id, "ai_analysis", "Running AI capability analysis", 60)

    capability_engine = CapabilityEngine(
        client=gemini_client,
        model=settings.gemini_model_capability,
    )
    scores, verified_capabilities = await capability_engine.score_all(signals, artifacts)

    await _set_status(db, job_id, "ai_analysis", "Capability scores computed", 80)
    bound.info(
        "stage3_complete",
        **{s.dimension: str(s.score) for s in scores},
        cap_applied=any(s.cap_applied for s in scores),
    )

    score_map     = {s.dimension: s for s in scores}
    te, pc, cq    = score_map["technical_execution"], score_map["problem_complexity"], score_map["communication_quality"]

    objective_signals = {
        "te_objective": round(te.objective_component, 3),
        "pc_objective": round(pc.objective_component, 3),
        "cq_objective": round(cq.objective_component, 3),
        "te_ai":        round(te.ai_component, 3),
        "pc_ai":        round(pc.ai_component, 3),
        "cq_ai":        round(cq.ai_component, 3),
        "repo_count":   len(signals.repos),
        "active_repos": signals.active_repo_count,
        "total_stars":  signals.total_stars,
        "has_tests":    signals.any_has_tests,
        "has_ci":       signals.any_has_ci,
        "has_deploy":   signals.any_has_deployment_config,
        "languages":    list(signals.total_languages.keys())[:10],
    }

    raw_ai_response = {
        "technical_execution":   {"narrative": te.narrative, "ai_score": te.ai_component_raw},
        "problem_complexity":    {"narrative": pc.narrative, "ai_score": pc.ai_component_raw},
        "communication_quality": {"narrative": cq.narrative, "ai_score": cq.ai_component_raw},
        "verified_capabilities": verified_capabilities,
    }

    # ── Stage 4 + 5: Gap Engine + Recommendations ─────────────────────────
    await _set_status(db, job_id, "scoring", "Computing role gaps", 85)

    student_languages = [
        lang for lang, _ in sorted(
            signals.total_languages.items(), key=lambda x: x[1], reverse=True
        )[:6]
    ]
    student_themes = list({
        topic
        for repo in signals.repos
        for topic in repo.topics[:3]
    })[:10]

    rec_engine = RecommendationEngine(
        client=gemini_client,
        model=settings.gemini_model_recommendation,
    )
    gap_engine = GapEngine()

    from sqlalchemy import select as sa_select
    from app.models.role_template import RoleTemplate

    role_result = await db.execute(sa_select(RoleTemplate))
    all_roles = list(role_result.scalars().all())

    recommendations_by_role: dict = {}

    if all_roles:
        def _deficit(role: RoleTemplate) -> float:
            g = gap_engine.compute(
                te_score=te.score, pc_score=pc.score, cq_score=cq.score,
                role_te=role.te_threshold, role_pc=role.pc_threshold, role_cq=role.cq_threshold,
                role_slug=role.slug, role_title=role.title,
            )
            return (
                min(float(g.te_gap), 0) +
                min(float(g.pc_gap), 0) +
                min(float(g.cq_gap), 0)
            )

        target_role = max(all_roles, key=_deficit)
        target_gap = gap_engine.compute(
            te_score=te.score, pc_score=pc.score, cq_score=cq.score,
            role_te=target_role.te_threshold, role_pc=target_role.pc_threshold,
            role_cq=target_role.cq_threshold,
            role_slug=target_role.slug, role_title=target_role.title,
        )

        await _set_status(db, job_id, "scoring", "Generating recommendations", 90)

        recs = await rec_engine.generate(
            gap_result=target_gap,
            student_languages=student_languages,
            student_themes=student_themes,
            te_narrative=te.narrative,
            pc_narrative=pc.narrative,
            cq_narrative=cq.narrative,
        )
        recommendations_by_role[target_role.slug] = recs

        bound.info("stage5_complete", target_role=target_role.slug, recs=len(recs))

    # ── Build + persist full profile ──────────────────────────────────────
    await _set_status(db, job_id, "scoring", "Saving capability profile", 95)

    await build_profile(
        db=db,
        user_id=user.id,
        job_id=job_id,
        scores=scores,
        verified_capabilities=verified_capabilities,
        objective_signals=objective_signals,
        raw_ai_response=raw_ai_response,
        recommendations_by_role=recommendations_by_role,
    )

    # ── Mark complete ─────────────────────────────────────────────────────
    await _set_status(
        db, job_id,
        status="complete",
        step="Profile ready",
        pct=100,
        completed_at=datetime.now(timezone.utc),
    )
    # Clear worker claim fields — committed separately so the write is durable
    # even though _set_status already committed the 'complete' status above.
    await db.execute(
        update(AnalysisJob)
        .where(AnalysisJob.id == job_id)
        .values(claimed_at=None, worker_id=None)
    )
    await db.commit()
    bound.info("pipeline.complete")


async def _set_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str = "queued",
    step: str = "",
    pct: int = 0,
    error: str | None = None,
    completed_at: datetime | None = None,
) -> None:
    values: dict = {
        "status":       status,
        "current_step": step,
        "progress_pct": pct,
    }
    if error:
        values["error_message"] = error
    if completed_at:
        values["completed_at"] = completed_at

    await db.execute(
        update(AnalysisJob)
        .where(AnalysisJob.id == job_id)
        .values(**values)
    )
    await db.commit()

"""
Profile Builder — persists Stage 3–5 pipeline outputs to PostgreSQL.

Writes:
  - capability_profiles  (one row, flips previous is_current → False)
  - evidence_citations   (one row per citation per dimension)
  - gap_analyses         (one row per role template)
  - recommendations      (up to 3 rows per gap_analysis)

All writes happen inside the caller's transaction — the orchestrator owns
the session and calls db.flush() after this function returns.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capability_profile import CapabilityProfile, EvidenceCitation
from app.models.role_template import GapAnalysis, Recommendation, RoleTemplate
from app.pipeline.capability_engine import CapabilityScore
from app.pipeline.gap_engine import GapEngine, GapResult
from app.pipeline.recommendation_engine import RecommendationData

log = structlog.get_logger()


async def build_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    scores: list[CapabilityScore],
    verified_capabilities: list[str],
    objective_signals: dict,
    raw_ai_response: dict,
    recommendations_by_role: dict[str, list[RecommendationData]],
) -> CapabilityProfile:
    """
    Persist a complete capability profile and all related records.

    Parameters
    ----------
    scores                  Three CapabilityScore objects (TE, PC, CQ).
    verified_capabilities   Claude's list of specific capability strings.
    objective_signals       Serialisable dict of raw objective sub-scores.
    raw_ai_response         The full Claude tool-use input dict for auditability.
    recommendations_by_role Keyed by role_slug → list[RecommendationData] (max 3 each).
    """
    # Index scores by dimension for quick lookup
    score_map = {s.dimension: s for s in scores}
    te = score_map["technical_execution"]
    pc = score_map["problem_complexity"]
    cq = score_map["communication_quality"]

    # ── 1. Deactivate previous current profile ────────────────────────────────
    await db.execute(
        update(CapabilityProfile)
        .where(CapabilityProfile.user_id == user_id, CapabilityProfile.is_current == True)  # noqa: E712
        .values(is_current=False)
    )

    # ── 2. Create new CapabilityProfile ──────────────────────────────────────
    profile = CapabilityProfile(
        user_id=user_id,
        job_id=job_id,
        is_current=True,
        technical_execution=te.score,
        problem_complexity=pc.score,
        communication_quality=cq.score,
        te_confidence=te.confidence,
        pc_confidence=pc.confidence,
        cq_confidence=cq.confidence,
        verified_capabilities=verified_capabilities,
        objective_signals=objective_signals,
        raw_ai_response={
            **raw_ai_response,
            "_meta": {
                "te_cap_applied": te.cap_applied,
                "pc_cap_applied": pc.cap_applied,
                "cq_cap_applied": cq.cap_applied,
                "te_ai_raw":      te.ai_component_raw,
                "pc_ai_raw":      pc.ai_component_raw,
                "cq_ai_raw":      cq.ai_component_raw,
                "generated_at":   datetime.now(timezone.utc).isoformat(),
            },
        },
    )
    db.add(profile)
    await db.flush()  # get profile.id before FK inserts

    log.info(
        "profile_builder.profile_created",
        profile_id=str(profile.id),
        te=str(te.score),
        pc=str(pc.score),
        cq=str(cq.score),
    )

    # ── 3. Evidence citations ─────────────────────────────────────────────────
    for score in scores:
        for cite in score.citations:
            db.add(EvidenceCitation(
                profile_id=profile.id,
                dimension=score.dimension,
                citation_text=cite.citation_text,
                artifact_type=cite.artifact_type,
                artifact_ref=cite.artifact_ref,
                score_contribution=Decimal(str(round(cite.score_contribution, 1))),
            ))

    # ── 4. Gap analyses against each role template ────────────────────────────
    role_rows_result = await db.execute(select(RoleTemplate))
    role_rows: list[RoleTemplate] = list(role_rows_result.scalars().all())

    gap_engine = GapEngine()

    for role in role_rows:
        gap_result: GapResult = gap_engine.compute(
            te_score=te.score,
            pc_score=pc.score,
            cq_score=cq.score,
            role_te=role.te_threshold,
            role_pc=role.pc_threshold,
            role_cq=role.cq_threshold,
            role_slug=role.slug,
            role_title=role.title,
        )

        gap_row = GapAnalysis(
            profile_id=profile.id,
            role_id=role.id,
            te_gap=gap_result.te_gap,
            pc_gap=gap_result.pc_gap,
            cq_gap=gap_result.cq_gap,
            overall_ready=gap_result.overall_ready,
        )
        db.add(gap_row)
        await db.flush()  # need gap_row.id for recommendations FK

        # 5. Recommendations for this role (if provided)
        recs = recommendations_by_role.get(role.slug, [])
        for rec in recs[:3]:  # enforce max 3
            db.add(Recommendation(
                gap_analysis_id=gap_row.id,
                dimension=rec.dimension,
                priority=rec.priority,
                title=rec.title,
                description=rec.description,
                evidence_type=rec.evidence_type,
            ))

    log.info(
        "profile_builder.complete",
        profile_id=str(profile.id),
        roles_evaluated=len(role_rows),
    )
    return profile

"""
Profiles router.

/me           — authenticated; current user's CapabilityProfile with citations + narratives
/me/gaps      — authenticated; gap analyses against all role templates
/{username}   — public; no auth required
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.capability_profile import CapabilityProfile
from app.models.role_template import GapAnalysis, RoleTemplate, Recommendation
from app.models.user import User
from app.schemas.profile import (
    CapabilityProfileResponse,
    GapAnalysisSchema,
    ProjectRepoAnalysisSchema,
    PublicProfileResponse,
    RecommendationSchema,
    UpdateProfileRequest,
    ResumeSkillsRequest,
)

log = structlog.get_logger()
router = APIRouter()


@router.get("/me", response_model=CapabilityProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CapabilityProfileResponse:
    """Current user's latest capability profile with evidence citations and narratives."""
    result = await db.execute(
        select(CapabilityProfile)
        .where(
            CapabilityProfile.user_id == user.id,
            CapabilityProfile.is_current == True,  # noqa: E712
        )
        .options(selectinload(CapabilityProfile.evidence_citations))
        .order_by(CapabilityProfile.created_at.desc())
        .limit(1)
    )
    profile: CapabilityProfile | None = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="No capability profile found. Run an analysis first.",
        )
    return CapabilityProfileResponse.from_orm_with_narratives(profile)


@router.get("/me/gaps", response_model=list[GapAnalysisSchema])
async def get_my_gaps(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[GapAnalysisSchema]:
    """
    Gap analysis for the current profile against all role templates.
    Includes recommendations for the roles that generated them.
    """
    # Get current profile ID
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
        raise HTTPException(status_code=404, detail="No capability profile found.")

    gap_result = await db.execute(
        select(GapAnalysis)
        .where(GapAnalysis.profile_id == profile_id)
        .options(
            selectinload(GapAnalysis.role),
            selectinload(GapAnalysis.recommendations),
        )
        .order_by(GapAnalysis.overall_ready.desc())
    )
    gaps = list(gap_result.scalars().all())

    output: list[GapAnalysisSchema] = []
    for gap in gaps:
        recs = [
            RecommendationSchema(
                id=r.id,
                dimension=r.dimension,
                priority=r.priority,
                title=r.title,
                description=r.description,
                evidence_type=r.evidence_type,
            )
            for r in sorted(gap.recommendations, key=lambda r: r.priority)
        ]
        output.append(GapAnalysisSchema(
            id=gap.id,
            role_slug=gap.role.slug,
            role_title=gap.role.title,
            te_gap=gap.te_gap,
            pc_gap=gap.pc_gap,
            cq_gap=gap.cq_gap,
            overall_ready=gap.overall_ready,
            recommendations=recs,
        ))
    return output


@router.get("/me/projects", response_model=list[ProjectRepoAnalysisSchema])
async def get_my_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProjectRepoAnalysisSchema]:
    """
    Project Intelligence — per-repository structured analysis from the latest profile.
    Returns an empty list if the current profile pre-dates this feature.
    """
    result = await db.execute(
        select(CapabilityProfile)
        .where(
            CapabilityProfile.user_id == user.id,
            CapabilityProfile.is_current == True,  # noqa: E712
        )
        .order_by(CapabilityProfile.created_at.desc())
        .limit(1)
    )
    profile: CapabilityProfile | None = result.scalar_one_or_none()
    if profile is None or not profile.raw_ai_response:
        return []

    raw_projects = profile.raw_ai_response.get("project_intelligence", [])
    if not isinstance(raw_projects, list):
        return []

    validated: list[ProjectRepoAnalysisSchema] = []
    for item in raw_projects:
        try:
            validated.append(ProjectRepoAnalysisSchema.model_validate(item))
        except Exception:
            log.warning("projects.validation_failed", item=str(item)[:120])

    return validated


@router.patch("/me", response_model=dict)
async def update_profile(
    payload: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Update institution or display name."""
    if payload.institution is not None:
        user.institution = payload.institution
    if payload.full_name is not None:
        user.full_name = payload.full_name
    await db.flush()
    log.info("profile.updated", user=user.github_username)
    return {
        "id":               str(user.id),
        "full_name":        user.full_name,
        "institution":      user.institution,
        "github_username":  user.github_username,
    }


@router.post("/me/resume-skills")
async def submit_resume_skills(
    payload: ResumeSkillsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Store self-reported resume skills used by the gap-reveal feature."""
    user.resume_skills = payload.skills
    await db.flush()
    return {"stored": len(payload.skills)}


@router.get("/{username}", response_model=PublicProfileResponse)
async def get_public_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> PublicProfileResponse:
    """
    Public profile — no auth required.
    Returns capability scores, evidence citations, and verified capabilities.
    """
    result = await db.execute(
        select(User).where(User.github_username == username)
    )
    profile_user: User | None = result.scalar_one_or_none()
    if profile_user is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    cp_result = await db.execute(
        select(CapabilityProfile)
        .where(
            CapabilityProfile.user_id == profile_user.id,
            CapabilityProfile.is_current == True,  # noqa: E712
        )
        .options(selectinload(CapabilityProfile.evidence_citations))
        .order_by(CapabilityProfile.created_at.desc())
        .limit(1)
    )
    capability_profile = cp_result.scalar_one_or_none()

    profile_response = (
        CapabilityProfileResponse.from_orm_with_narratives(capability_profile)
        if capability_profile
        else None
    )

    return PublicProfileResponse(
        github_username=profile_user.github_username,
        full_name=profile_user.full_name,
        github_avatar=profile_user.github_avatar,
        institution=profile_user.institution,
        resume_skills=profile_user.resume_skills or [],
        verified_capability_count=(
            len(capability_profile.verified_capabilities) if capability_profile else 0
        ),
        resume_skill_count=len(profile_user.resume_skills or []),
        profile=profile_response,
    )

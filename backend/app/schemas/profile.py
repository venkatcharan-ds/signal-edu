from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, UUID4


class EvidenceCitationSchema(BaseModel):
    id: UUID4
    dimension: str
    citation_text: str
    artifact_type: Optional[str] = None
    artifact_ref: Optional[str] = None
    score_contribution: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class RecommendationSchema(BaseModel):
    id: UUID4
    dimension: str
    priority: int
    title: str
    description: str
    evidence_type: Optional[str] = None

    model_config = {"from_attributes": True}


class GapAnalysisSchema(BaseModel):
    id: UUID4
    role_slug: str         # denormalised from role join in router
    role_title: str
    te_gap: Optional[Decimal] = None
    pc_gap: Optional[Decimal] = None
    cq_gap: Optional[Decimal] = None
    overall_ready: bool
    recommendations: list[RecommendationSchema] = []


class DimensionDetail(BaseModel):
    """Per-dimension breakdown returned to the frontend."""
    score: Decimal
    confidence: Optional[Decimal] = None
    percentile: Optional[int] = None
    narrative: Optional[str] = None     # extracted from raw_ai_response
    citations: list[EvidenceCitationSchema] = []


class CapabilityProfileResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    job_id: Optional[UUID4] = None
    is_current: bool

    # Raw scores
    technical_execution:   Optional[Decimal] = None
    problem_complexity:    Optional[Decimal] = None
    communication_quality: Optional[Decimal] = None

    # Confidence
    te_confidence: Optional[Decimal] = None
    pc_confidence: Optional[Decimal] = None
    cq_confidence: Optional[Decimal] = None

    # Cohort percentile (populated post-MVP)
    te_percentile: Optional[int] = None
    pc_percentile: Optional[int] = None
    cq_percentile: Optional[int] = None

    # Structured evidence and capabilities
    verified_capabilities: list[str] = []
    evidence_citations:    list[EvidenceCitationSchema] = []

    # Narratives extracted from raw_ai_response (computed in serialiser)
    te_narrative: Optional[str] = None
    pc_narrative: Optional[str] = None
    cq_narrative: Optional[str] = None

    # Objective signal snapshot
    objective_signals: Optional[dict] = None

    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_narratives(cls, profile) -> "CapabilityProfileResponse":
        """
        Factory that extracts per-dimension narratives from raw_ai_response
        so the frontend gets a flat, easy-to-render structure.
        """
        obj = cls.model_validate(profile)
        if profile.raw_ai_response:
            raw = profile.raw_ai_response
            obj.te_narrative = (raw.get("technical_execution") or {}).get("narrative")
            obj.pc_narrative = (raw.get("problem_complexity") or {}).get("narrative")
            obj.cq_narrative = (raw.get("communication_quality") or {}).get("narrative")
        return obj


class PublicProfileResponse(BaseModel):
    github_username: str
    full_name: Optional[str] = None
    github_avatar: Optional[str] = None
    institution: Optional[str] = None
    resume_skills: list[str] = []
    verified_capability_count: int = 0
    resume_skill_count: int = 0
    profile: Optional[CapabilityProfileResponse] = None


class UpdateProfileRequest(BaseModel):
    institution: Optional[str] = None
    full_name: Optional[str] = None


class ResumeSkillsRequest(BaseModel):
    skills: list[str]


# ── Project Intelligence schemas ──────────────────────────────────────────────

class ProjectTechnologySchema(BaseModel):
    name: str
    status: str  # "demonstrated" | "inferred" | "claimed" | "not_demonstrated"
    evidence: str


class ProjectDimensionScoresSchema(BaseModel):
    code_quality: float
    documentation: float
    architecture: float
    testing: float
    deployment_readiness: float
    complexity: float
    real_world_impact: float


class ProjectRepoAnalysisSchema(BaseModel):
    repo_full_name: str
    summary: str
    classification: str
    level: str  # "Beginner" | "Intermediate" | "Advanced"
    overall_score: float
    dimension_scores: ProjectDimensionScoresSchema
    academic_vs_realworld: str  # "academic" | "real_world" | "mixed"
    primary_technologies: list[ProjectTechnologySchema] = []
    role_relevance: dict[str, str] = {}  # role_slug -> "high" | "medium" | "low" | "none"
    improvement_recommendations: list[str] = []
    # V2 fields — default to empty so pre-V2 profiles degrade gracefully
    how_it_works: str = ""
    capabilities_demonstrated: list[str] = []
    real_world_comparison: str = ""

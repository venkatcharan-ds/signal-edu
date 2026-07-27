from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional
from decimal import Decimal


class RecommendationSchema(BaseModel):
    id: UUID4
    dimension: str
    priority: int
    title: str
    description: str
    evidence_type: Optional[str] = None

    model_config = {"from_attributes": True}


class GapAnalysisResponse(BaseModel):
    id: UUID4
    profile_id: UUID4
    role_slug: str
    role_title: str
    te_gap: Optional[Decimal] = None
    pc_gap: Optional[Decimal] = None
    cq_gap: Optional[Decimal] = None
    overall_ready: bool
    recommendations: list[RecommendationSchema] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleTemplateSchema(BaseModel):
    id: UUID4
    slug: str
    title: str
    te_threshold: Decimal
    pc_threshold: Decimal
    cq_threshold: Decimal
    description: Optional[str] = None

    model_config = {"from_attributes": True}

from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional


class AnalysisJobStart(BaseModel):
    pass


class AnalysisJobResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    status: str
    current_step: Optional[str] = None
    progress_pct: int
    error_message: Optional[str] = None
    is_test: bool = False
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnalysisProgressEvent(BaseModel):
    step: str
    label: str
    progress: int
    queue_position: int = 0   # 0 = not queued; N = position in queue (1-indexed)
    detail: Optional[str] = None
    error: Optional[str] = None


class QuotaResponse(BaseModel):
    used_today: int
    limit: int
    remaining: int
    has_active_job: bool

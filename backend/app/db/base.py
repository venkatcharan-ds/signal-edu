"""
Central import point for Alembic autogenerate.
Import Base and every model here so metadata is complete.
"""
from app.database import Base  # noqa: F401

# Models must be imported so SQLAlchemy registers them on Base.metadata
from app.models.user import User  # noqa: F401
from app.models.repository import Repository  # noqa: F401
from app.models.artifact import Artifact  # noqa: F401
from app.models.analysis_job import AnalysisJob  # noqa: F401
from app.models.capability_profile import CapabilityProfile, EvidenceCitation  # noqa: F401
from app.models.role_template import RoleTemplate, GapAnalysis, Recommendation, ProfileView  # noqa: F401

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "SIGNAL API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str            # Settings > API > JWT Secret

    # ── GitHub OAuth ──────────────────────────────────────────────────────────
    github_client_id: str
    github_client_secret: str
    github_redirect_uri: str = "http://localhost:3000/auth/callback"

    # ── Gemini ────────────────────────────────────────────────────────────────
    gemini_api_key: str
    gemini_model_capability: str = "gemini-3.1-pro-preview"
    gemini_model_recommendation: str = "gemini-2.5-flash-preview-05-20"

    # ── Frontend ──────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    # ── Pipeline ──────────────────────────────────────────────────────────────
    max_repos_to_analyze: int = 20
    analysis_timeout_seconds: int = 240

    # ── Rate limiting ────────────────────────────────────────────────────────
    daily_analysis_limit: int = 3       # Max analyses per user per calendar day (UTC)

    # ── Worker / queue ────────────────────────────────────────────────────────
    max_concurrent_jobs: int = 2        # Max simultaneous pipelines per worker process
    max_job_retries: int = 3            # Max retry attempts before marking a job failed
    job_claim_timeout_seconds: int = 600  # A claimed job older than this is considered stale
    worker_poll_interval_seconds: float = 2.0  # Idle poll interval when no jobs are waiting

    # ── Admin ─────────────────────────────────────────────────────────────────
    admin_api_key: str = ""             # Set in production; left blank = admin disabled

    # ── MCP ───────────────────────────────────────────────────────────────────
    mcp_api_key: str = ""               # Bearer token for /mcp endpoint; empty = open (dev only)


@lru_cache
def get_settings() -> Settings:
    return Settings()

import asyncio
import uuid
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.database import AsyncSessionLocal, engine, Base
from app.db.seed import seed_roles_if_empty
from app.routers import auth, analysis, profiles, artifacts, admin
from app.worker.poller import poll_loop

configure_logging()
log = structlog.get_logger()
settings = get_settings()


async def _embedded_worker(worker_id: str) -> None:
    """
    Run the job-queue poller inside the web process so jobs are picked up
    immediately during a demo session without waiting for GitHub Actions.

    Uses the same atomic FOR UPDATE SKIP LOCKED claim logic as the standalone
    worker — safe to run alongside GitHub Actions and any future Render
    Background Worker with no duplicate-processing risk.
    """
    bound = log.bind(worker_id=worker_id)
    bound.info("embedded_worker.start")
    try:
        await poll_loop(
            session_factory=AsyncSessionLocal,
            worker_id=worker_id,
            max_concurrent_jobs=settings.max_concurrent_jobs,
            poll_interval_seconds=settings.worker_poll_interval_seconds,
            claim_timeout_seconds=settings.job_claim_timeout_seconds,
        )
    except asyncio.CancelledError:
        bound.info("embedded_worker.stopped")
        raise
    except Exception:
        bound.exception("embedded_worker.crashed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("signal.startup", environment=settings.environment, version=settings.app_version)

    # Development convenience: create tables without running migrations.
    # Production relies solely on `alembic upgrade head`.
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Seed role templates on every startup — idempotent, no-op when all
    # 10 rows are already present.  Runs in all environments so a fresh
    # production deployment is immediately usable without a manual step.
    if settings.environment != "test":
        async with AsyncSessionLocal() as db:
            async with db.begin():
                seeded = await seed_roles_if_empty(db)
                if seeded:
                    log.info("signal.roles_seeded", count=seeded)

    # Start embedded worker — runs alongside the web service so jobs are
    # processed immediately without relying on GitHub Actions scheduling.
    worker_id = f"web-{uuid.uuid4().hex[:8]}"
    worker_task = asyncio.create_task(
        _embedded_worker(worker_id),
        name=f"embedded-worker-{worker_id}",
    )

    yield

    # Gracefully stop the embedded worker on shutdown
    worker_task.cancel()
    try:
        await asyncio.wait_for(asyncio.shield(worker_task), timeout=5.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    log.info("signal.shutdown")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── Middleware — order matters: outer → inner on request, inner → outer on response

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_exception", path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "_debug": f"{type(exc).__name__}: {exc}",
        },
    )


app.include_router(auth.router,      prefix="/v1/auth",      tags=["auth"])
app.include_router(analysis.router,  prefix="/v1/analysis",  tags=["analysis"])
app.include_router(profiles.router,  prefix="/v1/profiles",  tags=["profiles"])
app.include_router(artifacts.router, prefix="/v1/artifacts", tags=["artifacts"])
app.include_router(admin.router,     prefix="/v1/admin",     tags=["admin"])


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": settings.app_version, "environment": settings.environment}


# ── OAuth discovery at the server root (RFC 8414 §3 / MCP spec 2025-03-26) ───
# Claude probes /.well-known/oauth-authorization-server at the origin first.
# The actual metadata is served by the mcp library at /mcp/.well-known/…
# so we redirect there.  Claude follows the redirect per RFC 8414 §3.1.
@app.get("/.well-known/oauth-authorization-server", include_in_schema=False)
async def oauth_discovery_redirect() -> RedirectResponse:
    return RedirectResponse("/mcp/.well-known/oauth-authorization-server", status_code=302)


# ── MCP server — mounted last so REST routes always take precedence ────────────
# Import is deferred to here so the MCP package is only loaded when needed and
# all models are already registered with SQLAlchemy before FastMCP initialises.
from app.mcp.server import mcp_asgi_app  # noqa: E402

app.mount("/mcp", mcp_asgi_app)

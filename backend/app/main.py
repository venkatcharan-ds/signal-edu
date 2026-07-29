from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.database import AsyncSessionLocal, engine, Base
from app.db.seed import seed_roles_if_empty
from app.routers import auth, analysis, profiles, artifacts, admin

configure_logging()
log = structlog.get_logger()
settings = get_settings()


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

    yield
    log.info("signal.shutdown")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── MCP authentication middleware ─────────────────────────────────────────────
# Applied before all other middleware so unauthenticated MCP probes are
# rejected immediately.  If MCP_API_KEY is empty the endpoint is open
# (acceptable in local development; always set the key in production).

@app.middleware("http")
async def mcp_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/mcp"):
        mcp_key = get_settings().mcp_api_key
        if mcp_key:
            auth_header = request.headers.get("Authorization", "")
            token = auth_header.removeprefix("Bearer ").strip()
            if token != mcp_key:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "MCP authentication required. Provide a valid Bearer token."},
                )
    return await call_next(request)


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


# ── MCP server — mounted last so REST routes always take precedence ────────────
# Import is deferred to here so the MCP package is only loaded when needed and
# all models are already registered with SQLAlchemy before FastMCP initialises.
from app.mcp.server import mcp_asgi_app  # noqa: E402

app.mount("/mcp", mcp_asgi_app)

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

# Middleware — order matters: outer → inner on request, inner → outer on response
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
    import traceback
    tb = traceback.format_exc()
    log.exception("unhandled_exception", path=str(request.url), traceback=tb)
    # TEMPORARY: expose exception type for debugging — revert before GA
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "_debug": f"{type(exc).__name__}: {exc}"})


app.include_router(auth.router,      prefix="/v1/auth",      tags=["auth"])
app.include_router(analysis.router,  prefix="/v1/analysis",  tags=["analysis"])
app.include_router(profiles.router,  prefix="/v1/profiles",  tags=["profiles"])
app.include_router(artifacts.router, prefix="/v1/artifacts", tags=["artifacts"])
app.include_router(admin.router,     prefix="/v1/admin",     tags=["admin"])


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": settings.app_version, "environment": settings.environment}


@app.get("/debug/db", tags=["system"])
async def debug_db() -> dict:
    """TEMPORARY: test DB access from a request context. Remove before GA."""
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT count(*) FROM public.users"))
            count = result.scalar()
            return {"ok": True, "user_count": count}
    except Exception as exc:
        import traceback
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "tb": traceback.format_exc()}


@app.get("/debug/insert", tags=["system"])
async def debug_insert() -> dict:
    """TEMPORARY: test ORM INSERT for users table. Remove before GA."""
    import uuid as uuid_mod
    from app.models.user import User
    from sqlalchemy import select
    test_id = uuid_mod.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    try:
        async with AsyncSessionLocal() as session:
            # Check if test row exists first
            result = await session.execute(select(User).where(User.id == test_id))
            existing = result.scalar_one_or_none()
            if existing:
                return {"ok": True, "msg": "test row already exists", "username": existing.github_username}

            user = User(
                id=test_id,
                github_id=9999999999,
                github_username="_debug_test_user_",
                github_email="debug@test.invalid",
                github_avatar=None,
                full_name=None,
            )
            session.add(user)
            await session.flush()
            await session.rollback()  # don't persist the test row
            return {"ok": True, "msg": "INSERT succeeded (rolled back)"}
    except Exception as exc:
        import traceback
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "tb": traceback.format_exc()}

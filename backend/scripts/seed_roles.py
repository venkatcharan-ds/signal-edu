"""
Standalone role-template seeder.

Run from the backend/ directory:

    python scripts/seed_roles.py

Or with a custom DATABASE_URL:

    DATABASE_URL=postgresql+asyncpg://... python scripts/seed_roles.py

Requires:
    - .env file present in backend/ (or DATABASE_URL set in environment)
    - Alembic migrations already applied (tables must exist)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make `app` importable when run from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging
from app.database import AsyncSessionLocal
from app.db.seed import ROLE_TEMPLATES, seed_roles_if_empty

configure_logging()
log = structlog.get_logger()


async def main() -> None:
    log.info("seed.start", roles=len(ROLE_TEMPLATES))

    async with AsyncSessionLocal() as db:
        async with db.begin():
            inserted = await seed_roles_if_empty(db)

    if inserted:
        log.info("seed.done", inserted=inserted)
    else:
        log.info("seed.no_op", reason="all roles already present")


if __name__ == "__main__":
    asyncio.run(main())

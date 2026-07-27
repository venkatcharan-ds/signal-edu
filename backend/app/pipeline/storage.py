"""
Pipeline storage helpers — Stage 1 (GitHub Engine) DB writes.

Upserts Repository rows from GitHubEngine output.
Uses INSERT … ON CONFLICT DO UPDATE so re-running an analysis refreshes
existing rows rather than duplicating them.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository
from app.pipeline.github_engine import RepositorySignals, UserSignals

log = structlog.get_logger()


async def upsert_repositories(
    db: AsyncSession,
    user_id: uuid.UUID,
    signals: UserSignals,
) -> list[uuid.UUID]:
    """
    Upsert all repositories from UserSignals into the repositories table.
    Returns list of internal UUIDs for the upserted rows.
    """
    repo_ids: list[uuid.UUID] = []

    for repo in signals.repos:
        repo_id = await _upsert_one(db, user_id, repo)
        repo_ids.append(repo_id)

    await db.flush()
    log.info(
        "pipeline.storage.repos_upserted",
        user_id=str(user_id),
        count=len(repo_ids),
    )
    return repo_ids


async def _upsert_one(
    db: AsyncSession,
    user_id: uuid.UUID,
    sig: RepositorySignals,
) -> uuid.UUID:
    """
    INSERT … ON CONFLICT (github_repo_id) DO UPDATE.
    Returns the internal UUID of the row (new or existing).
    """
    new_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    stmt = text(
        """
        INSERT INTO repositories (
            id, user_id, github_repo_id, name, full_name, description,
            url, is_fork, stars, languages, commit_count, last_commit_at,
            has_readme, readme_content, readme_word_count,
            has_tests, has_ci, has_deployment_config,
            raw_github_data, fetched_at
        )
        VALUES (
            :id, :user_id, :github_repo_id, :name, :full_name, :description,
            :url, :is_fork, :stars, CAST(:languages AS jsonb), :commit_count, :last_commit_at,
            :has_readme, :readme_content, :readme_word_count,
            :has_tests, :has_ci, :has_deployment_config,
            CAST(:raw_github_data AS jsonb), :fetched_at
        )
        ON CONFLICT (github_repo_id) DO UPDATE SET
            name                  = EXCLUDED.name,
            full_name             = EXCLUDED.full_name,
            description           = EXCLUDED.description,
            url                   = EXCLUDED.url,
            is_fork               = EXCLUDED.is_fork,
            stars                 = EXCLUDED.stars,
            languages             = EXCLUDED.languages,
            commit_count          = EXCLUDED.commit_count,
            last_commit_at        = EXCLUDED.last_commit_at,
            has_readme            = EXCLUDED.has_readme,
            readme_content        = EXCLUDED.readme_content,
            readme_word_count     = EXCLUDED.readme_word_count,
            has_tests             = EXCLUDED.has_tests,
            has_ci                = EXCLUDED.has_ci,
            has_deployment_config = EXCLUDED.has_deployment_config,
            raw_github_data       = EXCLUDED.raw_github_data,
            fetched_at            = EXCLUDED.fetched_at
        RETURNING id
        """
    )

    import json

    result = await db.execute(
        stmt,
        {
            "id":                   new_id,
            "user_id":              user_id,
            "github_repo_id":       sig.repo_id,
            "name":                 sig.name,
            "full_name":            sig.full_name,
            "description":          sig.description,
            "url":                  sig.url,
            "is_fork":              sig.is_fork,
            "stars":                sig.stars,
            "languages":            json.dumps(sig.languages),
            "commit_count":         sig.commit_count,
            "last_commit_at":       sig.last_commit_at,
            "has_readme":           sig.has_readme,
            "readme_content":       sig.readme_content,
            "readme_word_count":    sig.readme_word_count,
            "has_tests":            sig.has_tests,
            "has_ci":               sig.has_ci,
            "has_deployment_config": sig.has_deployment_config,
            "raw_github_data":      json.dumps(sig.raw_data),
            "fetched_at":           now,
        },
    )

    row = result.fetchone()
    return row[0]

"""
GitHub API client.

Design decisions:
- Single httpx.AsyncClient for the lifetime of one pipeline run (connection pooling)
- Retry with exponential back-off on 5xx and network errors
- Rate-limit awareness: checks X-RateLimit-Remaining, backs off at < 50 remaining
- All methods are async; caller must use `async with GitHubService(token) as svc:`
- 404 responses are soft failures (repo gone mid-fetch) — return None, not raise
- Topics require Accept: application/vnd.github+json (already set)
"""
from __future__ import annotations

import asyncio
import base64
import re
import structlog
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = structlog.get_logger()

_API_BASE = "https://api.github.com"
_RETRY_STATUSES = {500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRY_STATUSES
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))


class GitHubService:
    """Async context manager — use as `async with GitHubService(token) as svc:`"""

    def __init__(self, token: str) -> None:
        self._token = token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GitHubService":
        self._client = httpx.AsyncClient(
            base_url=_API_BASE,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept":        "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Core request ─────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        assert self._client, "Use `async with GitHubService(token) as svc:`"
        response = await self._client.get(path, params=params)

        # Back off when approaching rate limit
        remaining = int(response.headers.get("X-RateLimit-Remaining", "9999"))
        if remaining < 50:
            reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
            import time
            sleep_for = max(0, reset_at - int(time.time())) + 1
            log.warning("github.rate_limit_low", remaining=remaining, sleeping_s=sleep_for)
            await asyncio.sleep(min(sleep_for, 60))

        if response.status_code in _RETRY_STATUSES:
            response.raise_for_status()

        return response

    # ── Public API methods ────────────────────────────────────────────────────

    async def get_authenticated_user(self) -> dict:
        """Return the authenticated user's profile."""
        r = await self._get("/user")
        r.raise_for_status()
        return r.json()

    async def get_repos(
        self,
        username: str,
        per_page: int = 100,
        sort: str = "pushed",
    ) -> list[dict]:
        """
        Return up to `per_page` public repos for a user, sorted by last push.
        Includes topics (requires Accept: application/vnd.github+json).
        """
        r = await self._get(
            f"/users/{username}/repos",
            params={"per_page": per_page, "sort": sort, "type": "owner"},
        )
        if r.status_code == 404:
            log.warning("github.user_not_found", username=username)
            return []
        r.raise_for_status()
        return r.json()

    async def get_languages(self, full_name: str) -> dict[str, int]:
        """
        Return language → byte-count mapping.
        e.g. {"Python": 12340, "Shell": 450, "Dockerfile": 120}
        """
        r = await self._get(f"/repos/{full_name}/languages")
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()

    async def get_readme(self, full_name: str) -> str | None:
        """
        Return decoded README text, or None if absent.
        Handles base64 encoding (default GitHub response format).
        """
        r = await self._get(f"/repos/{full_name}/readme")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        raw = data.get("content", "")
        encoding = data.get("encoding", "base64")
        if encoding == "base64":
            try:
                return base64.b64decode(raw.replace("\n", "")).decode("utf-8", errors="replace")
            except Exception:
                return None
        return raw or None

    async def get_file_paths(self, full_name: str, default_branch: str = "HEAD") -> list[str]:
        """
        Return all file paths in the repository tree (recursive).
        Used to detect tests, CI workflows, and deployment configs.
        Returns empty list on error (e.g. empty repo).
        """
        r = await self._get(
            f"/repos/{full_name}/git/trees/{default_branch}",
            params={"recursive": "1"},
        )
        if r.status_code in (404, 409):  # 409 = Git repository is empty
            return []
        r.raise_for_status()
        data = r.json()
        return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]

    async def get_commit_count(self, full_name: str) -> int:
        """
        Estimate total commit count using the Link header pagination trick.
        Single API request; not exact for repos with > 250 commits but close enough.
        """
        r = await self._get(
            f"/repos/{full_name}/commits",
            params={"per_page": 1},
        )
        if r.status_code in (404, 409):
            return 0
        r.raise_for_status()

        link = r.headers.get("link", "")
        match = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
        if match:
            return int(match.group(1))
        # Link header absent → all commits fit in one page
        commits = r.json()
        return len(commits) if isinstance(commits, list) else 0

    async def get_topics(self, full_name: str) -> list[str]:
        """
        Return repository topics list.
        Topics are included in repos list response but this provides a direct fetch.
        """
        r = await self._get(f"/repos/{full_name}/topics")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json().get("names", [])

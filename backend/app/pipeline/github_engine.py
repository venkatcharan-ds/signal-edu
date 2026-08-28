"""
GitHub Analysis Engine — Stage 1 of the SIGNAL pipeline.

Extracts objective signals from a user's public GitHub repositories.
No AI inference — all output is verifiable from the GitHub API.

Signals collected per repository:
  - Language composition (bytes per language)
  - Commit count and last-activity date
  - README presence and full text
  - Word count of README
  - Test file detection (path pattern matching)
  - CI workflow detection (path pattern matching)
  - Deployment config detection (path pattern matching)
  - Topics list
  - Fork status, stars, forks count

Concurrency model:
  Per-repo details (languages, readme, file tree, commit count) are fetched
  concurrently with asyncio.gather(), bounded by a semaphore to avoid
  hammering the GitHub API rate limit.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

from app.services.github_service import GitHubService

log = structlog.get_logger()

# File-path patterns used for evidence detection
_TEST_PATTERNS    = ("test/", "tests/", "_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js", "pytest", "unittest", "__tests__")
_CI_PATTERNS      = (".github/workflows/", ".travis.yml", "circle.yml", ".circleci/", "Jenkinsfile", "bitbucket-pipelines.yml", ".gitlab-ci.yml")
_DEPLOY_PATTERNS  = ("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "vercel.json", "Procfile", "railway.toml", "fly.toml", "render.yaml", "netlify.toml", ".platform.app.yaml")

# Repos younger than 1 year with at least 1 commit are "active"
_ACTIVE_DAYS = 365


@dataclass
class RepositorySignals:
    # Identity
    repo_id:    int
    name:       str
    full_name:  str
    url:        str
    description: str | None

    # Composition
    languages:     dict[str, int] = field(default_factory=dict)
    topics:        list[str]      = field(default_factory=list)

    # Activity
    commit_count:   int               = 0
    last_commit_at: datetime | None   = None
    stars:          int               = 0
    forks_count:    int               = 0

    # Evidence signals
    has_readme:            bool      = False
    readme_content:        str | None = None
    readme_word_count:     int       = 0
    has_tests:             bool      = False
    has_ci:                bool      = False
    has_deployment_config: bool      = False

    # Detected evidence files (paths that triggered each detection flag)
    detected_test_files:   list[str] = field(default_factory=list)
    detected_ci_files:     list[str] = field(default_factory=list)
    detected_deploy_files: list[str] = field(default_factory=list)

    # Meta
    is_fork:  bool = False
    raw_data: dict = field(default_factory=dict)


@dataclass
class UserSignals:
    github_username: str
    repos:           list[RepositorySignals] = field(default_factory=list)

    # Aggregated across all fetched repos
    total_languages:           dict[str, int] = field(default_factory=dict)
    any_has_tests:             bool           = False
    any_has_ci:                bool           = False
    any_has_deployment_config: bool           = False
    active_repo_count:         int            = 0
    total_stars:               int            = 0


class GitHubEngine:
    """
    Stage 1 of the SIGNAL pipeline.
    Uses GitHubService (async context manager) to fetch signals.
    """

    def __init__(self, github_token: str, max_concurrency: int = 5) -> None:
        self._token = github_token
        self._sem   = asyncio.Semaphore(max_concurrency)

    async def extract(self, username: str, max_repos: int = 20) -> UserSignals:
        """
        Fetch and extract signals from the user's public GitHub repositories.

        Filters:
          - Skips forks (unless the user has no original repos)
          - Takes the `max_repos` most-recently-pushed repos after filtering

        Returns a UserSignals aggregate ready for capability scoring.
        """
        log.info("github_engine.start", username=username, max_repos=max_repos)

        async with GitHubService(self._token) as svc:
            # Fetch repo list — sorted by last push, up to 100 (GitHub max per page)
            raw_repos: list[dict] = await svc.get_repos(username, per_page=100)

            if not raw_repos:
                log.warning("github_engine.no_repos", username=username)
                return UserSignals(github_username=username)

            # Filter forks unless the user has only forks
            originals = [r for r in raw_repos if not r.get("fork", False)]
            candidates = originals if originals else raw_repos
            candidates = candidates[:max_repos]

            log.info(
                "github_engine.repos_selected",
                username=username,
                total=len(raw_repos),
                after_filter=len(candidates),
            )

            # Fetch details concurrently, bounded by semaphore
            tasks = [self._fetch_repo_signals(svc, repo) for repo in candidates]
            results: list[RepositorySignals | None] = await asyncio.gather(*tasks, return_exceptions=False)

        repos = [r for r in results if r is not None]

        return self._aggregate(username, repos)

    # ── Per-repo fetch ────────────────────────────────────────────────────────

    async def _fetch_repo_signals(
        self,
        svc: GitHubService,
        repo: dict,
    ) -> RepositorySignals | None:
        full_name = repo["full_name"]

        async with self._sem:
            try:
                log.debug("github_engine.fetching_repo", repo=full_name)

                # Fire all detail requests concurrently for this repo
                languages, readme_text, file_paths, commit_count = await asyncio.gather(
                    svc.get_languages(full_name),
                    svc.get_readme(full_name),
                    svc.get_file_paths(full_name, repo.get("default_branch", "HEAD")),
                    svc.get_commit_count(full_name),
                )

                # Topics come from the repo list response (no extra request needed)
                topics: list[str] = repo.get("topics") or []

                last_commit_at: datetime | None = None
                pushed_at_str: str | None = repo.get("pushed_at")
                if pushed_at_str:
                    last_commit_at = datetime.fromisoformat(
                        pushed_at_str.replace("Z", "+00:00")
                    )

                readme_words  = len(readme_text.split()) if readme_text else 0
                _test_files   = self._match_tests(file_paths)
                _ci_files     = self._match_ci(file_paths)
                _deploy_files = self._match_deployment(file_paths)

                return RepositorySignals(
                    repo_id     = repo["id"],
                    name        = repo["name"],
                    full_name   = full_name,
                    url         = repo["html_url"],
                    description = repo.get("description"),

                    languages    = languages,
                    topics       = topics,

                    commit_count   = commit_count,
                    last_commit_at = last_commit_at,
                    stars          = repo.get("stargazers_count", 0),
                    forks_count    = repo.get("forks_count", 0),

                    has_readme            = readme_text is not None,
                    readme_content        = readme_text,
                    readme_word_count     = readme_words,
                    has_tests             = bool(_test_files),
                    has_ci                = bool(_ci_files),
                    has_deployment_config = bool(_deploy_files),
                    detected_test_files   = _test_files,
                    detected_ci_files     = _ci_files,
                    detected_deploy_files = _deploy_files,

                    is_fork  = repo.get("fork", False),
                    raw_data = {
                        "id":          repo["id"],
                        "language":    repo.get("language"),
                        "size":        repo.get("size", 0),
                        "open_issues": repo.get("open_issues_count", 0),
                        "visibility":  repo.get("visibility", "public"),
                        "topics":      topics,
                    },
                )

            except Exception as exc:
                log.warning("github_engine.repo_fetch_failed", repo=full_name, error=str(exc))
                return None

    # ── Aggregation ───────────────────────────────────────────────────────────

    def _aggregate(self, username: str, repos: list[RepositorySignals]) -> UserSignals:
        total_languages: dict[str, int] = {}
        for repo in repos:
            for lang, bytes_count in repo.languages.items():
                total_languages[lang] = total_languages.get(lang, 0) + bytes_count

        now = datetime.now(timezone.utc)
        active_repos = [
            r for r in repos
            if r.last_commit_at
            and (now - r.last_commit_at).days <= _ACTIVE_DAYS
        ]

        return UserSignals(
            github_username           = username,
            repos                     = repos,
            total_languages           = total_languages,
            any_has_tests             = any(r.has_tests for r in repos),
            any_has_ci                = any(r.has_ci for r in repos),
            any_has_deployment_config = any(r.has_deployment_config for r in repos),
            active_repo_count         = len(active_repos),
            total_stars               = sum(r.stars for r in repos),
        )

    # ── Pattern matchers ─────────────────────────────────────────────────────

    @staticmethod
    def _match_tests(paths: list[str]) -> list[str]:
        matched = []
        for p in paths:
            if any(pat in p.lower() for pat in _TEST_PATTERNS):
                matched.append(p)
        return matched[:5]

    @staticmethod
    def _match_ci(paths: list[str]) -> list[str]:
        matched = []
        for p in paths:
            pl = p.lower()
            if any(pl.startswith(pat.lower()) or pat.lower() in pl for pat in _CI_PATTERNS):
                matched.append(p)
        return matched[:5]

    @staticmethod
    def _match_deployment(paths: list[str]) -> list[str]:
        matched = []
        for p in paths:
            basename = p.split("/")[-1].lower()
            if any(pat.lower() == basename for pat in _DEPLOY_PATTERNS):
                matched.append(p)
        return matched[:5]

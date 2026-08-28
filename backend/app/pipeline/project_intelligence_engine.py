"""
Project Intelligence Engine — Stage 3.5 of the SIGNAL pipeline.

Analyzes the top repositories in a single Gemini call to produce structured
per-repo intelligence:
  - Classification and skill level
  - 7-dimension scoring on a 10-point scale
  - Technology status: Demonstrated / Inferred / Claimed / Not Demonstrated
  - Academic vs real-world readiness
  - Role relevance
  - Improvement recommendations

Called after Stage 3 (Capability Engine) with the same UserSignals and Gemini
client that are already in scope.  Stored under raw_ai_response["project_intelligence"].

Failure is intentionally non-fatal — a timeout or Gemini error here leaves
project_intelligence as an empty list; the rest of the profile is unaffected.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from google import genai
from google.genai import types
import structlog

from app.pipeline.github_engine import UserSignals, RepositorySignals

log = structlog.get_logger()

_MAX_REPOS = 5
_CALL_TIMEOUT = 45  # seconds — hard ceiling for this stage

# ── Gemini function-calling schema ────────────────────────────────────────────

_TECH_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["name", "status", "evidence"],
    properties={
        "name": types.Schema(type=types.Type.STRING, description="Technology name, e.g. 'FastAPI', 'PostgreSQL'."),
        "status": types.Schema(
            type=types.Type.STRING,
            enum=["demonstrated", "inferred", "claimed", "not_demonstrated"],
            description=(
                "demonstrated = verified by file paths or explicit signals in context; "
                "inferred = language detected but specific usage not confirmed; "
                "claimed = mentioned in README only, not in repo structure; "
                "not_demonstrated = absent but expected for this project type."
            ),
        ),
        "evidence": types.Schema(
            type=types.Type.STRING,
            description="One sentence citing the specific signal that justifies this status.",
        ),
    },
)

_DIM_SCORES_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["code_quality", "documentation", "architecture", "testing", "deployment_readiness", "complexity", "real_world_impact"],
    properties={
        "code_quality":          types.Schema(type=types.Type.NUMBER, minimum=1.0, maximum=10.0),
        "documentation":         types.Schema(type=types.Type.NUMBER, minimum=1.0, maximum=10.0),
        "architecture":          types.Schema(type=types.Type.NUMBER, minimum=1.0, maximum=10.0),
        "testing":               types.Schema(type=types.Type.NUMBER, minimum=1.0, maximum=10.0),
        "deployment_readiness":  types.Schema(type=types.Type.NUMBER, minimum=1.0, maximum=10.0),
        "complexity":            types.Schema(type=types.Type.NUMBER, minimum=1.0, maximum=10.0),
        "real_world_impact":     types.Schema(type=types.Type.NUMBER, minimum=1.0, maximum=10.0),
    },
)

_REPO_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=[
        "repo_full_name", "summary", "classification", "level",
        "overall_score", "dimension_scores", "academic_vs_realworld",
        "primary_technologies", "role_relevance", "improvement_recommendations",
        "how_it_works", "capabilities_demonstrated", "real_world_comparison",
    ],
    properties={
        "repo_full_name": types.Schema(type=types.Type.STRING),
        "summary": types.Schema(
            type=types.Type.STRING,
            description="2–3 sentence description of what this project demonstrates about the developer.",
        ),
        "classification": types.Schema(
            type=types.Type.STRING,
            enum=["Web Application", "API/Backend", "CLI Tool", "Library/Package",
                  "Data Science", "ML/AI", "DevOps/Infrastructure", "Mobile", "Other"],
        ),
        "level": types.Schema(
            type=types.Type.STRING,
            enum=["Beginner", "Intermediate", "Advanced"],
        ),
        "overall_score": types.Schema(
            type=types.Type.NUMBER, minimum=1.0, maximum=10.0,
            description="Weighted average of dimension scores (1–10).",
        ),
        "dimension_scores": _DIM_SCORES_SCHEMA,
        "academic_vs_realworld": types.Schema(
            type=types.Type.STRING,
            enum=["academic", "real_world", "mixed"],
            description=(
                "academic = course assignment or toy project; "
                "real_world = deployed or production-oriented; mixed = both."
            ),
        ),
        "primary_technologies": types.Schema(
            type=types.Type.ARRAY,
            items=_TECH_SCHEMA,
            description="Up to 8 key technologies. Status must reflect repo evidence.",
            max_items=8,
        ),
        "role_relevance": types.Schema(
            type=types.Type.OBJECT,
            description="Relevance to each target engineering role.",
            properties={
                "backend_engineer":   types.Schema(type=types.Type.STRING, enum=["high", "medium", "low", "none"]),
                "ml_engineer":        types.Schema(type=types.Type.STRING, enum=["high", "medium", "low", "none"]),
                "data_scientist":     types.Schema(type=types.Type.STRING, enum=["high", "medium", "low", "none"]),
                "frontend_engineer":  types.Schema(type=types.Type.STRING, enum=["high", "medium", "low", "none"]),
                "devops_engineer":    types.Schema(type=types.Type.STRING, enum=["high", "medium", "low", "none"]),
            },
        ),
        "improvement_recommendations": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
            description="Up to 3 specific, actionable improvements for this project.",
            max_items=3,
        ),
        "how_it_works": types.Schema(
            type=types.Type.STRING,
            description=(
                "2–3 sentences explaining HOW this project works internally: "
                "the design pattern, how data flows through the system, which core libraries "
                "handle the heavy lifting. Be specific to this repo — not generic boilerplate."
            ),
        ),
        "capabilities_demonstrated": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
            description=(
                "3–6 concrete engineering capabilities this repo directly demonstrates, "
                "each backed by evidence from the context. "
                "Bad: 'Uses Python'. "
                "Good: 'Async REST API with FastAPI, PostgreSQL integration via SQLAlchemy, "
                "JWT authentication middleware'. Only list what the evidence confirms."
            ),
            max_items=6,
        ),
        "real_world_comparison": types.Schema(
            type=types.Type.STRING,
            description=(
                "2–4 sentences comparing this project to three benchmarks: "
                "(1) a typical college assignment, "
                "(2) a strong internship-level project, "
                "(3) a production system. "
                "State specifically what is present and what would need to be added "
                "to reach each next level. Be honest and specific, not flattering."
            ),
        ),
    },
)

_PI_FUNCTION = types.FunctionDeclaration(
    name="record_project_intelligence",
    description=(
        "Record structured intelligence for each repository in the analyses list. "
        "Base every field on the evidence provided — do not invent repositories, files, or technologies."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        required=["analyses"],
        properties={
            "analyses": types.Schema(
                type=types.Type.ARRAY,
                items=_REPO_SCHEMA,
                description="One entry per repository, in the same order as the input context.",
            ),
        },
    ),
)

_SYSTEM_PROMPT = """\
You are the SIGNAL Project Intelligence engine. Analyze student developer repositories
and produce structured, evidence-grounded intelligence based ONLY on the context provided.
Every claim must be traceable to the evidence in the context.

RULES:
1. technology.status MUST reflect the actual evidence given:
   - demonstrated: a specific file path listed under "Test files:", "CI/CD files:", or
     "Deployment files:", OR confirmed by language byte count
   - inferred: the primary language is detected but no framework-specific evidence exists
   - claimed: the README mentions it but no file paths or language data confirm it
   - not_demonstrated: expected for this project type but absent from all evidence
   Use the exact file names listed to justify "demonstrated". If Deployment files shows
   "render.yaml" but no Dockerfile, do NOT claim Docker as demonstrated.
2. Score conservatively on a 1–10 scale:
   - "Test files: none detected" → testing score MUST be ≤ 3
   - README absent or < 50 words → documentation score MUST be ≤ 2
   - "Deployment files: none detected" → deployment_readiness MUST be ≤ 4
   - A toy project with 5 commits and no stars should not score 7+ on complexity.
3. overall_score will be recomputed server-side as the mean of dimension_scores.
   Provide an honest estimate — it will be overridden, but the dimension scores will not.
4. academic_vs_realworld: explicit deployment files (Dockerfile, render.yaml, vercel.json,
   fly.toml) in the context strongly indicate real_world orientation.
5. how_it_works: explain the internal mechanics specific to THIS repo — the data flow,
   design pattern used, which specific libraries handle the heavy lifting. Avoid generic
   statements like "it uses REST APIs". Name the specific framework and how it's used.
6. capabilities_demonstrated: only list what the repo evidence directly supports.
   Each capability must cite a signal from the context (a file name, a language, a topic).
   Write for a hiring manager who will verify these claims by looking at the repo.
7. real_world_comparison: be honest. A project with no tests, no CI, and no deployment
   config is not "approaching internship level" — say what's missing explicitly.
8. Do not reference repositories, files, or facts not explicitly present in the context.
"""


# ── Context builder ───────────────────────────────────────────────────────────

def _build_repo_context(repo: RepositorySignals) -> str:
    lines: list[str] = [f"=== REPOSITORY: {repo.full_name} ==="]
    if repo.description:
        lines.append(f"Description: {repo.description}")
    lines.append(f"Stars: {repo.stars} | Forks: {repo.forks_count} | Commits: {repo.commit_count}")
    lines.append(f"Is fork: {repo.is_fork}")

    if repo.languages:
        sorted_langs = sorted(repo.languages.items(), key=lambda x: x[1], reverse=True)
        top = ", ".join(f"{l} ({b:,}B)" for l, b in sorted_langs[:6])
        lines.append(f"Languages: {top}")

    if repo.topics:
        lines.append(f"Topics: {', '.join(repo.topics[:8])}")

    lines.append(f"README: {'present' if repo.has_readme else 'absent'} ({repo.readme_word_count} words)")
    lines.append(f"Test files: {', '.join(repo.detected_test_files) if repo.detected_test_files else 'none detected'}")
    lines.append(f"CI/CD files: {', '.join(repo.detected_ci_files) if repo.detected_ci_files else 'none detected'}")
    lines.append(f"Deployment files: {', '.join(repo.detected_deploy_files) if repo.detected_deploy_files else 'none detected'}")

    if repo.readme_content and repo.readme_word_count > 30:
        snippet = repo.readme_content[:500].replace("\n", " ")
        lines.append(f"README snippet: {snippet}…")

    return "\n".join(lines)


def _build_context(repos: list[RepositorySignals]) -> str:
    parts = [_build_repo_context(r) for r in repos]
    return "\n\n".join(parts)


# ── Engine ────────────────────────────────────────────────────────────────────

class ProjectIntelligenceEngine:
    """
    Stage 3.5 of the SIGNAL pipeline.
    One Gemini function-calling call covers all top repos and returns a list.
    """

    def __init__(self, client: genai.Client, model: str) -> None:
        self._client = client
        self._model = model

    async def analyze(
        self,
        signals: UserSignals,
    ) -> list[dict[str, Any]]:
        """
        Analyze the top repos (by stars, then activity) in a single Gemini call.
        Returns a list of raw dicts suitable for storing in raw_ai_response["project_intelligence"].
        Returns [] on any error — failure is non-fatal.
        """
        # Pick top repos — stars first, then most recently active
        candidates = sorted(
            signals.repos,
            key=lambda r: (r.stars, r.commit_count),
            reverse=True,
        )[:_MAX_REPOS]

        if not candidates:
            log.info("project_intelligence.no_repos")
            return []

        log.info("project_intelligence.start", repos=[r.full_name for r in candidates])

        try:
            result = await asyncio.wait_for(
                self._call_gemini(candidates),
                timeout=_CALL_TIMEOUT,
            )
            log.info("project_intelligence.complete", count=len(result))
            return result
        except asyncio.TimeoutError:
            log.warning("project_intelligence.timeout", timeout=_CALL_TIMEOUT)
            return []
        except Exception as exc:
            log.warning("project_intelligence.failed", error=str(exc))
            return []

    async def _call_gemini(self, repos: list[RepositorySignals]) -> list[dict[str, Any]]:
        context = _build_context(repos)

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=(
                "Analyze these repositories and record structured intelligence for each.\n\n"
                + context
            ),
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=[_PI_FUNCTION])],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY",
                        allowed_function_names=["record_project_intelligence"],
                    )
                ),
            ),
        )

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.function_call and part.function_call.name == "record_project_intelligence":
                    # Round-trip through JSON to ensure all nested MapComposite
                    # objects are converted to plain Python dicts/lists.
                    raw = json.loads(json.dumps(dict(part.function_call.args), default=str))
                    analyses = list(raw.get("analyses", []))
                    # Override overall_score with the server-computed mean of
                    # dimension_scores — this eliminates Gemini inconsistency.
                    for item in analyses:
                        dim = item.get("dimension_scores")
                        if isinstance(dim, dict):
                            vals = [float(v) for v in dim.values() if isinstance(v, (int, float))]
                            if len(vals) == 7:
                                server_score = sum(vals) / 7
                                item["overall_score"] = max(1.0, min(10.0, round(server_score, 1)))
                    return analyses

        raise ValueError(
            f"Gemini did not return function_call block. "
            f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}"
        )

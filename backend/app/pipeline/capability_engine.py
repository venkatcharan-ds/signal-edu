"""
Capability Intelligence Engine — Stage 3 of the SIGNAL pipeline.

Hybrid scoring formula per dimension:
  final_score = clamp(objective_component + ai_component, 1.0, 9.0)

  objective_component  = deterministic signals → 0.0 – 3.6  (40 % of 9-pt scale)
  ai_component         = Claude Sonnet analysis → 0.0 – 5.4  (60 % of 9-pt scale)

Anti-hallucination cap (§ ARCH-1):
  ai_component is clamped so that final_score cannot exceed
  (objective_component / 3.6 × 9.0) + 1.5

  Example: if objective = 1.8 (50 % of max) → ceiling = 4.5 + 1.5 = 6.0
  Claude may return an ai_component that would yield 7.2 — it is silently
  capped to 6.0.  The cap value is logged and stored in raw_ai_response.

Claude is called once per analysis with a tool-use schema that forces
structured JSON output.  A free-form prose field is also requested per
dimension so the UI can display narrative explanations.

Every citation must reference a specific artifact (repo full_name, README
word count, etc.) — the prompt explicitly forbids generic statements.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

import anthropic
import structlog

from app.pipeline.evidence_engine import ArtifactText
from app.pipeline.github_engine import UserSignals

log = structlog.get_logger()

# ── Scoring constants ─────────────────────────────────────────────────────────

# Objective ceiling for each dimension (40 % of 9-pt scale)
_OBJ_MAX = 3.6

# Maximum AI contribution (60 % of 9-pt scale)
_AI_MAX = 5.4

# Anti-hallucination: AI cannot push score more than N points above
# the normalised objective ceiling
_HALLUCINATION_CAP_DELTA = 1.5

# SIGNAL scale hard bounds
_SCORE_MIN = Decimal("1.0")
_SCORE_MAX = Decimal("9.0")

# Language complexity tiers
_LANG_LEVEL: dict[str, str] = {
    "rust": "advanced",   "c++": "advanced",  "c": "advanced",
    "go": "advanced",     "haskell": "advanced", "scala": "advanced",
    "zig": "advanced",    "ocaml": "advanced",
    "python": "intermediate", "typescript": "intermediate",
    "java": "intermediate",   "kotlin": "intermediate",
    "swift": "intermediate",  "c#": "intermediate",
    "ruby": "intermediate",   "elixir": "intermediate",
    "javascript": "beginner", "html": "beginner", "css": "beginner",
    "r": "beginner",          "matlab": "beginner", "shell": "beginner",
    "jupyter notebook": "beginner",
}
_LANG_SCORE = {"advanced": 1.2, "intermediate": 0.8, "beginner": 0.4}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class EvidenceCitationData:
    dimension: str          # "technical_execution" | "problem_complexity" | "communication_quality"
    citation_text: str      # Specific, citable sentence
    artifact_type: str      # "github_repo" | "readme" | "commit_history" | "ci_workflow"
    artifact_ref: str       # repo full_name or other locator
    score_contribution: float


@dataclass
class CapabilityScore:
    dimension: str
    score: Decimal
    confidence: Decimal
    objective_component: float
    ai_component: float
    ai_component_raw: float    # before cap — stored for auditability
    cap_applied: bool
    narrative: str             # Claude's prose explanation
    citations: list[EvidenceCitationData] = field(default_factory=list)


# ── Objective scoring ─────────────────────────────────────────────────────────

def _top_language_score(languages: dict[str, int]) -> tuple[float, str | None]:
    if not languages:
        return 0.0, None
    top = max(languages, key=lambda k: languages[k]).lower()
    level = _LANG_LEVEL.get(top, "beginner")
    return _LANG_SCORE[level], top


def compute_te_objective(signals: UserSignals) -> tuple[float, list[str]]:
    """
    Technical Execution objective component (max 3.6).
    Returns (score, list-of-evidence-strings).
    """
    evidence: list[str] = []
    score = 0.0

    lang_pts, top_lang = _top_language_score(signals.total_languages)
    if top_lang:
        level = _LANG_LEVEL.get(top_lang, "beginner")
        score += lang_pts
        evidence.append(f"Primary language {top_lang.title()} classified as {level} tier ({lang_pts:.1f} pts)")

    active_pts = min(signals.active_repo_count / 5, 1.0) * 0.8
    score += active_pts
    if signals.active_repo_count > 0:
        evidence.append(f"{signals.active_repo_count} active repositories in past 12 months ({active_pts:.2f} pts)")

    if signals.any_has_tests:
        score += 1.0
        evidence.append("Test suite detected in at least one repository (+1.0 pts)")

    if signals.any_has_ci:
        score += 0.6
        evidence.append("CI/CD workflow detected (.github/workflows or equivalent) (+0.6 pts)")

    if signals.any_has_deployment_config:
        score += 0.5
        evidence.append("Deployment configuration detected (Dockerfile, fly.toml, etc.) (+0.5 pts)")

    return min(score, _OBJ_MAX), evidence


def compute_pc_objective(signals: UserSignals) -> tuple[float, list[str]]:
    """
    Problem Complexity objective component (max 3.6).
    """
    evidence: list[str] = []
    score = 0.0

    unique_langs = len(signals.total_languages)
    lang_div_pts = min(unique_langs / 5, 1.0) * 0.9
    score += lang_div_pts
    if unique_langs > 0:
        evidence.append(f"{unique_langs} distinct languages used across repositories ({lang_div_pts:.2f} pts)")

    star_pts = min(signals.total_stars / 20, 1.0) * 0.6
    score += star_pts
    if signals.total_stars > 0:
        evidence.append(f"{signals.total_stars} total stars across repositories ({star_pts:.2f} pts)")

    active_pts = min(signals.active_repo_count / 8, 1.0) * 1.0
    score += active_pts
    if signals.active_repo_count > 0:
        evidence.append(f"{signals.active_repo_count} active repos — breadth of maintained work ({active_pts:.2f} pts)")

    # Repos with multiple languages suggest higher complexity projects
    multi_lang_repos = sum(
        1 for r in signals.repos if len(r.languages) >= 3
    )
    multi_pts = min(multi_lang_repos / 3, 1.0) * 0.6
    score += multi_pts
    if multi_lang_repos > 0:
        evidence.append(f"{multi_lang_repos} repositories use 3+ languages (polyglot complexity) ({multi_pts:.2f} pts)")

    if signals.any_has_deployment_config:
        score += 0.5
        evidence.append("Deployment automation signals real-world delivery complexity (+0.5 pts)")

    return min(score, _OBJ_MAX), evidence


def compute_cq_objective(signals: UserSignals) -> tuple[float, list[str]]:
    """
    Communication Quality objective component (max 3.6).
    """
    evidence: list[str] = []
    score = 0.0

    repos_with_readme = [r for r in signals.repos if r.has_readme]
    readme_ratio = len(repos_with_readme) / max(len(signals.repos), 1)
    ratio_pts = readme_ratio * 0.8
    score += ratio_pts
    if repos_with_readme:
        evidence.append(
            f"{len(repos_with_readme)}/{len(signals.repos)} repositories have a README "
            f"({readme_ratio:.0%} coverage, {ratio_pts:.2f} pts)"
        )

    # Average word count of READMEs that exist
    word_counts = [r.readme_word_count for r in repos_with_readme if r.readme_word_count > 0]
    if word_counts:
        avg_words = sum(word_counts) / len(word_counts)
        word_pts = min(avg_words / 300, 1.0) * 1.4
        score += word_pts
        evidence.append(
            f"Average README length {avg_words:.0f} words "
            f"(target ≥ 300 words, {word_pts:.2f} pts)"
        )

    # Topics signal deliberate project categorisation
    repos_with_topics = sum(1 for r in signals.repos if r.topics)
    if repos_with_topics:
        topic_pts = min(repos_with_topics / max(len(signals.repos), 1), 1.0) * 0.6
        score += topic_pts
        evidence.append(f"{repos_with_topics} repositories have topics set ({topic_pts:.2f} pts)")

    if signals.any_has_ci:
        score += 0.4
        evidence.append("CI configuration documents automated quality process (+0.4 pts)")

    return min(score, _OBJ_MAX), evidence


# ── Anti-hallucination cap ────────────────────────────────────────────────────

def apply_hallucination_cap(
    objective: float,
    ai_raw: float,
) -> tuple[float, bool]:
    """
    Returns (capped_ai_component, cap_was_applied).

    Objective is in [0, 3.6].  Normalised to [0, 9] → that is the ceiling.
    AI component may not push the combined score more than 1.5 above that ceiling.
    """
    obj_normalised = (objective / _OBJ_MAX) * 9.0 if _OBJ_MAX > 0 else 0.0
    max_combined = obj_normalised + _HALLUCINATION_CAP_DELTA
    combined_raw = objective + ai_raw
    if combined_raw > max_combined:
        # Clamp AI component to make combined == max_combined
        capped_ai = max(max_combined - objective, 0.0)
        return capped_ai, True
    return ai_raw, False


def _clamp_score(value: float) -> Decimal:
    d = Decimal(str(round(value, 1)))
    return max(_SCORE_MIN, min(_SCORE_MAX, d))


# ── Claude prompt builder ─────────────────────────────────────────────────────

def _build_context(signals: UserSignals, artifacts: list[ArtifactText]) -> str:
    """
    Build a compact text context for Claude.  Deliberately concise to stay
    within token budgets and prevent the model from inventing unseen details.
    """
    lines: list[str] = ["=== GITHUB SIGNALS ==="]

    lines.append(f"GitHub username: {signals.github_username}")
    lines.append(f"Total repos analysed: {len(signals.repos)}")
    lines.append(f"Active repos (≤12 months): {signals.active_repo_count}")
    lines.append(f"Total stars: {signals.total_stars}")

    if signals.total_languages:
        sorted_langs = sorted(
            signals.total_languages.items(), key=lambda x: x[1], reverse=True
        )
        top5 = ", ".join(f"{lang} ({bytes_:,} bytes)" for lang, bytes_ in sorted_langs[:5])
        lines.append(f"Language composition (top 5): {top5}")

    lines.append(f"Has test suite in any repo: {signals.any_has_tests}")
    lines.append(f"Has CI/CD in any repo: {signals.any_has_ci}")
    lines.append(f"Has deployment config in any repo: {signals.any_has_deployment_config}")

    lines.append("\n=== REPOSITORY DETAILS ===")
    for repo in signals.repos[:15]:  # cap at 15 to control context size
        lines.append(
            f"- {repo.full_name}: "
            f"{repo.commit_count} commits, "
            f"{repo.stars} stars, "
            f"langs=[{', '.join(list(repo.languages.keys())[:4])}], "
            f"readme={repo.has_readme}({repo.readme_word_count}w), "
            f"tests={repo.has_tests}, ci={repo.has_ci}, deploy={repo.has_deployment_config}, "
            f"topics=[{', '.join(repo.topics[:5])}]"
        )
        if repo.readme_content and repo.readme_word_count > 50:
            # Include first 400 chars of README for Claude to assess quality
            snippet = repo.readme_content[:400].replace("\n", " ")
            lines.append(f"  README snippet: {snippet}…")

    if artifacts:
        lines.append("\n=== ADDITIONAL EVIDENCE ===")
        for art in artifacts:
            lines.append(
                f"- [{art.type}] {art.title or 'Untitled'}: {art.word_count} words"
            )

    return "\n".join(lines)


# ── Tool schema for structured Claude output ──────────────────────────────────

_SCORING_TOOL: dict = {
    "name": "record_capability_scores",
    "description": (
        "Record the SIGNAL capability scores with mandatory evidence citations. "
        "Every ai_score must be supported by at least two citations from the provided data. "
        "Do not reference repositories, files, or facts not present in the context above."
    ),
    "input_schema": {
        "type": "object",
        "required": ["technical_execution", "problem_complexity", "communication_quality"],
        "additionalProperties": False,
        "properties": {
            "technical_execution": {
                "type": "object",
                "required": ["ai_score", "confidence", "narrative", "citations"],
                "additionalProperties": False,
                "properties": {
                    "ai_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 5.4,
                        "description": "AI component only (0–5.4). The objective component (0–3.6) is added server-side.",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Model confidence in this assessment (0.0–1.0).",
                    },
                    "narrative": {
                        "type": "string",
                        "description": "2–3 sentence explanation citing specific repositories and signals from the context.",
                    },
                    "citations": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["text", "artifact_type", "artifact_ref", "contribution"],
                            "additionalProperties": False,
                            "properties": {
                                "text": {"type": "string", "description": "Specific citable fact from the context."},
                                "artifact_type": {
                                    "type": "string",
                                    "enum": ["github_repo", "readme", "commit_history", "ci_workflow", "deployment_config", "language_signal"],
                                },
                                "artifact_ref": {"type": "string", "description": "repo full_name or other locator from context."},
                                "contribution": {"type": "number", "description": "Score contribution of this citation (0.0–2.0)."},
                            },
                        },
                    },
                },
            },
            "problem_complexity": {
                "type": "object",
                "required": ["ai_score", "confidence", "narrative", "citations"],
                "additionalProperties": False,
                "properties": {
                    "ai_score": {"type": "number", "minimum": 0.0, "maximum": 5.4},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "narrative": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["text", "artifact_type", "artifact_ref", "contribution"],
                            "additionalProperties": False,
                            "properties": {
                                "text": {"type": "string"},
                                "artifact_type": {
                                    "type": "string",
                                    "enum": ["github_repo", "readme", "commit_history", "ci_workflow", "deployment_config", "language_signal"],
                                },
                                "artifact_ref": {"type": "string"},
                                "contribution": {"type": "number"},
                            },
                        },
                    },
                },
            },
            "communication_quality": {
                "type": "object",
                "required": ["ai_score", "confidence", "narrative", "citations"],
                "additionalProperties": False,
                "properties": {
                    "ai_score": {"type": "number", "minimum": 0.0, "maximum": 5.4},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "narrative": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["text", "artifact_type", "artifact_ref", "contribution"],
                            "additionalProperties": False,
                            "properties": {
                                "text": {"type": "string"},
                                "artifact_type": {
                                    "type": "string",
                                    "enum": ["github_repo", "readme", "commit_history", "ci_workflow", "deployment_config", "language_signal"],
                                },
                                "artifact_ref": {"type": "string"},
                                "contribution": {"type": "number"},
                            },
                        },
                    },
                },
            },
            "verified_capabilities": {
                "type": "array",
                "description": "List of specific, citable capability strings. Max 10. Every entry must reference a repo or artifact from the context.",
                "items": {"type": "string"},
                "maxItems": 10,
            },
        },
    },
}

_SYSTEM_PROMPT = """\
You are the SIGNAL capability scoring engine. Your job is to assess a student developer's \
capability across three dimensions based ONLY on verifiable GitHub evidence provided to you.

RULES — violation of any rule invalidates the assessment:
1. Every citation must reference a specific repository, file, commit count, or signal \
   explicitly present in the context. Never invent repositories or facts.
2. ai_score is your AI contribution (0–5.4). The objective component (0–3.6) is added \
   server-side. Together they form a 9-point scale.
3. Score conservatively. A student with 3 repos and no tests should not receive an \
   ai_score above 2.5 for technical_execution.
4. verified_capabilities must be specific: "FastAPI REST API with PostgreSQL" is valid; \
   "backend development" is not.
5. Do not penalise for technologies the student hasn't used — only score what is present.
6. Do not reference the hallucination cap — just score honestly from the evidence.
"""


# ── Main engine ───────────────────────────────────────────────────────────────

class CapabilityEngine:
    """
    Stage 3 of the SIGNAL pipeline.
    Call `score_all()` with GitHub signals and optional artifact texts.
    Returns three CapabilityScore objects + a list of verified capability strings.
    """

    def __init__(self, client: anthropic.AsyncAnthropic, model: str) -> None:
        self._client = client
        self._model = model

    async def score_all(
        self,
        signals: UserSignals,
        artifacts: list[ArtifactText],
        *,
        model_override: str | None = None,
    ) -> tuple[list[CapabilityScore], list[str]]:
        """
        Score TE, PC, CQ in a single Claude call.

        Returns:
          scores           — list[CapabilityScore] with combined final scores
          verified_capabilities — list[str] of specific capability strings
        """
        context = _build_context(signals, artifacts)

        # ── Objective components ──────────────────────────────────────────────
        te_obj, te_obj_ev  = compute_te_objective(signals)
        pc_obj, pc_obj_ev  = compute_pc_objective(signals)
        cq_obj, cq_obj_ev  = compute_cq_objective(signals)

        log.info(
            "capability_engine.objective_scores",
            te=round(te_obj, 3),
            pc=round(pc_obj, 3),
            cq=round(cq_obj, 3),
        )

        # ── Claude AI components ──────────────────────────────────────────────
        model = model_override or self._model
        raw_response = await self._call_claude(context, model)

        te_raw  = raw_response["technical_execution"]
        pc_raw  = raw_response["problem_complexity"]
        cq_raw  = raw_response["communication_quality"]
        verified = raw_response.get("verified_capabilities", [])

        # ── Apply hallucination cap + combine ─────────────────────────────────
        scores: list[CapabilityScore] = []
        for dim, obj, raw_dim, obj_evidence in [
            ("technical_execution",   te_obj, te_raw,  te_obj_ev),
            ("problem_complexity",    pc_obj, pc_raw,  pc_obj_ev),
            ("communication_quality", cq_obj, cq_raw,  cq_obj_ev),
        ]:
            ai_raw   = float(raw_dim["ai_score"])
            ai_capped, cap_applied = apply_hallucination_cap(obj, ai_raw)

            if cap_applied:
                log.warning(
                    "capability_engine.cap_applied",
                    dimension=dim,
                    ai_raw=ai_raw,
                    ai_capped=ai_capped,
                    objective=obj,
                )

            combined = _clamp_score(obj + ai_capped)

            # Build citations — objective first, then Claude's
            citations: list[EvidenceCitationData] = []
            for ev_text in obj_evidence:
                citations.append(EvidenceCitationData(
                    dimension=dim,
                    citation_text=ev_text,
                    artifact_type="github_repo",
                    artifact_ref=signals.github_username,
                    score_contribution=0.0,  # objective, already counted
                ))
            for cite in raw_dim.get("citations", []):
                citations.append(EvidenceCitationData(
                    dimension=dim,
                    citation_text=cite["text"],
                    artifact_type=cite["artifact_type"],
                    artifact_ref=cite["artifact_ref"],
                    score_contribution=float(cite.get("contribution", 0.0)),
                ))

            scores.append(CapabilityScore(
                dimension=dim,
                score=combined,
                confidence=Decimal(str(round(float(raw_dim["confidence"]), 2))),
                objective_component=obj,
                ai_component=ai_capped,
                ai_component_raw=ai_raw,
                cap_applied=cap_applied,
                narrative=raw_dim.get("narrative", ""),
                citations=citations,
            ))

        log.info(
            "capability_engine.final_scores",
            **{s.dimension: str(s.score) for s in scores},
        )
        return scores, verified

    async def _call_claude(self, context: str, model: str) -> dict:
        """
        Single Claude tool-use call.  Returns the parsed tool input dict.
        Raises ValueError on unexpected response shape.
        """
        response = await self._client.messages.create(
            model=model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            tools=[_SCORING_TOOL],
            tool_choice={"type": "tool", "name": "record_capability_scores"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Score this student's capabilities based ONLY on the evidence below.\n\n"
                        + context
                    ),
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "record_capability_scores":
                return block.input  # type: ignore[return-value]

        raise ValueError(
            f"Claude did not return tool_use block. Stop reason: {response.stop_reason}. "
            f"Content: {response.content}"
        )

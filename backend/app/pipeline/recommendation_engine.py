"""
Recommendation Engine — Stage 5 of the SIGNAL pipeline.

Uses Claude Haiku to generate exactly 3 prioritised, evidence-backed
recommendations for a student's identified gaps.

Design constraints:
- Recommendations are NOT generic advice ("learn Docker").
- Each recommendation names a specific project type, references the student's
  existing languages/themes, and specifies an evidence_type so the gap can
  be closed in a measurable way.
- Haiku is used (not Sonnet) for cost efficiency — the context is small and
  the output schema is tight.
"""
from __future__ import annotations

from dataclasses import dataclass

import anthropic
import structlog

from app.pipeline.gap_engine import GapResult

log = structlog.get_logger()


@dataclass
class RecommendationData:
    dimension: str     # "technical_execution" | "problem_complexity" | "communication_quality"
    priority: int      # 1 = most impactful
    title: str
    description: str
    evidence_type: str  # "github_repo" | "readme" | "ci_workflow" | "deployment_config" | "pdf"


_TOOL: dict = {
    "name": "record_recommendations",
    "description": "Record exactly 3 actionable, evidence-backed recommendations for the student.",
    "input_schema": {
        "type": "object",
        "required": ["recommendations"],
        "additionalProperties": False,
        "properties": {
            "recommendations": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["dimension", "priority", "title", "description", "evidence_type"],
                    "additionalProperties": False,
                    "properties": {
                        "dimension": {
                            "type": "string",
                            "enum": [
                                "technical_execution",
                                "problem_complexity",
                                "communication_quality",
                            ],
                        },
                        "priority": {"type": "integer", "minimum": 1, "maximum": 3},
                        "title": {
                            "type": "string",
                            "maxLength": 120,
                            "description": "Short action title shown as a card header in the UI.",
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "2–4 sentences. Name a specific project idea using the student's "
                                "existing languages. Explain what gap it closes and why. "
                                "Do not use generic phrases like 'learn X' without a concrete project."
                            ),
                        },
                        "evidence_type": {
                            "type": "string",
                            "enum": ["github_repo", "readme", "ci_workflow", "deployment_config", "pdf", "link"],
                            "description": "The type of artifact the student must produce to close this gap.",
                        },
                    },
                },
            }
        },
    },
}

_SYSTEM_PROMPT = """\
You are the SIGNAL recommendation engine. You generate specific, actionable improvement \
recommendations for student developers based on their gap analysis.

RULES:
1. Address the largest gaps first (priority 1 = biggest gap).
2. Recommendations must be concrete — name a real project idea using the student's languages.
3. Each recommendation must specify what the student needs to BUILD or WRITE (not just learn).
4. If the student's primary language is Python, suggest a Python project. \
   Do not suggest switching languages.
5. evidence_type must match what the student needs to produce to close the gap.
6. Avoid buzzwords. Be specific and practical.
"""


class RecommendationEngine:
    """Stage 5 of the SIGNAL pipeline."""

    def __init__(self, client: anthropic.AsyncAnthropic, model: str) -> None:
        self._client = client
        self._model = model

    async def generate(
        self,
        gap_result: GapResult,
        student_languages: list[str],
        student_themes: list[str],
        te_narrative: str = "",
        pc_narrative: str = "",
        cq_narrative: str = "",
    ) -> list[RecommendationData]:
        """
        Generate 3 prioritised recommendations for the identified gaps.
        Gaps with the largest absolute deficit get priority 1.
        """
        context = _build_context(
            gap_result, student_languages, student_themes,
            te_narrative, pc_narrative, cq_narrative,
        )

        raw = await self._call_claude(context)
        recs = raw.get("recommendations", [])

        result: list[RecommendationData] = []
        for rec in recs[:3]:
            result.append(RecommendationData(
                dimension=rec["dimension"],
                priority=int(rec["priority"]),
                title=rec["title"],
                description=rec["description"],
                evidence_type=rec["evidence_type"],
            ))

        log.info(
            "recommendation_engine.generated",
            role=gap_result.role_slug,
            count=len(result),
        )
        return result

    async def _call_claude(self, context: str) -> dict:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "record_recommendations"},
            messages=[{"role": "user", "content": context}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "record_recommendations":
                return block.input  # type: ignore[return-value]

        raise ValueError(
            f"Claude Haiku did not return tool_use block. "
            f"Stop reason: {response.stop_reason}"
        )


def _build_context(
    gap: GapResult,
    languages: list[str],
    themes: list[str],
    te_narrative: str,
    pc_narrative: str,
    cq_narrative: str,
) -> str:
    lines: list[str] = [
        f"=== GAP ANALYSIS — {gap.role_title} ===",
        f"Role: {gap.role_slug}",
        f"Overall ready: {gap.overall_ready}",
        "",
        "Dimension gaps (negative = below threshold, positive = exceeds):",
        f"  Technical Execution:   {gap.te_gap:+.1f}",
        f"  Problem Complexity:    {gap.pc_gap:+.1f}",
        f"  Communication Quality: {gap.cq_gap:+.1f}",
        "",
        "Missing signals:",
    ]
    for sig in gap.missing_signals:
        lines.append(f"  - {sig}")

    lines.extend([
        "",
        "=== STUDENT CONTEXT ===",
        f"Primary languages: {', '.join(languages[:6]) if languages else 'unknown'}",
        f"Project themes: {', '.join(themes[:8]) if themes else 'none detected'}",
        "",
        "=== CURRENT CAPABILITY NARRATIVES ===",
    ])
    if te_narrative:
        lines.append(f"Technical Execution: {te_narrative}")
    if pc_narrative:
        lines.append(f"Problem Complexity: {pc_narrative}")
    if cq_narrative:
        lines.append(f"Communication Quality: {cq_narrative}")

    lines.append(
        "\nGenerate 3 recommendations that close the largest gaps. "
        "Priority 1 must address the dimension with the most negative gap."
    )
    return "\n".join(lines)

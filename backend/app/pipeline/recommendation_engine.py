"""
Recommendation Engine — Stage 5 of the SIGNAL pipeline.

Uses Gemini Flash to generate exactly 3 prioritised, evidence-backed
recommendations for a student's identified gaps.

Design constraints:
- Recommendations are NOT generic advice ("learn Docker").
- Each recommendation names a specific project type, references the student's
  existing languages/themes, and specifies an evidence_type so the gap can
  be closed in a measurable way.
- Flash is used (not Pro) for cost efficiency — the context is small and
  the output schema is tight.
"""
from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai import types
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


_REC_FUNCTION = types.FunctionDeclaration(
    name="record_recommendations",
    description="Record exactly 3 actionable, evidence-backed recommendations for the student.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        required=["recommendations"],
        properties={
            "recommendations": types.Schema(
                type=types.Type.ARRAY,
                min_items=3,
                max_items=3,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    required=["dimension", "priority", "title", "description", "evidence_type"],
                    properties={
                        "dimension": types.Schema(
                            type=types.Type.STRING,
                            enum=[
                                "technical_execution",
                                "problem_complexity",
                                "communication_quality",
                            ],
                        ),
                        "priority": types.Schema(
                            type=types.Type.INTEGER,
                            minimum=1,
                            maximum=3,
                        ),
                        "title": types.Schema(
                            type=types.Type.STRING,
                            max_length=120,
                            description="Short action title shown as a card header in the UI.",
                        ),
                        "description": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "2–4 sentences. Name a specific project idea using the student's "
                                "existing languages. Explain what gap it closes and why. "
                                "Do not use generic phrases like 'learn X' without a concrete project."
                            ),
                        ),
                        "evidence_type": types.Schema(
                            type=types.Type.STRING,
                            enum=["github_repo", "readme", "ci_workflow", "deployment_config", "pdf", "link"],
                            description="The type of artifact the student must produce to close this gap.",
                        ),
                    },
                ),
            ),
        },
    ),
)

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

    def __init__(self, client: genai.Client, model: str) -> None:
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

        raw = await self._call_gemini(context)
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

    async def _call_gemini(self, context: str) -> dict:
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=context,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=[_REC_FUNCTION])],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY",
                        allowed_function_names=["record_recommendations"],
                    )
                ),
            ),
        )

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.function_call and part.function_call.name == "record_recommendations":
                    return dict(part.function_call.args)

        raise ValueError(
            f"Gemini did not return function_call block. "
            f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'unknown'}"
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

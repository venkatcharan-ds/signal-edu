"""
Recommendation generation prompt for Claude Haiku.

CONTRACT:
- Exactly 3 recommendations, ordered by gap severity (largest gap first)
- Each recommendation must be specific and evidence-typed
- Never say "learn more X" — always say "build a project that demonstrates X"
- Each recommendation maps to a specific scoring rubric signal
"""


def build_recommendation_prompt(
    target_role: str,
    gaps: list[dict],
    student_themes: list[str],
    student_languages: list[str],
    current_scores: dict,
) -> str:
    gaps_str = "\n".join(
        f"  - {g['dimension']}: {abs(g['delta']):.1f} points below threshold "
        f"(missing signals: {', '.join(g['missing_signals'])})"
        for g in sorted(gaps, key=lambda x: abs(x["delta"]), reverse=True)
    )
    themes_str = ", ".join(student_themes) if student_themes else "general software"
    langs_str = ", ".join(student_languages) if student_languages else "Python"

    return f"""You are generating project recommendations for a student on SIGNAL EDU.

Target role: {target_role}
Student's existing project themes: {themes_str}
Student's primary languages: {langs_str}
Current scores: TE={current_scores.get('te', 0):.1f}, PC={current_scores.get('pc', 0):.1f}, CQ={current_scores.get('cq', 0):.1f}

GAPS TO CLOSE:
{gaps_str}

RECOMMENDATION RULES:
1. Generate EXACTLY 3 recommendations
2. Each must be specific — name an evidence type, a data source, or a system to build
3. Tie each recommendation to the student's existing themes when possible
4. Never say "learn X" — say "build a project that demonstrates X"
5. Each must include an evidence_type that maps to a scoring rubric signal
6. Recommendations must be achievable in 2–4 weeks

EVIDENCE TYPES:
- real_world_dataset: uses non-benchmark, real-world data
- production_deployment: deployed to a real environment
- ci_cd_pipeline: GitHub Actions or equivalent CI setup
- test_coverage: unit/integration tests present
- quantified_outcomes: results measured and documented
- multi_system_integration: multiple services/APIs connected
- technical_documentation: detailed README with setup + examples
- novel_methodology: non-standard algorithmic approach

OUTPUT FORMAT:
```json
{{
  "recommendations": [
    {{
      "dimension": "technical_execution|problem_complexity|communication_quality",
      "priority": 1,
      "title": "<concise action title>",
      "description": "<specific, evidence-typed 2-3 sentence description>",
      "evidence_type": "<one of the evidence types above>"
    }},
    ...
  ]
}}
```"""

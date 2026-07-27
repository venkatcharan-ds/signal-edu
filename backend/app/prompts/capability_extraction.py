"""
Capability extraction prompt for Claude Sonnet.

CONTRACT:
- Every score MUST have at least one specific evidence citation.
- If no artifact justifies a sub-score, assign zero for that sub-score.
- AI component for Technical Execution cannot exceed objective_te_ceiling + 1.5 points.
- Return valid JSON matching the schema exactly.
"""


def build_capability_prompt(
    github_signals: dict,
    artifact_texts: list[dict],
    objective_te: float,
    objective_te_ceiling: float,
) -> str:
    signals_str = _format_signals(github_signals)
    artifacts_str = _format_artifacts(artifact_texts)

    return f"""You are a technical capability evaluator for SIGNAL EDU.
Your task is to evaluate a student's real engineering capability from their work artifacts.

SCORING RULES (follow exactly):
1. Score each dimension 1.0–9.0 in increments of 0.1
2. For EVERY score, provide a specific evidence citation naming the exact artifact or code pattern
3. If no artifact justifies a sub-score, assign 0 for that component — never fabricate evidence
4. Technical Execution AI component: your AI assessment may NOT produce a final TE score
   above {objective_te_ceiling + 1.5:.1f} (the objective ceiling {objective_te_ceiling:.1f} + 1.5 cap)
5. Return ONLY valid JSON — no prose before or after

CALIBRATION ANCHORS:
- Emerging (1–3): Tutorial-level work, single language, no deployment, minimal documentation
- Developing (4–6): Multiple projects, some structure, evidence of real-world awareness
- Advanced (7–9): Production systems, CI/CD, real-world data, deployment, strong documentation

OBJECTIVE SIGNALS (pre-computed, weight 40%):
{signals_str}

ARTIFACTS (PDFs, links — weight included in qualitative assessment):
{artifacts_str}

SCORING RUBRIC:

Technical Execution (assesses engineering quality):
- Primary languages and sophistication level
- Repository completeness (not just scaffolds)
- Test coverage presence
- CI/CD and deployment configuration
- Code modularity and architecture (inferred from file structure and README)

Problem Complexity (assesses what the student chose to build):
Binary rubric — answer each YES/NO with specific evidence:
1. Is the problem self-defined (not a tutorial/assignment)? [0 or 1]
2. Does it use real-world data (not benchmark/synthetic)? [0 or 1]
3. Does it integrate multiple systems? [0, 1, or 2]
4. Is the methodology non-standard (novel approach)? [0, 1, or 2]
5. Are outcomes quantified in documentation? [0 or 1]
6. Novel deployment context (constrained environment, real users)? [0 or 1]
Sum / 8 * 9 = final score

Communication Quality (assesses documentation and explanation):
- README word count and structure
- Presence of setup instructions, code examples, result descriptions
- Documentation completeness
- Notebook narrative quality (if Jupyter present)
- Writing quality in uploaded artifacts

OUTPUT FORMAT (return exactly this JSON):
```json
{{
  "technical_execution": {{
    "ai_component": <float 0.0–5.4>,
    "final_score": <float 1.0–9.0>,
    "confidence": <float 0.0–1.0>,
    "citations": [
      {{
        "citation_text": "<specific evidence>",
        "artifact_type": "repository|pdf|link",
        "artifact_ref": "<repo name or URL>",
        "score_contribution": <float>
      }}
    ]
  }},
  "problem_complexity": {{
    "sub_scores": {{
      "self_defined": <0 or 1>,
      "real_world_data": <0 or 1>,
      "multi_system": <0, 1, or 2>,
      "novel_methodology": <0, 1, or 2>,
      "quantified_outcomes": <0 or 1>,
      "novel_deployment": <0 or 1>
    }},
    "final_score": <float 1.0–9.0>,
    "confidence": <float 0.0–1.0>,
    "citations": [...]
  }},
  "communication_quality": {{
    "final_score": <float 1.0–9.0>,
    "confidence": <float 0.0–1.0>,
    "citations": [...]
  }},
  "verified_capabilities": [
    "<specific capability string e.g. 'Production deployment on constrained hardware'>",
    ...
  ]
}}
```"""


def _format_signals(signals: dict) -> str:
    lines = []
    for key, val in signals.items():
        lines.append(f"  {key}: {val}")
    return "\n".join(lines) if lines else "  (no signals)"


def _format_artifacts(artifacts: list[dict]) -> str:
    if not artifacts:
        return "  (no additional artifacts uploaded)"
    lines = []
    for a in artifacts:
        lines.append(f"  [{a.get('type', 'unknown')}] {a.get('title', 'Untitled')} ({a.get('word_count', 0)} words)")
        if a.get("preview"):
            lines.append(f"    Preview: {a['preview'][:300]}...")
    return "\n".join(lines)

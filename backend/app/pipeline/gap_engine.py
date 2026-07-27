"""
Gap Engine — Stage 4 of the pipeline.

Deterministic. No AI.
Compares a capability profile against a role template
and computes per-dimension gaps.

Negative gap = below threshold (needs work).
Positive gap = above threshold (exceeds requirement).
"""
from decimal import Decimal
from dataclasses import dataclass
import structlog

log = structlog.get_logger()


@dataclass
class GapResult:
    role_slug: str
    role_title: str
    te_gap: Decimal
    pc_gap: Decimal
    cq_gap: Decimal
    overall_ready: bool
    missing_signals: list[str]


class GapEngine:
    def compute(
        self,
        te_score: Decimal,
        pc_score: Decimal,
        cq_score: Decimal,
        role_te: Decimal,
        role_pc: Decimal,
        role_cq: Decimal,
        role_slug: str,
        role_title: str,
    ) -> GapResult:
        te_gap = te_score - role_te
        pc_gap = pc_score - role_pc
        cq_gap = cq_score - role_cq
        overall_ready = te_gap >= 0 and pc_gap >= 0 and cq_gap >= 0

        missing_signals = []
        if te_gap < 0:
            missing_signals.append(f"technical_execution: {abs(te_gap):.1f} below threshold")
        if pc_gap < 0:
            missing_signals.append(f"problem_complexity: {abs(pc_gap):.1f} below threshold")
        if cq_gap < 0:
            missing_signals.append(f"communication_quality: {abs(cq_gap):.1f} below threshold")

        return GapResult(
            role_slug=role_slug,
            role_title=role_title,
            te_gap=te_gap,
            pc_gap=pc_gap,
            cq_gap=cq_gap,
            overall_ready=overall_ready,
            missing_signals=missing_signals,
        )

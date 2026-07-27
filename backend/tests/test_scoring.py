"""
Unit tests for the deterministic scoring components.
These tests must pass with zero external API calls.
"""
import os
from decimal import Decimal

import pytest

# Inject minimal required env vars before any app import triggers Settings()
_ENV_DEFAULTS = {
    "DATABASE_URL":              "postgresql+asyncpg://x:x@localhost/test",
    "SUPABASE_URL":              "https://test.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SUPABASE_JWT_SECRET":       "test-jwt-secret-32-chars-minimum!!",
    "GITHUB_CLIENT_ID":          "test-client-id",
    "GITHUB_CLIENT_SECRET":      "test-client-secret",
    "ANTHROPIC_API_KEY":         "test-anthropic-key",
    "ENVIRONMENT":               "test",
    "DEBUG":                     "false",
}
for _k, _v in _ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)


# ── Gap Engine ────────────────────────────────────────────────────────────────

from app.pipeline.gap_engine import GapEngine


def test_gap_engine_below_threshold():
    engine = GapEngine()
    result = engine.compute(
        te_score=Decimal("5.5"), pc_score=Decimal("4.0"), cq_score=Decimal("6.0"),
        role_te=Decimal("7.0"), role_pc=Decimal("6.5"), role_cq=Decimal("5.5"),
        role_slug="ml-engineer", role_title="ML Engineer",
    )
    assert result.overall_ready is False
    assert result.te_gap == Decimal("-1.5")
    assert result.pc_gap == Decimal("-2.5")
    assert result.cq_gap == Decimal("0.5")
    assert len(result.missing_signals) == 2


def test_gap_engine_above_threshold():
    engine = GapEngine()
    result = engine.compute(
        te_score=Decimal("8.0"), pc_score=Decimal("7.5"), cq_score=Decimal("7.0"),
        role_te=Decimal("7.0"), role_pc=Decimal("6.5"), role_cq=Decimal("5.5"),
        role_slug="ml-engineer", role_title="ML Engineer",
    )
    assert result.overall_ready is True
    assert len(result.missing_signals) == 0


def test_gap_engine_exact_threshold():
    """A score exactly at threshold means overall_ready = True with no missing signals."""
    engine = GapEngine()
    result = engine.compute(
        te_score=Decimal("5.0"), pc_score=Decimal("4.5"), cq_score=Decimal("4.5"),
        role_te=Decimal("5.0"), role_pc=Decimal("4.5"), role_cq=Decimal("4.5"),
        role_slug="software-engineer", role_title="Software Engineer",
    )
    assert result.overall_ready is True
    assert result.te_gap == Decimal("0.0")
    assert result.pc_gap == Decimal("0.0")
    assert result.cq_gap == Decimal("0.0")
    assert len(result.missing_signals) == 0


def test_gap_engine_all_below():
    engine = GapEngine()
    result = engine.compute(
        te_score=Decimal("2.0"), pc_score=Decimal("2.0"), cq_score=Decimal("2.0"),
        role_te=Decimal("6.5"), role_pc=Decimal("6.5"), role_cq=Decimal("5.0"),
        role_slug="ml-engineer", role_title="ML Engineer",
    )
    assert result.overall_ready is False
    assert len(result.missing_signals) == 3


# ── Language Level / Score tables ────────────────────────────────────────────

from app.pipeline.capability_engine import (
    _LANG_LEVEL,
    _LANG_SCORE,
    apply_hallucination_cap,
    compute_te_objective,
    compute_pc_objective,
    compute_cq_objective,
    _clamp_score,
    EvidenceCitationData,
)


def test_language_level_advanced():
    assert _LANG_LEVEL.get("rust") == "advanced"
    assert _LANG_LEVEL.get("go") == "advanced"
    assert _LANG_LEVEL.get("c++") == "advanced"
    assert _LANG_SCORE["advanced"] == 1.2


def test_language_level_intermediate():
    assert _LANG_LEVEL.get("python") == "intermediate"
    assert _LANG_LEVEL.get("typescript") == "intermediate"
    assert _LANG_LEVEL.get("java") == "intermediate"
    assert _LANG_SCORE["intermediate"] == 0.8


def test_language_level_beginner():
    assert _LANG_LEVEL.get("javascript") == "beginner"
    assert _LANG_LEVEL.get("html") == "beginner"
    assert _LANG_LEVEL.get("r") == "beginner"
    assert _LANG_SCORE["beginner"] == 0.4


def test_language_level_unknown_falls_back_to_beginner():
    # Unknown languages should fall through to beginner (via .get default)
    assert _LANG_LEVEL.get("cobol") is None


# ── Hallucination cap ─────────────────────────────────────────────────────────

def test_hallucination_cap_triggers():
    """AI cannot push score more than 1.5 above objective ceiling."""
    # objective=1.8 → normalised = (1.8/3.6)*9 = 4.5 → max_combined = 6.0
    # combined_raw = 1.8 + 6.5 = 8.3 > 6.0 → cap applies
    # capped_ai = 6.0 - 1.8 = 4.2
    capped_ai, cap_applied = apply_hallucination_cap(objective=1.8, ai_raw=6.5)
    assert cap_applied is True
    assert abs(capped_ai - 4.2) < 1e-9
    # Verify the combined score after capping equals the ceiling
    assert abs((1.8 + capped_ai) - 6.0) < 1e-9
    # And that _clamp_score of the combined value gives Decimal("6.0")
    assert _clamp_score(1.8 + capped_ai) == Decimal("6.0")


def test_hallucination_cap_not_triggered():
    """AI score within bounds should pass through unchanged."""
    # objective=3.6 (max) → normalised = 9.0 → max_combined = 10.5
    # combined_raw = 3.6 + 5.4 = 9.0 < 10.5 → no cap
    capped_ai, cap_applied = apply_hallucination_cap(objective=3.6, ai_raw=5.4)
    assert cap_applied is False
    assert capped_ai == 5.4


def test_hallucination_cap_exact_boundary():
    """Score exactly at the cap boundary should not trigger the cap."""
    # objective=1.8 → max_combined = 6.0; combined = 1.8 + 4.2 = 6.0 (not > 6.0)
    capped_ai, cap_applied = apply_hallucination_cap(objective=1.8, ai_raw=4.2)
    assert cap_applied is False
    assert capped_ai == 4.2


def test_hallucination_cap_zero_objective():
    """Zero objective → ceiling = 0 + 1.5 = 1.5; anything above triggers cap."""
    capped_ai, cap_applied = apply_hallucination_cap(objective=0.0, ai_raw=2.0)
    assert cap_applied is True
    assert abs(capped_ai - 1.5) < 1e-9

    # Exactly at ceiling should not cap
    capped_ai2, cap_applied2 = apply_hallucination_cap(objective=0.0, ai_raw=1.5)
    assert cap_applied2 is False
    assert capped_ai2 == 1.5


def test_hallucination_cap_moderate_objective():
    """Mid-range objective with moderate AI: no cap."""
    # objective=2.7 → normalised = 6.75 → max_combined = 8.25
    # combined = 2.7 + 5.0 = 7.7 < 8.25 → no cap
    capped_ai, cap_applied = apply_hallucination_cap(objective=2.7, ai_raw=5.0)
    assert cap_applied is False
    assert capped_ai == 5.0


# ── _clamp_score ──────────────────────────────────────────────────────────────

def test_clamp_score_below_min():
    assert _clamp_score(0.0) == Decimal("1.0")
    assert _clamp_score(-5.0) == Decimal("1.0")


def test_clamp_score_above_max():
    assert _clamp_score(9.5) == Decimal("9.0")
    assert _clamp_score(15.0) == Decimal("9.0")


def test_clamp_score_within_range():
    assert _clamp_score(5.0) == Decimal("5.0")
    assert _clamp_score(6.0) == Decimal("6.0")
    assert _clamp_score(1.0) == Decimal("1.0")
    assert _clamp_score(9.0) == Decimal("9.0")


def test_clamp_score_rounds_to_one_decimal():
    # round(6.04, 1) = 6.0
    assert _clamp_score(6.04) == Decimal("6.0")


# ── Objective scoring ─────────────────────────────────────────────────────────

from app.pipeline.github_engine import RepositorySignals, UserSignals


def _make_repo(
    name: str = "test/repo",
    languages: dict | None = None,
    has_readme: bool = False,
    readme_word_count: int = 0,
    readme_content: str | None = None,
    has_tests: bool = False,
    has_ci: bool = False,
    has_deployment_config: bool = False,
    topics: list | None = None,
    stars: int = 0,
    commit_count: int = 1,
) -> RepositorySignals:
    return RepositorySignals(
        repo_id=1,
        name=name.split("/")[-1],
        full_name=name,
        url=f"https://github.com/{name}",
        description=None,
        languages=languages or {},
        topics=topics or [],
        commit_count=commit_count,
        stars=stars,
        has_readme=has_readme,
        readme_content=readme_content,
        readme_word_count=readme_word_count,
        has_tests=has_tests,
        has_ci=has_ci,
        has_deployment_config=has_deployment_config,
    )


def _make_signals(
    username: str = "testuser",
    repos: list | None = None,
    total_languages: dict | None = None,
    any_has_tests: bool = False,
    any_has_ci: bool = False,
    any_has_deployment_config: bool = False,
    active_repo_count: int = 0,
    total_stars: int = 0,
) -> UserSignals:
    return UserSignals(
        github_username=username,
        repos=repos or [],
        total_languages=total_languages or {},
        any_has_tests=any_has_tests,
        any_has_ci=any_has_ci,
        any_has_deployment_config=any_has_deployment_config,
        active_repo_count=active_repo_count,
        total_stars=total_stars,
    )


class TestComputeTEObjective:
    def test_empty_signals_returns_zero(self):
        signals = _make_signals()
        score, evidence = compute_te_objective(signals)
        assert score == 0.0
        assert evidence == []

    def test_advanced_language_adds_1_2(self):
        signals = _make_signals(total_languages={"rust": 5000})
        score, evidence = compute_te_objective(signals)
        assert abs(score - 1.2) < 1e-9
        assert any("advanced" in e for e in evidence)

    def test_intermediate_language_adds_0_8(self):
        signals = _make_signals(total_languages={"python": 5000})
        score, evidence = compute_te_objective(signals)
        assert abs(score - 0.8) < 1e-9

    def test_beginner_language_adds_0_4(self):
        signals = _make_signals(total_languages={"javascript": 5000})
        score, evidence = compute_te_objective(signals)
        assert abs(score - 0.4) < 1e-9

    def test_unknown_language_treated_as_beginner(self):
        signals = _make_signals(total_languages={"cobol": 5000})
        score, evidence = compute_te_objective(signals)
        # Falls back to beginner (0.4)
        assert abs(score - 0.4) < 1e-9

    def test_tests_contribute_1_point(self):
        signals = _make_signals(any_has_tests=True)
        score, evidence = compute_te_objective(signals)
        assert abs(score - 1.0) < 1e-9

    def test_ci_contributes_0_6(self):
        signals = _make_signals(any_has_ci=True)
        score, evidence = compute_te_objective(signals)
        assert abs(score - 0.6) < 1e-9

    def test_deployment_config_contributes_0_5(self):
        signals = _make_signals(any_has_deployment_config=True)
        score, evidence = compute_te_objective(signals)
        assert abs(score - 0.5) < 1e-9

    def test_active_repos_scale_linearly(self):
        # 5 repos → min(5/5, 1.0) * 0.8 = 0.8
        signals = _make_signals(active_repo_count=5)
        score, _ = compute_te_objective(signals)
        assert abs(score - 0.8) < 1e-9

    def test_active_repos_capped_at_0_8(self):
        # 10 repos still max at 0.8
        signals = _make_signals(active_repo_count=10)
        score, _ = compute_te_objective(signals)
        assert abs(score - 0.8) < 1e-9

    def test_all_signals_capped_at_3_6(self):
        # rust(1.2) + 5 repos(0.8) + tests(1.0) + ci(0.6) + deploy(0.5) = 4.1 → capped at 3.6
        signals = _make_signals(
            total_languages={"rust": 10000},
            active_repo_count=5,
            any_has_tests=True,
            any_has_ci=True,
            any_has_deployment_config=True,
        )
        score, evidence = compute_te_objective(signals)
        assert score == 3.6
        assert len(evidence) >= 4

    def test_top_language_is_highest_byte_count(self):
        # Python has more bytes than Rust → Python wins → intermediate tier
        signals = _make_signals(total_languages={"rust": 100, "python": 50000})
        score, evidence = compute_te_objective(signals)
        assert abs(score - 0.8) < 1e-9
        assert any("intermediate" in e for e in evidence)


class TestComputePCObjective:
    def test_empty_signals_returns_zero(self):
        signals = _make_signals()
        score, evidence = compute_pc_objective(signals)
        assert score == 0.0

    def test_language_diversity_5_langs_maxes_out(self):
        langs = {"python": 1, "rust": 1, "go": 1, "typescript": 1, "c++": 1}
        signals = _make_signals(total_languages=langs)
        score, _ = compute_pc_objective(signals)
        # lang_div_pts = min(5/5, 1.0) * 0.9 = 0.9
        assert abs(score - 0.9) < 1e-9

    def test_stars_contribute_up_to_0_6(self):
        signals = _make_signals(total_stars=20)
        score, _ = compute_pc_objective(signals)
        # star_pts = min(20/20, 1.0) * 0.6 = 0.6
        assert abs(score - 0.6) < 1e-9

    def test_stars_partial(self):
        signals = _make_signals(total_stars=10)
        score, _ = compute_pc_objective(signals)
        # star_pts = min(10/20, 1.0) * 0.6 = 0.3
        assert abs(score - 0.3) < 1e-9

    def test_multi_lang_repos_contribute(self):
        # 3 repos each with ≥3 languages → min(3/3, 1.0) * 0.6 = 0.6
        repos = [
            _make_repo(languages={"python": 1, "javascript": 1, "typescript": 1}),
            _make_repo(languages={"go": 1, "rust": 1, "c": 1}),
            _make_repo(languages={"java": 1, "kotlin": 1, "sql": 1}),
        ]
        signals = _make_signals(repos=repos)
        score, _ = compute_pc_objective(signals)
        assert abs(score - 0.6) < 1e-9

    def test_deployment_config_adds_0_5(self):
        signals = _make_signals(any_has_deployment_config=True)
        score, _ = compute_pc_objective(signals)
        assert abs(score - 0.5) < 1e-9

    def test_max_score_capped_at_3_6(self):
        # 5 langs(0.9) + 20 stars(0.6) + 8 repos(1.0) + 3 multi-lang repos(0.6) + deploy(0.5) = 3.6
        repos = [
            _make_repo(languages={"python": 1, "rust": 1, "go": 1}),
            _make_repo(languages={"typescript": 1, "c++": 1, "java": 1}),
            _make_repo(languages={"kotlin": 1, "swift": 1, "r": 1}),
        ]
        signals = _make_signals(
            total_languages={"python": 1, "rust": 1, "go": 1, "typescript": 1, "c++": 1},
            total_stars=20,
            active_repo_count=8,
            any_has_deployment_config=True,
            repos=repos,
        )
        score, _ = compute_pc_objective(signals)
        assert score == 3.6


class TestComputeCQObjective:
    def test_empty_signals_returns_zero(self):
        signals = _make_signals()
        score, evidence = compute_cq_objective(signals)
        assert score == 0.0

    def test_readme_coverage_full(self):
        # 2/2 repos have README → ratio = 1.0 → ratio_pts = 0.8
        repos = [
            _make_repo(has_readme=True),
            _make_repo(has_readme=True),
        ]
        signals = _make_signals(repos=repos)
        score, _ = compute_cq_objective(signals)
        assert abs(score - 0.8) < 1e-9

    def test_readme_coverage_half(self):
        # 1/2 repos have README → ratio = 0.5 → ratio_pts = 0.4
        repos = [_make_repo(has_readme=True), _make_repo(has_readme=False)]
        signals = _make_signals(repos=repos)
        score, _ = compute_cq_objective(signals)
        assert abs(score - 0.4) < 1e-9

    def test_readme_word_count_at_300_maxes_word_pts(self):
        # avg_words = 300 → word_pts = min(300/300, 1.0) * 1.4 = 1.4
        repos = [_make_repo(has_readme=True, readme_word_count=300)]
        signals = _make_signals(repos=repos)
        score, _ = compute_cq_objective(signals)
        # ratio_pts(0.8) + word_pts(1.4) = 2.2
        assert abs(score - 2.2) < 1e-9

    def test_readme_word_count_partial(self):
        # avg_words = 150 → word_pts = min(150/300, 1.0) * 1.4 = 0.7
        repos = [_make_repo(has_readme=True, readme_word_count=150)]
        signals = _make_signals(repos=repos)
        score, _ = compute_cq_objective(signals)
        # ratio_pts(0.8) + word_pts(0.7) = 1.5
        assert abs(score - 1.5) < 1e-9

    def test_topics_contribute(self):
        # 2/2 repos have topics → topic_pts = min(2/2, 1.0) * 0.6 = 0.6
        repos = [
            _make_repo(topics=["machine-learning", "python"]),
            _make_repo(topics=["web", "api"]),
        ]
        signals = _make_signals(repos=repos)
        score, _ = compute_cq_objective(signals)
        assert abs(score - 0.6) < 1e-9

    def test_ci_adds_0_4(self):
        signals = _make_signals(any_has_ci=True)
        score, _ = compute_cq_objective(signals)
        assert abs(score - 0.4) < 1e-9

    def test_score_capped_at_3_6(self):
        # Full README coverage (0.8) + 600 word avg (1.4) + full topics (0.6) + ci (0.4) = 3.2
        # To hit cap we need word_pts already maxed at 1.4, so max is 0.8+1.4+0.6+0.4 = 3.2
        repos = [
            _make_repo(has_readme=True, readme_word_count=600, topics=["a", "b"]),
            _make_repo(has_readme=True, readme_word_count=600, topics=["c"]),
        ]
        signals = _make_signals(repos=repos, any_has_ci=True)
        score, _ = compute_cq_objective(signals)
        assert score <= 3.6
        assert abs(score - 3.2) < 1e-9


# ── EvidenceCitationData dataclass ────────────────────────────────────────────

def test_evidence_citation_data_construction():
    citation = EvidenceCitationData(
        dimension="technical_execution",
        citation_text="Test suite detected in testuser/my-api (tests/ directory, 47 test files)",
        artifact_type="github_repo",
        artifact_ref="testuser/my-api",
        score_contribution=1.0,
    )
    assert citation.dimension == "technical_execution"
    assert citation.artifact_type == "github_repo"
    assert citation.artifact_ref == "testuser/my-api"
    assert citation.score_contribution == 1.0
    assert "testuser/my-api" in citation.citation_text


def test_evidence_citation_data_all_artifact_types():
    """Validate all artifact_type values used in the pipeline."""
    valid_types = {
        "github_repo", "readme", "commit_history",
        "ci_workflow", "deployment_config", "language_signal",
    }
    for artifact_type in valid_types:
        citation = EvidenceCitationData(
            dimension="communication_quality",
            citation_text="sample",
            artifact_type=artifact_type,
            artifact_ref="owner/repo",
            score_contribution=0.5,
        )
        assert citation.artifact_type == artifact_type

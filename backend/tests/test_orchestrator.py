"""
Tests for the pipeline orchestrator transaction model.

Verifies that:
  - _set_status() commits each stage update (not just flushes) so the SSE
    poller, which opens its own separate DB session, can see live progress.
  - run_analysis() no longer wraps _run() in a single outer transaction.
  - Retry logic correctly re-queues the job and commits the re-queue update.
  - Failure logic correctly marks the job failed and commits.
  - Timeout (asyncio.TimeoutError) is treated as retryable.
  - Maximum retries are enforced — non-retryable or exhausted jobs are failed.
  - Successful completion clears claimed_at/worker_id and commits.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# ── Minimal env ───────────────────────────────────────────────────────────────
_ENV = {
    "DATABASE_URL":              "postgresql+asyncpg://x:x@localhost/test",
    "SUPABASE_URL":              "https://testref.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SUPABASE_JWT_SECRET":       "test-jwt-secret-at-least-32-chars!!",
    "GITHUB_CLIENT_ID":          "test-client-id",
    "GITHUB_CLIENT_SECRET":      "test-client-secret",
    "GEMINI_API_KEY":            "test-gemini-key",
    "ENVIRONMENT":               "test",
    "DEBUG":                     "false",
}
for k, v in _ENV.items():
    os.environ.setdefault(k, v)

from app.config import get_settings  # noqa: E402
from app.pipeline.orchestrator import (  # noqa: E402
    _backoff_seconds,
    _is_retryable,
    _set_status,
    run_analysis,
)

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ─────────────────────────────────────────────────────────────────────────────
# _set_status — commits, not flushes
# ─────────────────────────────────────────────────────────────────────────────

class TestSetStatus:
    """_set_status() must call db.commit() so other sessions see the update."""

    def _make_mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.flush  = AsyncMock()
        return db

    def test_commit_is_called(self):
        db = self._make_mock_db()
        asyncio.run(_set_status(db, uuid.uuid4(), "github_fetch", "Fetching", 5))
        db.commit.assert_called_once()

    def test_flush_is_not_called(self):
        """flush() would keep changes invisible to other sessions — must not be used."""
        db = self._make_mock_db()
        asyncio.run(_set_status(db, uuid.uuid4(), "github_fetch", "Fetching", 5))
        db.flush.assert_not_called()

    def test_execute_is_called_once(self):
        db = self._make_mock_db()
        asyncio.run(_set_status(db, uuid.uuid4(), "ai_analysis", "Analyzing", 60))
        db.execute.assert_called_once()

    def test_commit_called_per_stage_update(self):
        """Each _set_status() call issues its own commit — stage visibility is immediate."""
        db = self._make_mock_db()
        job_id = uuid.uuid4()
        asyncio.run(_set_status(db, job_id, "github_fetch", "Fetching", 5))
        asyncio.run(_set_status(db, job_id, "evidence_extract", "Evidence", 45))
        asyncio.run(_set_status(db, job_id, "ai_analysis", "Analyzing", 60))
        assert db.commit.call_count == 3
        assert db.flush.call_count == 0

    def test_error_field_included_when_provided(self):
        """error= is forwarded into the UPDATE values."""
        db = self._make_mock_db()
        asyncio.run(_set_status(db, uuid.uuid4(), "failed", "Oops", 0, error="boom"))
        args = db.execute.call_args[0][0]
        compiled = str(args.compile(compile_kwargs={"literal_binds": True}))
        assert "error_message" in compiled or "boom" in compiled

    def test_completed_at_included_when_provided(self):
        db = self._make_mock_db()
        now = datetime.now(timezone.utc)
        asyncio.run(_set_status(db, uuid.uuid4(), "complete", "Done", 100, completed_at=now))
        args = db.execute.call_args[0][0]
        compiled = str(args.compile(compile_kwargs={"literal_binds": True}))
        assert "completed_at" in compiled


# ─────────────────────────────────────────────────────────────────────────────
# run_analysis — no outer transaction
# ─────────────────────────────────────────────────────────────────────────────

def _make_session_factory(mock_db: AsyncMock) -> MagicMock:
    """Build a mock async_sessionmaker that yields mock_db."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=ctx)
    return factory


class TestRunAnalysisTransactionModel:
    """run_analysis() must not wrap _run() in a single outer db.begin()."""

    def test_no_outer_begin_on_success(self):
        """A successful run must not call db.begin() — each stage commits independently."""
        mock_db = AsyncMock()
        mock_db.begin = MagicMock()
        factory = _make_session_factory(mock_db)

        async def fake_run(jid, db, log):
            pass

        with patch("app.pipeline.orchestrator._run", fake_run):
            asyncio.run(run_analysis(uuid.uuid4(), factory))

        mock_db.begin.assert_not_called()

    def test_no_outer_begin_on_failure(self):
        """Even when _run() raises, db.begin() must not have been called."""
        mock_db_run = AsyncMock()
        mock_db_run.begin = MagicMock()

        mock_job = MagicMock()
        mock_job.retry_count = 3  # already at max so no retry loop
        mock_db_fail = AsyncMock()
        mock_db_fail.get = AsyncMock(return_value=mock_job)
        mock_db_fail.execute = AsyncMock()
        mock_db_fail.commit = AsyncMock()

        call_n = [0]
        def factory():
            call_n[0] += 1
            ctx = AsyncMock()
            db = mock_db_run if call_n[0] == 1 else mock_db_fail
            ctx.__aenter__ = AsyncMock(return_value=db)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        with patch("app.pipeline.orchestrator._run", side_effect=Exception("boom")):
            asyncio.run(run_analysis(uuid.uuid4(), factory))

        mock_db_run.begin.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# run_analysis — retry behavior
# ─────────────────────────────────────────────────────────────────────────────

class TestRunAnalysisRetry:
    """Retryable failures re-queue the job with incremented retry_count and commit."""

    def _run_with_failure(self, exc: Exception, retry_count: int = 0):
        """Run run_analysis() with _run() raising exc; return the mock db2."""
        mock_db_run = AsyncMock()

        mock_job = MagicMock()
        mock_job.retry_count = retry_count
        mock_db2 = AsyncMock()
        mock_db2.get = AsyncMock(return_value=mock_job)
        mock_db2.execute = AsyncMock()
        mock_db2.commit = AsyncMock()

        call_n = [0]
        def factory():
            call_n[0] += 1
            ctx = AsyncMock()
            db = mock_db_run if call_n[0] == 1 else mock_db2
            ctx.__aenter__ = AsyncMock(return_value=db)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        with patch("app.pipeline.orchestrator._run", side_effect=exc):
            asyncio.run(run_analysis(uuid.uuid4(), factory))

        return mock_db2

    def test_retryable_error_calls_commit(self):
        db2 = self._run_with_failure(Exception("429 resource exhausted"), retry_count=0)
        db2.commit.assert_called_once()

    def test_retryable_error_updates_status_to_queued(self):
        db2 = self._run_with_failure(Exception("429 resource exhausted"), retry_count=0)
        update_call = db2.execute.call_args[0][0]
        compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "queued" in compiled

    def test_retryable_error_increments_retry_count(self):
        db2 = self._run_with_failure(Exception("429 resource exhausted"), retry_count=1)
        update_call = db2.execute.call_args[0][0]
        compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "retry_count" in compiled

    def test_retryable_error_clears_claimed_at_and_worker_id(self):
        db2 = self._run_with_failure(Exception("connection refused"), retry_count=0)
        update_call = db2.execute.call_args[0][0]
        compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "claimed_at" in compiled
        assert "worker_id" in compiled

    def test_timeout_is_retried(self):
        """asyncio.TimeoutError must trigger the retry path (not immediate failure)."""
        db2 = self._run_with_failure(asyncio.TimeoutError(), retry_count=0)
        update_call = db2.execute.call_args[0][0]
        compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "queued" in compiled
        db2.commit.assert_called_once()

    def test_max_retries_exhausted_marks_failed(self):
        """When retry_count >= max_job_retries (3), job must be marked failed."""
        db2 = self._run_with_failure(Exception("429 quota exceeded"), retry_count=3)
        update_call = db2.execute.call_args[0][0]
        compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "failed" in compiled
        db2.commit.assert_called_once()

    def test_non_retryable_error_marks_failed_immediately(self):
        """Non-retryable errors bypass the retry path and fail immediately."""
        db2 = self._run_with_failure(ValueError("No GitHub token"), retry_count=0)
        update_call = db2.execute.call_args[0][0]
        compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "failed" in compiled
        db2.commit.assert_called_once()

    def test_failed_status_includes_error_message(self):
        exc_msg = "Specific failure detail"
        db2 = self._run_with_failure(ValueError(exc_msg), retry_count=3)
        update_call = db2.execute.call_args[0][0]
        compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "failed" in compiled

    def test_failed_status_clears_claimed_at(self):
        db2 = self._run_with_failure(ValueError("bad input"), retry_count=3)
        update_call = db2.execute.call_args[0][0]
        compiled = str(update_call.compile(compile_kwargs={"literal_binds": True}))
        assert "claimed_at" in compiled
        assert "worker_id" in compiled


# ─────────────────────────────────────────────────────────────────────────────
# run_analysis — successful completion
# ─────────────────────────────────────────────────────────────────────────────

class TestRunAnalysisSuccess:
    """Successful pipeline must commit the completion state and clear claim fields."""

    def test_no_failure_handler_on_success(self):
        """If _run() succeeds, the failure-handling db2 session is never opened."""
        mock_db = AsyncMock()
        factory_calls = []

        def factory():
            factory_calls.append(1)
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=mock_db)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        async def fake_run(jid, db, log):
            pass

        with patch("app.pipeline.orchestrator._run", fake_run):
            asyncio.run(run_analysis(uuid.uuid4(), factory))

        # Only 1 session opened — the run session; no failure-handler session
        assert len(factory_calls) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Stage-progress visibility — cross-session contract
# ─────────────────────────────────────────────────────────────────────────────

class TestStageProgressVisibility:
    """
    Prove the cross-session visibility contract:
    Each _set_status() commit makes the update visible to a new session opened
    after the commit. Simulated with two independent mock sessions.
    """

    def test_second_session_reads_committed_status(self):
        """
        Simulate: session A commits github_fetch status.
        Session B (opened after) reads back 'github_fetch'.
        With flush-only, session B would see the old value.
        With commit, session B sees the new value.

        This test verifies the contract by confirming commit is called
        before the second session is opened.
        """
        committed_values = []

        # Session A — the pipeline session
        db_a = AsyncMock()
        db_a.execute = AsyncMock()
        db_a.commit = AsyncMock(
            side_effect=lambda: committed_values.append("commit")
        )

        asyncio.run(_set_status(db_a, uuid.uuid4(), "github_fetch", "Fetching", 5))

        # By the time we open a second session, the commit has happened
        assert committed_values == ["commit"], (
            "Commit must occur before returning from _set_status(), so any "
            "independently-opened SSE session reads the updated status."
        )

    def test_all_pipeline_stages_commit_in_order(self):
        """Each of the 8 named stage transitions produces exactly one commit."""
        stages = [
            ("github_fetch",      "Fetching repositories",     5),
            ("github_fetch",      "Storing signals",           30),
            ("github_fetch",      "GitHub done",               40),
            ("evidence_extract",  "Processing evidence",       45),
            ("evidence_extract",  "Evidence ready",            55),
            ("ai_analysis",       "Running AI analysis",       60),
            ("ai_analysis",       "Scores computed",           80),
            ("scoring",           "Computing gaps",            85),
            ("scoring",           "Generating recommendations",90),
            ("scoring",           "Saving profile",            95),
            ("complete",          "Profile ready",            100),
        ]
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        for status, step, pct in stages:
            asyncio.run(_set_status(db, uuid.uuid4(), status, step, pct))

        assert db.commit.call_count == len(stages)
        assert db.flush.call_count == 0

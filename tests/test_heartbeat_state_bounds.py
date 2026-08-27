"""Heartbeat tracking state must not grow without bound.

``_heartbeat_timestamps`` and ``_step_metrics`` record, per run and per step,
when a step last reported in and what it reported. ``_cleanup_heartbeats`` was
written to release that state, but nothing ever called it, so both dictionaries
gained an entry per run and per step for the lifetime of the process. A server
executing pipelines continuously leaked memory in proportion to how much work
it had done.

Cleanup on run termination is not enough on its own: a worker that crashes
never reports a terminal status, so entries also age out, with a hard ceiling
as a backstop.
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from flowyml.ui.backend.routers import runs as runs_router  # noqa: E402


@pytest.fixture(autouse=True)
def clean_heartbeat_state(monkeypatch):
    """Each test starts from empty tracking with the shipped thresholds."""
    monkeypatch.setattr(runs_router, "_heartbeat_timestamps", {})
    monkeypatch.setattr(runs_router, "_step_metrics", {})
    yield


class TestExplicitCleanup:
    def test_cleanup_releases_both_dictionaries(self):
        runs_router._record_heartbeat("run-1", "train")
        runs_router._record_step_metrics("run-1", "train", {"loss": 0.1})

        runs_router._cleanup_heartbeats("run-1")

        assert "run-1" not in runs_router._heartbeat_timestamps
        assert "run-1" not in runs_router._step_metrics

    def test_cleanup_of_an_unknown_run_is_harmless(self):
        runs_router._cleanup_heartbeats("never-existed")

    def test_cleanup_leaves_other_runs_alone(self):
        runs_router._record_heartbeat("run-1", "train")
        runs_router._record_heartbeat("run-2", "train")

        runs_router._cleanup_heartbeats("run-1")

        assert "run-2" in runs_router._heartbeat_timestamps


class TestStaleEntriesAgeOut:
    def test_a_run_that_stops_reporting_is_pruned(self, monkeypatch):
        """A crashed worker never sends a terminal status."""
        monkeypatch.setattr(runs_router, "HEARTBEAT_RETENTION_SECONDS", 0.05)

        runs_router._record_heartbeat("abandoned", "train")
        runs_router._record_step_metrics("abandoned", "train", {"loss": 1.0})
        assert "abandoned" in runs_router._heartbeat_timestamps

        time.sleep(0.1)
        # Pruning happens opportunistically, on the next recorded heartbeat.
        runs_router._record_heartbeat("active", "train")

        assert "abandoned" not in runs_router._heartbeat_timestamps
        assert "abandoned" not in runs_router._step_metrics

    def test_an_actively_reporting_run_is_kept(self, monkeypatch):
        monkeypatch.setattr(runs_router, "HEARTBEAT_RETENTION_SECONDS", 60)

        runs_router._record_heartbeat("busy", "train")
        runs_router._record_heartbeat("other", "train")

        assert "busy" in runs_router._heartbeat_timestamps


class TestCeilingBackstop:
    def test_tracked_runs_never_exceed_the_ceiling(self, monkeypatch):
        monkeypatch.setattr(runs_router, "MAX_TRACKED_RUNS", 10)
        monkeypatch.setattr(runs_router, "HEARTBEAT_RETENTION_SECONDS", 3600)

        for index in range(100):
            runs_router._record_heartbeat(f"run-{index}", "train")

        assert len(runs_router._heartbeat_timestamps) <= 10

    def test_the_most_recent_runs_survive(self, monkeypatch):
        monkeypatch.setattr(runs_router, "MAX_TRACKED_RUNS", 5)
        monkeypatch.setattr(runs_router, "HEARTBEAT_RETENTION_SECONDS", 3600)

        for index in range(20):
            runs_router._record_heartbeat(f"run-{index}", "train")

        assert "run-19" in runs_router._heartbeat_timestamps


class TestDeadStepDetectionStillWorks:
    """Bounding the state must not break the feature it supports."""

    def test_a_fresh_heartbeat_is_not_dead(self):
        runs_router._record_heartbeat("run-1", "train")

        assert runs_router._get_dead_steps("run-1") == []

    def test_a_stale_step_is_reported_dead(self, monkeypatch):
        monkeypatch.setattr(runs_router, "HEARTBEAT_INTERVAL", 0.01)
        monkeypatch.setattr(runs_router, "DEAD_THRESHOLD", 1)

        runs_router._record_heartbeat("run-1", "train")
        time.sleep(0.05)

        assert runs_router._get_dead_steps("run-1") == ["train"]

    def test_an_unknown_run_has_no_dead_steps(self):
        assert runs_router._get_dead_steps("never-existed") == []

    def test_metrics_are_recorded_per_step(self):
        runs_router._record_step_metrics("run-1", "train", {"loss": 0.5})
        runs_router._record_step_metrics("run-1", "eval", {"acc": 0.9})

        assert runs_router._step_metrics["run-1"]["train"] == {"loss": 0.5}
        assert runs_router._step_metrics["run-1"]["eval"] == {"acc": 0.9}

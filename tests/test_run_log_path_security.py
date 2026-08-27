"""Path-traversal regression tests for the step-log endpoints.

``POST /api/runs/{run_id}/steps/{step_name}/logs`` appends caller-supplied text
to a file whose path is built from the two URL parameters, and the matching GET
reads it back.

Starlette matches a path parameter against a single segment, so an encoded
``%2F`` is rejected by routing - but ``..`` is a perfectly ordinary segment.
``curl --path-as-is -X POST /api/runs/../steps/x/logs`` was accepted and wrote
``.flowyml/logs/x.log``, outside the runs directory, with attacker-controlled
content. Anything that reaches the filesystem from a URL parameter has to be
confined explicitly.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from flowyml.ui.backend.artifact_paths import resolve_run_log_path  # noqa: E402


class TestResolveRunLogPath:
    def test_normal_run_and_step_land_under_the_root(self, tmp_path):
        path = resolve_run_log_path(tmp_path, "run-123", "train")

        assert path == (tmp_path / "run-123" / "logs" / "train.log").resolve()

    def test_directory_form_omits_the_step(self, tmp_path):
        path = resolve_run_log_path(tmp_path, "run-123")

        assert path == (tmp_path / "run-123" / "logs").resolve()

    @pytest.mark.parametrize("run_id", ["..", "../..", "../../../etc", "/etc", "."])
    def test_traversal_in_the_run_id_cannot_escape(self, tmp_path, run_id):
        path = resolve_run_log_path(tmp_path, run_id, "step")

        assert tmp_path.resolve() in path.parents, f"{run_id!r} escaped to {path}"

    @pytest.mark.parametrize("step_name", ["..", "../../evil", "/etc/passwd", "."])
    def test_traversal_in_the_step_name_cannot_escape(self, tmp_path, step_name):
        path = resolve_run_log_path(tmp_path, "run-123", step_name)

        assert tmp_path.resolve() in path.parents, f"{step_name!r} escaped to {path}"

    def test_the_log_suffix_is_always_applied(self, tmp_path):
        assert resolve_run_log_path(tmp_path, "r", "step").name == "step.log"

    def test_empty_components_get_a_readable_placeholder(self, tmp_path):
        path = resolve_run_log_path(tmp_path, "", "")

        assert tmp_path.resolve() in path.parents
        assert "unknown-run" in str(path)
        assert path.name == "unknown-step.log"

    def test_distinct_runs_stay_distinct(self, tmp_path):
        """Sanitisation must not collapse unrelated runs into one file."""
        first = resolve_run_log_path(tmp_path, "run-a", "train")
        second = resolve_run_log_path(tmp_path, "run-b", "train")

        assert first != second


@pytest.fixture
def client(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    from flowyml.utils import config as config_module

    real_get_config = config_module.get_config

    def _scoped_config(*args, **kwargs):
        cfg = real_get_config(*args, **kwargs)
        cfg.runs_dir = runs_dir
        return cfg

    monkeypatch.setattr(config_module, "get_config", _scoped_config)

    from flowyml.ui.backend.main import app

    with TestClient(app) as test_client:
        test_client.runs_dir = runs_dir
        test_client.outside = tmp_path
        yield test_client


class TestStepLogEndpoints:
    def test_logs_round_trip(self, client):
        """The hardening must not break ordinary log streaming."""
        posted = client.post(
            "/api/runs/run-1/steps/train/logs",
            json={"content": "epoch 1 complete", "level": "INFO"},
        )
        assert posted.status_code == 200

        body = client.get("/api/runs/run-1/steps/train/logs").json()
        assert "epoch 1 complete" in body["logs"]

        assert (client.runs_dir / "run-1" / "logs" / "train.log").is_file()

    def test_a_traversal_segment_writes_nothing_outside_the_runs_directory(self, client):
        """The original exploit: curl --path-as-is with a bare '..' segment."""
        client.post(
            "/api/runs/../steps/evil/logs",
            json={"content": "INJECTED", "level": "INFO"},
        )

        stray = list(client.outside.glob("*.log")) + list(client.outside.glob("logs/*.log"))
        assert not stray, f"files written outside the runs directory: {stray}"

    def test_every_written_log_stays_under_the_runs_directory(self, client):
        for run_id, step in [("..", "x"), ("run", ".."), ("..", ".."), ("", "")]:
            client.post(
                f"/api/runs/{run_id or 'blank'}/steps/{step or 'blank'}/logs",
                json={"content": "probe", "level": "INFO"},
            )

        written = list(client.runs_dir.rglob("*.log"))
        runs_root = client.runs_dir.resolve()
        for path in written:
            assert runs_root in path.resolve().parents

    def test_reading_an_unknown_run_is_not_an_error(self, client):
        """A missing log file is an empty result, not a failure."""
        body = client.get("/api/runs/never-existed/steps/nope/logs").json()

        assert body["logs"] == ""

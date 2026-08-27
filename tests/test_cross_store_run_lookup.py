"""Looking a run up by id must consult every store, not just the global one.

A run can live in the globally configured metadata store or in a project's own
store. ``runs.py`` searched both; ``ai_context.py`` searched only the global
one, because each router kept its own copy of the same loop and they drifted.
The result was visible in the UI: opening a run detail page rendered fine while
the AI-context request behind it answered 404 for the very run on screen.

The loop now lives in ``dependencies`` and every caller shares it.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from flowyml.storage.sql import SQLMetadataStore  # noqa: E402
from flowyml.ui.backend import dependencies  # noqa: E402


RUN_RECORD = {
    "pipeline_name": "demo_pipeline",
    "status": "completed",
    "start_time": "2026-03-14T09:00:00",
    "end_time": "2026-03-14T09:01:00",
    "steps": {},
}


@pytest.fixture
def global_store(monkeypatch, tmp_path):
    store = SQLMetadataStore(db_path=str(tmp_path / "global.db"))
    monkeypatch.setattr(dependencies, "_store", store)
    return store


@pytest.fixture
def project_store(monkeypatch, tmp_path, global_store):
    """A second store, exposed as if it belonged to a project."""
    store = SQLMetadataStore(db_path=str(tmp_path / "project.db"))

    def _stores():
        return [(None, global_store), ("demo-project", store)]

    monkeypatch.setattr(dependencies, "iter_metadata_stores", _stores)
    return store


@pytest.fixture
def client(monkeypatch, global_store):
    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)

    from flowyml.ui.backend.main import app

    with TestClient(app) as test_client:
        yield test_client


class TestFindRunAcrossStores:
    def test_finds_a_run_in_the_global_store(self, global_store):
        global_store.save_run("run-global", {"run_id": "run-global", **RUN_RECORD})

        run, store = dependencies.find_run_across_stores("run-global")

        assert run is not None
        assert store is global_store

    def test_finds_a_run_in_a_project_store(self, project_store):
        project_store.save_run("run-project", {"run_id": "run-project", **RUN_RECORD})

        run, store = dependencies.find_run_across_stores("run-project")

        assert run is not None, "a run in a project store must still be found"
        assert store is project_store

    def test_annotates_the_run_with_its_project(self, project_store):
        project_store.save_run("run-project", {"run_id": "run-project", **RUN_RECORD})

        run, _ = dependencies.find_run_across_stores("run-project")

        assert run["project"] == "demo-project"

    def test_does_not_overwrite_an_existing_project(self, project_store):
        project_store.save_run(
            "run-project",
            {"run_id": "run-project", "project": "explicit", **RUN_RECORD},
        )

        run, _ = dependencies.find_run_across_stores("run-project")

        assert run["project"] == "explicit"

    def test_unknown_run_returns_nothing(self, global_store):
        assert dependencies.find_run_across_stores("nope") == (None, None)


class TestEndpointsAgreeOnWhatExists:
    """The bug in one sentence: two endpoints disagreed about the same run."""

    def test_run_detail_and_ai_context_agree_for_a_global_run(self, client, global_store):
        global_store.save_run("run-global", {"run_id": "run-global", **RUN_RECORD})

        assert client.get("/api/runs/run-global").status_code == 200
        assert client.get("/api/ai/context/run/run-global").status_code == 200

    def test_run_detail_and_ai_context_agree_for_a_project_run(self, client, project_store):
        project_store.save_run("run-project", {"run_id": "run-project", **RUN_RECORD})

        detail = client.get("/api/runs/run-project")
        context = client.get("/api/ai/context/run/run-project")

        assert detail.status_code == 200
        assert context.status_code == 200, (
            "the AI context endpoint 404'd for a run the detail page renders"
        )

    def test_both_agree_a_missing_run_is_missing(self, client, global_store):
        assert client.get("/api/runs/never-existed").status_code == 404
        assert client.get("/api/ai/context/run/never-existed").status_code == 404

    def test_ai_context_returns_the_run_summary(self, client, project_store):
        project_store.save_run(
            "run-project",
            {
                "run_id": "run-project",
                **RUN_RECORD,
                "steps": {"train": {"success": True, "duration": 1.5}},
            },
        )

        body = client.get("/api/ai/context/run/run-project").json()

        assert body["page_type"] == "run"
        assert body["resource_id"] == "run-project"
        assert [step["name"] for step in body["summary"]["steps"]] == ["train"]

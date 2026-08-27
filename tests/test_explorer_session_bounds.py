"""The model explorer's in-memory session state must be bounded.

Exploration sessions are scratch state held in the server process rather than
the database, which is fine - but nothing ever expired them. A session was
created for every model a user opened and removed only by an explicit delete,
and each prediction and parameter sweep appended to a list that only grew. A
server left running accumulated all of it until it ran out of memory.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from flowyml.ui.backend.routers import model_explorer  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)

    # Each test starts from an empty session table.
    monkeypatch.setattr(model_explorer, "_sessions", type(model_explorer._sessions)())

    from flowyml.ui.backend.main import app

    with TestClient(app) as test_client:
        yield test_client


def _create_session(client, model_id: str) -> str:
    response = client.post(
        "/api/explorer/sessions",
        params={"model_id": model_id, "model_name": "Model"},
    )
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


class TestSessionCountIsBounded:
    def test_sessions_stop_accumulating_at_the_cap(self, client):
        for index in range(model_explorer.MAX_SESSIONS + 50):
            _create_session(client, f"model-{index}")

        assert len(model_explorer._sessions) == model_explorer.MAX_SESSIONS

    def test_the_most_recent_sessions_survive_eviction(self, client):
        newest = None
        for index in range(model_explorer.MAX_SESSIONS + 10):
            newest = _create_session(client, f"model-{index}")

        assert newest in model_explorer._sessions
        assert client.get(f"/api/explorer/sessions/{newest}").status_code == 200

    def test_eviction_drops_the_oldest_first(self, client):
        oldest = _create_session(client, "first")
        for index in range(model_explorer.MAX_SESSIONS):
            _create_session(client, f"model-{index}")

        assert oldest not in model_explorer._sessions

    def test_activity_protects_a_session_from_eviction(self, client):
        """Least-recently-*used*, so an active session is not evicted by age."""
        active = _create_session(client, "active")

        for index in range(model_explorer.MAX_SESSIONS - 1):
            _create_session(client, f"model-{index}")
            model_explorer._record_session_entry(active, "predictions", {"n": index})

        assert active in model_explorer._sessions


class TestSessionHistoryIsBounded:
    def test_prediction_history_stops_growing_at_the_cap(self, client):
        session_id = _create_session(client, "model-1")

        for index in range(model_explorer.MAX_HISTORY_PER_SESSION + 100):
            model_explorer._record_session_entry(session_id, "predictions", {"n": index})

        history = model_explorer._sessions[session_id]["predictions"]
        assert len(history) == model_explorer.MAX_HISTORY_PER_SESSION

    def test_the_newest_entries_are_the_ones_kept(self, client):
        session_id = _create_session(client, "model-1")
        total = model_explorer.MAX_HISTORY_PER_SESSION + 10

        for index in range(total):
            model_explorer._record_session_entry(session_id, "predictions", {"n": index})

        history = model_explorer._sessions[session_id]["predictions"]
        assert history[-1] == {"n": total - 1}
        assert history[0] == {"n": total - model_explorer.MAX_HISTORY_PER_SESSION}

    def test_sweep_history_is_bounded_too(self, client):
        session_id = _create_session(client, "model-1")

        for index in range(model_explorer.MAX_HISTORY_PER_SESSION + 25):
            model_explorer._record_session_entry(session_id, "sweeps", {"n": index})

        assert len(model_explorer._sessions[session_id]["sweeps"]) == model_explorer.MAX_HISTORY_PER_SESSION

    def test_recording_against_an_unknown_session_is_a_no_op(self, client):
        """An evicted session must not resurrect itself on the next prediction."""
        model_explorer._record_session_entry("never-existed", "predictions", {"n": 1})

        assert "never-existed" not in model_explorer._sessions


class TestSessionsStillWork:
    def test_a_session_can_be_created_read_and_deleted(self, client):
        session_id = _create_session(client, "model-1")

        assert client.get(f"/api/explorer/sessions/{session_id}").status_code == 200
        assert client.delete(f"/api/explorer/sessions/{session_id}").status_code == 200
        assert client.get(f"/api/explorer/sessions/{session_id}").status_code == 404

    def test_listing_reflects_created_sessions(self, client):
        _create_session(client, "model-1")
        _create_session(client, "model-2")

        assert len(client.get("/api/explorer/sessions").json()) == 2

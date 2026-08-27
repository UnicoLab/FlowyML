"""Every API router must read and write the *configured* metadata store.

``SQLiteMetadataStore`` is an alias for ``SQLMetadataStore``, and calling it
with no arguments opens the default local SQLite file - ignoring
``FLOWYML_DATABASE_URL`` entirely. Three routers did exactly that.

In the deployment the project documents, docker-compose sets
``FLOWYML_DATABASE_URL`` to Postgres. Pipelines wrote their experiments,
metrics and runs there, while the experiments listing, the leaderboard and the
model-metrics endpoints read a SQLite file inside the container: permanently
empty, and discarded whenever the container restarted.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

@pytest.fixture
def configured_store(monkeypatch, tmp_path):
    """Point FLOWYML_DATABASE_URL at a non-default database and reset the cache."""
    db_path = tmp_path / "configured.db"
    monkeypatch.setenv("FLOWYML_DATABASE_URL", f"sqlite:///{db_path}")

    from flowyml.ui.backend import dependencies

    monkeypatch.setattr(dependencies, "_store", None)

    store = dependencies.get_store()
    assert str(db_path) in str(store.engine.url)
    return store


class TestRoutersUseTheConfiguredStore:
    def test_experiments_router_uses_it(self, configured_store):
        from flowyml.ui.backend.routers.experiments import _iter_metadata_stores

        global_store = _iter_metadata_stores()[0][1]
        assert global_store is configured_store

    def test_metrics_router_uses_it(self, configured_store):
        from flowyml.ui.backend.routers.metrics import get_global_store

        assert get_global_store() is configured_store

    def test_experiments_written_by_a_pipeline_are_visible_to_the_api(self, configured_store):
        """The bug in one sentence: the API read a different database."""
        from fastapi.testclient import TestClient

        from flowyml.ui.backend.main import app

        configured_store.save_experiment(
            experiment_id="exp-from-pipeline",
            name="training-sweep",
            description="",
            tags={},
        )

        with TestClient(app) as client:
            listed = client.get("/api/experiments/").json()["experiments"]

        assert any(entry.get("name") == "training-sweep" for entry in listed), (
            "an experiment written to the configured store was invisible to the API"
        )


class TestNoRouterBypassesTheStoreFactory:
    def test_no_router_constructs_a_metadata_store_directly(self):
        """Constructing one directly silently ignores FLOWYML_DATABASE_URL."""
        import ast
        from pathlib import Path

        backend_dir = Path(__file__).resolve().parent.parent / "flowyml" / "ui" / "backend"
        forbidden = {"SQLiteMetadataStore", "SQLMetadataStore"}

        offenders = []
        for path in sorted(backend_dir.rglob("*.py")):
            # dependencies.py is the factory itself.
            if path.name == "dependencies.py":
                continue
            # Parsing rather than grepping, so prose in a docstring that names
            # the forbidden call cannot be mistaken for the call itself.
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name in forbidden:
                    offenders.append(f"{path.name}:{node.lineno}: {name}(...)")

        assert not offenders, (
            "Use get_store() so FLOWYML_DATABASE_URL is honoured; these construct a "
            f"store directly:\n" + "\n".join(f"  {o}" for o in offenders)
        )


class TestStoreFactory:
    def test_database_url_takes_precedence(self, monkeypatch, tmp_path):
        db_path = tmp_path / "explicit.db"
        monkeypatch.setenv("FLOWYML_DATABASE_URL", f"sqlite:///{db_path}")

        from flowyml.ui.backend import dependencies

        monkeypatch.setattr(dependencies, "_store", None)
        assert str(db_path) in str(dependencies.get_store().engine.url)

    def test_store_is_cached(self, monkeypatch, tmp_path):
        """A new engine per request would exhaust connections under load."""
        monkeypatch.setenv("FLOWYML_DATABASE_URL", f"sqlite:///{tmp_path / 'x.db'}")

        from flowyml.ui.backend import dependencies

        monkeypatch.setattr(dependencies, "_store", None)
        assert dependencies.get_store() is dependencies.get_store()

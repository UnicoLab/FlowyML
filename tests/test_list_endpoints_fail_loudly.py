"""List endpoints must report a storage failure instead of hiding it.

Several handlers used to catch every exception and answer ``200`` with an empty
collection plus an ``error`` key nothing read::

    except Exception as e:
        return {"runs": [], "error": str(e)}

The UI does ``data.runs || []``, so a database outage rendered the same "no
runs yet" empty state as a brand-new installation. Nothing alerted, no status
code indicated a problem, and the failure stayed invisible until a user asked
why their data had disappeared.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)

    from flowyml.ui.backend.main import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _break_store(monkeypatch, module_name: str) -> None:
    """Make the metadata store raise, as an unreachable database would.

    Patched at ``dependencies``, the single place every router now obtains a
    store from, plus the router's own re-exported name for the handlers that
    still call ``get_store()`` directly.
    """
    from flowyml.ui.backend import dependencies
    from flowyml.ui.backend.routers import (  # noqa: F401
        assets,
        experiments,
        pipelines,
        runs,
    )

    def unavailable(*args, **kwargs):
        raise RuntimeError("could not connect to server: Connection refused")

    monkeypatch.setattr(dependencies, "get_store", unavailable)
    monkeypatch.setattr(dependencies, "iter_metadata_stores", unavailable)

    module = {
        "assets": assets,
        "experiments": experiments,
        "pipelines": pipelines,
        "runs": runs,
    }[module_name]
    if hasattr(module, "get_store"):
        monkeypatch.setattr(module, "get_store", unavailable)


class TestStorageFailuresAreReported:
    @pytest.mark.parametrize(
        ("module_name", "url"),
        [
            ("runs", "/api/runs/"),
            ("assets", "/api/assets/"),
            ("experiments", "/api/experiments/"),
            ("pipelines", "/api/pipelines/stats"),
        ],
    )
    def test_a_broken_store_yields_a_server_error(self, client, monkeypatch, module_name, url):
        _break_store(monkeypatch, module_name)

        response = client.get(url)

        assert response.status_code >= 500, (
            f"{url} answered {response.status_code}; a storage failure must not be "
            "reported as success"
        )

    @pytest.mark.parametrize(
        ("module_name", "url", "collection"),
        [
            ("runs", "/api/runs/", "runs"),
            ("assets", "/api/assets/", "assets"),
            ("experiments", "/api/experiments/", "experiments"),
        ],
    )
    def test_a_broken_store_never_returns_an_empty_collection(
        self,
        client,
        monkeypatch,
        module_name,
        url,
        collection,
    ):
        """An empty list would be indistinguishable from having no data."""
        _break_store(monkeypatch, module_name)

        body = client.get(url).json()

        assert body.get(collection) != [], (
            f"{url} returned an empty {collection} list on failure, which the UI "
            "renders as its empty state"
        )

    def test_pipeline_stats_do_not_report_zeroes_on_failure(self, client, monkeypatch):
        """Zeroed statistics look exactly like an installation nothing has run on."""
        _break_store(monkeypatch, "pipelines")

        response = client.get("/api/pipelines/stats")

        assert response.status_code >= 500
        assert response.json().get("total_pipelines") != 0


class TestHealthyRequestsAreUnaffected:
    """The change must not turn ordinary empty results into errors."""

    @pytest.mark.parametrize(
        "url",
        [
            "/api/runs/",
            "/api/assets/",
            "/api/experiments/",
            "/api/pipelines/",
            "/api/pipelines/stats",
        ],
    )
    def test_a_working_store_still_returns_200(self, client, url):
        assert client.get(url).status_code == 200

    def test_no_results_is_still_a_success(self, client):
        """Filtering to a project that does not exist is not an error."""
        response = client.get("/api/runs/?project=definitely-not-a-real-project")

        assert response.status_code == 200
        assert response.json()["runs"] == []

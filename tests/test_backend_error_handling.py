"""Error-response and input-bound tests for the UI backend.

Two production concerns are covered.

*Information disclosure.* Handlers across the API raise
``HTTPException(500, detail=str(e))``.  For a SQLAlchemy failure that string
carries the failing statement and connection details; for a filesystem failure
it carries absolute server paths.  Redacting centrally covers every call site
at once, and keeps full detail in development where the operator is the
developer.

*Resource exhaustion.* List endpoints took an unbounded ``limit``, so a single
``?limit=100000000`` made the server materialise an arbitrarily large result
set.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi import HTTPException  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SECRET_SQL = "SELECT * FROM users WHERE password='hunter2'"
SECRET_DSN = "psycopg2 connect failed: password=hunter2 host=10.0.0.5"


async def _raises_http_500():
    raise HTTPException(status_code=500, detail=SECRET_SQL)


async def _raises_unhandled():
    raise RuntimeError(SECRET_DSN)


@pytest.fixture
def app_with_failing_routes():
    """The real app plus two routes that fail the way real handlers do."""
    from flowyml.ui.backend.main import app

    added = [
        APIRoute("/api/_test_http_500", _raises_http_500, methods=["GET"]),
        APIRoute("/api/_test_unhandled", _raises_unhandled, methods=["GET"]),
    ]
    # Insert at the front: a catch-all SPA route is registered last and would
    # otherwise shadow anything added after import.
    for route in added:
        app.router.routes.insert(0, route)
    try:
        yield app
    finally:
        for route in added:
            app.router.routes.remove(route)


@pytest.fixture
def dev_env(monkeypatch):
    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)


@pytest.fixture
def prod_env(monkeypatch):
    monkeypatch.setenv("FLOWYML_ENV", "production")
    monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
    monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "secret-password")
    return {"Authorization": "Bearer secret-token"}


class TestProductionErrorRedaction:
    def test_http_500_detail_is_redacted(self, prod_env, app_with_failing_routes):
        with TestClient(app_with_failing_routes, raise_server_exceptions=False) as client:
            response = client.get("/api/_test_http_500", headers=prod_env)

        assert response.status_code == 500
        assert "hunter2" not in response.text
        assert "SELECT" not in response.text

    def test_unhandled_exception_text_is_redacted(self, prod_env, app_with_failing_routes):
        with TestClient(app_with_failing_routes, raise_server_exceptions=False) as client:
            response = client.get("/api/_test_unhandled", headers=prod_env)

        assert response.status_code == 500
        assert "hunter2" not in response.text
        assert "10.0.0.5" not in response.text
        assert "detail" not in response.json()

    def test_responses_carry_a_reference_for_log_correlation(
        self,
        prod_env,
        app_with_failing_routes,
    ):
        with TestClient(app_with_failing_routes, raise_server_exceptions=False) as client:
            for path in ("/api/_test_http_500", "/api/_test_unhandled"):
                body = client.get(path, headers=prod_env).json()
                assert body["reference"], path

    def test_client_errors_keep_their_message(self, prod_env, app_with_failing_routes):
        """Redaction applies to 5xx only; 4xx text is meant for the caller."""
        with TestClient(app_with_failing_routes) as client:
            response = client.get("/api/runs/nonexistent-run-id", headers=prod_env)

        assert response.status_code == 404
        assert response.json()["detail"]


class TestDevelopmentErrorDetail:
    def test_detail_is_preserved_for_the_developer(self, dev_env, app_with_failing_routes):
        with TestClient(app_with_failing_routes, raise_server_exceptions=False) as client:
            response = client.get("/api/_test_http_500")

        assert response.status_code == 500
        assert SECRET_SQL in response.text

    def test_unhandled_exception_detail_is_preserved(self, dev_env, app_with_failing_routes):
        with TestClient(app_with_failing_routes, raise_server_exceptions=False) as client:
            body = client.get("/api/_test_unhandled").json()

        assert body["detail"] == SECRET_DSN


class TestUnknownApiRoutes:
    def test_unknown_api_path_returns_json_not_the_spa_shell(self, dev_env):
        """A typo'd fetch URL must not receive HTML with a 200-looking body."""
        from flowyml.ui.backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/no-such-endpoint")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")


class TestPaginationBounds:
    """Every list endpoint must reject an unbounded page size."""

    OVERSIZED = [
        "/api/assets/?limit=100000000",
        "/api/runs/?limit=100000000",
        "/api/pipelines/?limit=100000000",
        "/api/traces/?limit=100000000",
        "/api/projects/demo/runs?limit=100000000",
        "/api/projects/demo/artifacts?limit=100000000",
        "/api/projects/demo/metrics?limit=100000000",
        "/api/assets/search?q=x&limit=100000000",
        "/api/assets/lineage?depth=1000",
    ]

    NON_POSITIVE = [
        "/api/assets/?limit=0",
        "/api/runs/?limit=-1",
        "/api/pipelines/?limit=0",
        "/api/traces/?limit=-10",
    ]

    VALID = [
        "/api/assets/?limit=25",
        "/api/runs/?limit=25",
        "/api/pipelines/?limit=25",
        "/api/traces/?limit=25",
        "/api/assets/search?q=model",
        "/api/assets/lineage?depth=2",
    ]

    @pytest.fixture
    def client(self, dev_env):
        from flowyml.ui.backend.main import app

        with TestClient(app) as test_client:
            yield test_client

    @pytest.mark.parametrize("url", OVERSIZED)
    def test_oversized_limit_is_rejected(self, client, url):
        assert client.get(url).status_code == 422, url

    @pytest.mark.parametrize("url", NON_POSITIVE)
    def test_non_positive_limit_is_rejected(self, client, url):
        assert client.get(url).status_code == 422, url

    @pytest.mark.parametrize("url", VALID)
    def test_reasonable_requests_still_succeed(self, client, url):
        assert client.get(url).status_code == 200, url

    def test_negative_log_offset_is_rejected(self, client):
        response = client.get("/api/runs/some-run/steps/some-step/logs?offset=-1")
        assert response.status_code == 422

    def test_empty_search_query_is_rejected(self, client):
        assert client.get("/api/assets/search?q=").status_code == 422

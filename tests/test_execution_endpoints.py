"""Functional tests for the token and server-info endpoints the UI depends on.

The API Tokens page's "Revoke" button used to call an endpoint that did not
exist, and never checked the response, so the UI reported success while the
token stayed valid.  The Settings page's system-information card used to call a
missing endpoint too, so it always rendered its hard-coded fallbacks: version
"0.1.0" and database "PostgreSQL", regardless of the real values.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from flowyml.ui.backend.auth import TokenManager  # noqa: E402


@pytest.fixture
def client(monkeypatch, tmp_path):
    """A dev-mode client backed by an isolated token store."""
    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)

    import flowyml.ui.backend.auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "token_manager",
        TokenManager(tokens_file=str(tmp_path / "tokens.json")),
    )

    from flowyml.ui.backend.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def token_manager():
    from flowyml.ui.backend.auth import token_manager as tm

    return tm


class TestServerInfo:
    def test_reports_the_real_package_version(self, client):
        from flowyml import __version__

        body = client.get("/api/execution/info").json()
        assert body["version"] == __version__
        # The fallback the UI used to display unconditionally.
        assert body["version"] != "0.1.0"

    def test_reports_the_real_database_backend(self, client):
        body = client.get("/api/execution/info").json()
        # Default deployment is SQLite, not the hard-coded "PostgreSQL".
        assert body["database"] == "sqlite"

    def test_reports_environment_and_uptime(self, client):
        body = client.get("/api/execution/info").json()
        assert body["environment"] == "development"
        assert body["uptime_seconds"] >= 0
        assert isinstance(body["uptime"], str) and body["uptime"]

    def test_reports_production_environment(self, client, monkeypatch):
        # A production deployment must also be authenticated, otherwise the
        # middleware (correctly) refuses the request before it reaches here.
        monkeypatch.setenv("FLOWYML_ENV", "production")
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")

        response = client.get(
            "/api/execution/info",
            headers={"Authorization": "Bearer secret-token"},
        )
        assert response.status_code == 200
        assert response.json()["environment"] == "production"


class TestTokenListing:
    def test_empty_store_lists_no_tokens(self, client):
        assert client.get("/api/execution/tokens").json() == {"tokens": []}

    def test_listing_never_reveals_token_values(self, client, token_manager):
        token = token_manager.create_token(name="ci", permissions=["read"])

        body = client.get("/api/execution/tokens").text
        assert token not in body

    def test_listing_exposes_a_stable_public_id(self, client, token_manager):
        token_manager.create_token(name="ci")

        tokens = client.get("/api/execution/tokens").json()["tokens"]
        assert len(tokens) == 1
        assert tokens[0]["id"]
        # Stable across calls, so the UI can address a specific row.
        assert tokens[0]["id"] == client.get("/api/execution/tokens").json()["tokens"][0]["id"]


class TestTokenRevocation:
    def test_revoking_by_id_invalidates_the_token(self, client, token_manager):
        token = token_manager.create_token(name="leaked")
        token_id = client.get("/api/execution/tokens").json()["tokens"][0]["id"]

        response = client.delete(f"/api/execution/tokens/{token_id}")
        assert response.status_code == 200
        assert response.json()["revoked"] == 1

        # The whole point: the credential must actually stop working.
        assert token_manager.verify_token(token) is None
        assert client.get("/api/execution/tokens").json()["tokens"] == []

    def test_revoking_by_name_removes_every_match(self, client, token_manager):
        """Names are user-supplied labels and need not be unique."""
        first = token_manager.create_token(name="shared-label")
        second = token_manager.create_token(name="shared-label")
        keep = token_manager.create_token(name="other")

        response = client.delete("/api/execution/tokens/shared-label")
        assert response.status_code == 200
        assert response.json()["revoked"] == 2

        assert token_manager.verify_token(first) is None
        assert token_manager.verify_token(second) is None
        assert token_manager.verify_token(keep) is not None

    def test_revoking_by_id_removes_only_that_token(self, client, token_manager):
        token_manager.create_token(name="shared-label")
        survivor = token_manager.create_token(name="shared-label")

        listed = client.get("/api/execution/tokens").json()["tokens"]
        survivor_id = next(
            entry["id"]
            for entry in listed
            # identify the survivor by elimination: revoke the other one
            if entry["id"] != listed[0]["id"]
        )
        victim_id = listed[0]["id"]

        assert client.delete(f"/api/execution/tokens/{victim_id}").json()["revoked"] == 1

        remaining = client.get("/api/execution/tokens").json()["tokens"]
        assert [entry["id"] for entry in remaining] == [survivor_id]
        assert token_manager.verify_token(survivor) is not None

    def test_unknown_reference_returns_404(self, client):
        response = client.delete("/api/execution/tokens/does-not-exist")
        assert response.status_code == 404
        assert "does-not-exist" in response.json()["detail"]

    def test_names_needing_url_encoding_round_trip(self, client, token_manager):
        token = token_manager.create_token(name="build token #1")

        response = client.delete("/api/execution/tokens/build%20token%20%231")
        assert response.status_code == 200
        assert token_manager.verify_token(token) is None


class TestTokenInitialisation:
    def test_first_token_can_be_created_without_auth(self, client):
        response = client.post("/api/execution/tokens/init")
        assert response.status_code == 200
        assert response.json()["token"].startswith("uf_")

    def test_init_refuses_once_a_token_exists(self, client, token_manager):
        token_manager.create_token(name="existing")

        response = client.post("/api/execution/tokens/init")
        assert response.status_code == 403

    def test_created_token_has_admin_permission(self, client, token_manager):
        token = client.post("/api/execution/tokens/init").json()["token"]

        data = token_manager.verify_token(token)
        assert data is not None
        assert "admin" in data["permissions"]

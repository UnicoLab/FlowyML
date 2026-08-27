"""Tests for the UI backend's authentication and authorization posture.

These cover the fail-closed guarantees: a deployment that declares itself
production but has no credentials must refuse to serve, must never fall back to
the publicly documented default password, and must never mint a guessable
session token.  ``POST /api/execution/execute`` imports and runs arbitrary
Python modules, so an unauthenticated instance is remote code execution.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from flowyml.ui.backend import security  # noqa: E402


@pytest.fixture
def production_env(monkeypatch):
    """Put the process into production mode with no credentials configured."""
    monkeypatch.setenv("FLOWYML_ENV", "production")
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)
    monkeypatch.delenv("FLOWYML_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("FLOWYML_ALLOW_INSECURE", raising=False)


@pytest.fixture
def dev_env(monkeypatch):
    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)
    monkeypatch.delenv("FLOWYML_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("FLOWYML_ALLOW_INSECURE", raising=False)


@pytest.fixture
def app():
    from flowyml.ui.backend.main import app as fastapi_app

    return fastapi_app


# ---------------------------------------------------------------------------
# security helpers
# ---------------------------------------------------------------------------


class TestSecurityHelpers:
    def test_blank_env_var_counts_as_unset(self, monkeypatch):
        """docker-compose ships FLOWYML_API_TOKEN= with an empty value."""
        monkeypatch.setenv("FLOWYML_API_TOKEN", "   ")
        assert security.get_api_token() is None

    def test_is_production_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("FLOWYML_ENV", "PRODUCTION")
        assert security.is_production() is True

    def test_non_production_env_is_not_production(self, monkeypatch):
        monkeypatch.setenv("FLOWYML_ENV", "staging")
        assert security.is_production() is False

    def test_constant_time_equals_rejects_none(self):
        assert security.constant_time_equals(None, "x") is False
        assert security.constant_time_equals("x", None) is False
        assert security.constant_time_equals(None, None) is False

    def test_constant_time_equals_matches_identical_secrets(self):
        assert security.constant_time_equals("s3cret", "s3cret") is True
        assert security.constant_time_equals("s3cret", "s3crey") is False

    def test_cors_never_uses_wildcard(self, dev_env):
        """A wildcard origin combined with credentials lets any site read the API."""
        assert "*" not in security.get_cors_origins()

    def test_cors_origins_are_configurable(self, monkeypatch):
        monkeypatch.setenv("FLOWYML_CORS_ORIGINS", "https://a.example, https://b.example")
        assert security.get_cors_origins() == ["https://a.example", "https://b.example"]

    def test_public_prefix_cannot_be_widened(self):
        """`/assets` must not act as a prefix for an unrelated route."""
        assert security.is_public_path("/assets/index.js") is True
        assert security.is_public_path("/assets-internal/secrets") is False

    def test_api_assets_route_is_not_public(self):
        assert security.is_public_path("/api/assets/") is False


class TestProductionValidation:
    def test_production_without_credentials_is_rejected(self, production_env):
        problems = security.security_misconfigurations()
        assert len(problems) == 2
        assert any("FLOWYML_API_TOKEN" in p for p in problems)
        assert any("FLOWYML_ADMIN_PASSWORD" in p for p in problems)

        with pytest.raises(RuntimeError, match="refuses to start"):
            security.assert_production_security()

    def test_default_password_is_rejected_in_production(self, production_env, monkeypatch):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "a-real-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", security.INSECURE_DEFAULT_PASSWORD)

        problems = security.security_misconfigurations()
        assert len(problems) == 1
        assert "default" in problems[0]

    def test_fully_configured_production_passes(self, production_env, monkeypatch):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "a-real-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "a-real-password")

        assert security.security_misconfigurations() == []
        security.assert_production_security()  # must not raise

    def test_explicit_opt_out_is_honoured(self, production_env, monkeypatch):
        """Operators terminating auth at a proxy can opt out deliberately."""
        monkeypatch.setenv("FLOWYML_ALLOW_INSECURE", "1")
        assert security.security_misconfigurations() == []
        security.assert_production_security()

    def test_development_is_never_blocked(self, dev_env):
        assert security.security_misconfigurations() == []
        security.assert_production_security()


# ---------------------------------------------------------------------------
# middleware
# ---------------------------------------------------------------------------


class TestAuthMiddleware:
    def test_development_allows_unauthenticated_requests(self, dev_env, app):
        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 200
            assert client.get("/api/runs/").status_code == 200

    def test_production_without_token_refuses_to_start(self, production_env, app):
        """The lifespan handler must abort startup rather than serve openly."""
        with pytest.raises(RuntimeError, match="refuses to start"):
            with TestClient(app):
                pass

    def test_production_without_token_denies_requests(self, production_env, app):
        """Second line of defence when the lifespan handler never ran.

        An ASGI host that imports ``app`` and serves it without running
        lifespan events would previously have exposed everything.
        """
        client = TestClient(app)  # not used as a context manager => no lifespan
        response = client.get("/api/runs/")
        assert response.status_code == 503
        # The remedy is logged for the operator; the caller is told nothing
        # that would confirm the instance is running unauthenticated.
        assert "FLOWYML_API_TOKEN" not in response.text
        assert "misconfigured" in response.json()["message"]

    def test_production_rejects_missing_token(self, production_env, monkeypatch, app):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "pw")

        with TestClient(app) as client:
            response = client.get("/api/runs/")
            assert response.status_code == 401
            assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_production_rejects_wrong_token(self, production_env, monkeypatch, app):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "pw")

        with TestClient(app) as client:
            response = client.get(
                "/api/runs/",
                headers={"Authorization": "Bearer wrong-token"},
            )
            assert response.status_code == 401

    def test_production_accepts_valid_bearer_token(self, production_env, monkeypatch, app):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "pw")

        with TestClient(app) as client:
            response = client.get(
                "/api/runs/",
                headers={"Authorization": "Bearer secret-token"},
            )
            assert response.status_code == 200

    def test_production_accepts_session_cookie(self, production_env, monkeypatch, app):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "pw")

        with TestClient(app) as client:
            client.cookies.set("access_token", "Bearer secret-token")
            assert client.get("/api/runs/").status_code == 200

    def test_query_string_token_is_not_accepted(self, production_env, monkeypatch, app):
        """Tokens in URLs leak via access logs, history and Referer headers."""
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "pw")

        with TestClient(app) as client:
            response = client.get("/api/runs/?token=secret-token")
            assert response.status_code == 401

    def test_health_stays_public_in_production(self, production_env, monkeypatch, app):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "pw")

        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 200

    def test_malformed_authorization_header_is_rejected(self, production_env, monkeypatch, app):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "pw")

        with TestClient(app) as client:
            for header in ("secret-token", "Basic secret-token", "Bearer"):
                response = client.get("/api/runs/", headers={"Authorization": header})
                assert response.status_code == 401, header


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_production_login_refuses_without_configured_password(
        self,
        production_env,
        monkeypatch,
        app,
    ):
        """Must never accept the publicly documented default in production."""
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": security.INSECURE_DEFAULT_PASSWORD},
        )
        # Refused, and without echoing the configuration detail to the caller.
        assert response.status_code == 503
        assert "FLOWYML_ADMIN_PASSWORD" not in response.text

    def test_production_login_never_issues_placeholder_token(
        self,
        production_env,
        monkeypatch,
        app,
    ):
        """The old code handed out the guessable string 'dev-token-placeholder'."""
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "correct-horse")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct-horse"},
        )
        assert response.status_code == 503
        # Crucially, no token is issued - least of all a guessable placeholder.
        assert "dev-token-placeholder" not in response.text
        assert "access_token" not in response.json()

    def test_successful_production_login_sets_secure_cookie(
        self,
        production_env,
        monkeypatch,
        app,
    ):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "correct-horse")

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "correct-horse"},
            )
            assert response.status_code == 200
            assert response.json()["access_token"] == "secret-token"

            cookie_header = response.headers["set-cookie"]
            assert "HttpOnly" in cookie_header
            assert "Secure" in cookie_header

    def test_wrong_password_is_rejected(self, production_env, monkeypatch, app):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "correct-horse")

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "wrong"},
            )
            assert response.status_code == 401

    def test_wrong_username_is_rejected(self, production_env, monkeypatch, app):
        monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
        monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "correct-horse")

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={"username": "intruder", "password": "correct-horse"},
            )
            assert response.status_code == 401

    def test_development_login_uses_default_password(self, dev_env, app):
        """Local development stays zero-config."""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": security.INSECURE_DEFAULT_PASSWORD},
            )
            assert response.status_code == 200

    def test_logout_clears_the_cookie(self, dev_env, app):
        with TestClient(app) as client:
            response = client.post("/api/auth/logout")
            assert response.status_code == 200
            assert 'access_token=""' in response.headers["set-cookie"]

"""WebSocket endpoints must enforce the same authentication as HTTP routes.

``AuthMiddleware`` is a Starlette ``BaseHTTPMiddleware``, which only processes
scopes of type ``http``. WebSocket handshakes pass straight through it, so in
production the log-streaming endpoints accepted any connection while every HTTP
route demanded a bearer token. Pipeline step logs routinely carry data paths,
hostnames and occasionally credentials, so that was a plain read bypass.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient  # noqa: E402

from flowyml.ui.backend.security import is_websocket_authorized  # noqa: E402

WS_ENDPOINTS = [
    "/ws/runs/run-1/logs",
    "/ws/runs/run-1/steps/train/logs",
]


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setenv("FLOWYML_ENV", "production")
    monkeypatch.setenv("FLOWYML_API_TOKEN", "secret-token")
    monkeypatch.setenv("FLOWYML_ADMIN_PASSWORD", "secret-password")
    monkeypatch.delenv("FLOWYML_ALLOW_INSECURE", raising=False)


@pytest.fixture
def development(monkeypatch):
    monkeypatch.delenv("FLOWYML_ENV", raising=False)
    monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)
    monkeypatch.delenv("FLOWYML_ALLOW_INSECURE", raising=False)


@pytest.fixture
def client():
    from flowyml.ui.backend.main import app

    with TestClient(app) as test_client:
        yield test_client


def _can_connect(client, endpoint, **kwargs) -> bool:
    try:
        with client.websocket_connect(endpoint, **kwargs):
            return True
    except Exception:
        return False


class TestAuthorizationHelper:
    def test_development_allows_everything(self, development):
        assert is_websocket_authorized({}, {}) is True

    def test_production_without_credentials_is_refused(self, production):
        assert is_websocket_authorized({}, {}) is False

    def test_production_accepts_a_bearer_header(self, production):
        assert is_websocket_authorized({"authorization": "Bearer secret-token"}, {}) is True

    def test_production_accepts_the_session_cookie(self, production):
        """Browsers cannot set headers on a WebSocket handshake."""
        assert is_websocket_authorized({}, {"access_token": "Bearer secret-token"}) is True

    def test_production_rejects_a_wrong_token(self, production):
        assert is_websocket_authorized({"authorization": "Bearer wrong"}, {}) is False

    def test_a_query_string_token_is_not_accepted(self, production, client):
        """URLs leak into access logs, history and Referer headers."""
        assert not _can_connect(client, "/ws/runs/r/logs?token=secret-token")

    @pytest.mark.parametrize(
        "credential",
        ["secret-token", "Basic secret-token", "Bearer", "Bearer ", ""],
    )
    def test_malformed_credentials_are_rejected(self, production, credential):
        assert is_websocket_authorized({"authorization": credential}, {}) is False

    def test_missing_server_token_fails_closed(self, monkeypatch):
        monkeypatch.setenv("FLOWYML_ENV", "production")
        monkeypatch.delenv("FLOWYML_API_TOKEN", raising=False)
        monkeypatch.delenv("FLOWYML_ALLOW_INSECURE", raising=False)

        assert is_websocket_authorized({"authorization": "Bearer anything"}, {}) is False

    def test_explicit_opt_out_is_honoured(self, production, monkeypatch):
        monkeypatch.setenv("FLOWYML_ALLOW_INSECURE", "1")
        assert is_websocket_authorized({}, {}) is True


class TestEndpointEnforcement:
    @pytest.mark.parametrize("endpoint", WS_ENDPOINTS)
    def test_unauthenticated_handshake_is_refused(self, production, client, endpoint):
        assert not _can_connect(client, endpoint)

    @pytest.mark.parametrize("endpoint", WS_ENDPOINTS)
    def test_a_wrong_token_is_refused(self, production, client, endpoint):
        assert not _can_connect(client, endpoint, headers={"Authorization": "Bearer wrong"})

    @pytest.mark.parametrize("endpoint", WS_ENDPOINTS)
    def test_a_valid_token_connects(self, production, client, endpoint):
        assert _can_connect(client, endpoint, headers={"Authorization": "Bearer secret-token"})

    @pytest.mark.parametrize("endpoint", WS_ENDPOINTS)
    def test_a_valid_cookie_connects(self, production, client, endpoint):
        client.cookies.set("access_token", "Bearer secret-token")
        assert _can_connect(client, endpoint)

    @pytest.mark.parametrize("endpoint", WS_ENDPOINTS)
    def test_development_stays_zero_config(self, development, client, endpoint):
        assert _can_connect(client, endpoint)


class TestStreamingStillWorks:
    @pytest.fixture
    def scoped_client(self, development, monkeypatch, tmp_path):
        """Client whose run logs are written under tmp_path."""
        from flowyml.utils import config as config_module

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        real_get_config = config_module.get_config

        def _scoped(*args, **kwargs):
            cfg = real_get_config(*args, **kwargs)
            cfg.runs_dir = runs_dir
            return cfg

        monkeypatch.setattr(config_module, "get_config", _scoped)

        from flowyml.ui.backend.main import app

        with TestClient(app) as test_client:
            yield test_client

    def test_a_posted_log_reaches_a_subscribed_client(self, scoped_client):
        """Authentication must not break the feature it protects."""
        client = scoped_client
        with client.websocket_connect("/ws/runs/live-run/steps/train/logs") as ws:
            client.post(
                "/api/runs/live-run/steps/train/logs",
                json={"content": "epoch 1", "level": "INFO"},
            )
            message = ws.receive_json()

        assert message["type"] == "log"
        assert message["content"] == "epoch 1"
        assert message["step"] == "train"

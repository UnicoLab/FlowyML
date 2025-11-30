"""Tests for the model metrics API."""

from pathlib import Path
import asyncio
import httpx

from flowyml.ui.backend.main import app
from flowyml.ui.backend.auth import token_manager
from tests.base import BaseTestCase


class TestMetricsAPI(BaseTestCase):
    """Ensure metrics endpoints integrate with projects and tokens."""

    def setUp(self):
        super().setUp()
        # Use temp token file
        self.tokens_file = Path(self.test_path) / "tokens.json"
        token_manager.tokens_file = self.tokens_file
        token_manager._load_tokens()

        self.loop = asyncio.new_event_loop()
        self.transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(
            transport=self.transport,
            base_url="http://testserver",
        )

        self.addCleanup(self._close_loop)
        self.addCleanup(lambda: self._run_async_cleanup(self.client.aclose()))
        self.addCleanup(lambda: self._run_async_cleanup(self.transport.aclose()))

        self.write_token = token_manager.create_token(
            name="metrics-writer",
            project="demo-project",
            permissions=["read", "write"],
        )
        self.read_token = token_manager.create_token(
            name="metrics-reader",
            project="demo-project",
            permissions=["read"],
        )

    def request(self, method: str, url: str, **kwargs):
        """Run an async httpx request on a dedicated event loop."""
        return self.loop.run_until_complete(self.client.request(method, url, **kwargs))

    def _run_async_cleanup(self, awaitable):
        if not self.loop.is_closed():
            self.loop.run_until_complete(awaitable)

    def _close_loop(self):
        if not self.loop.is_closed():
            self.loop.close()

    def test_log_and_query_metrics(self):
        """Log metrics and ensure they can be retrieved via both APIs."""
        payload = {
            "project": "demo-project",
            "model_name": "classifier-v1",
            "environment": "prod",
            "metrics": {"precision": 0.91, "recall": 0.88},
            "tags": {"region": "eu"},
        }

        resp = self.request(
            "POST",
            "/api/metrics/log",
            headers={"Authorization": f"Bearer {self.write_token}"},
            json=payload,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("precision", data["logged_metrics"])

        # Query via metrics API
        resp = self.request(
            "GET",
            "/api/metrics?model_name=classifier-v1",
            headers={"Authorization": f"Bearer {self.read_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        metrics = resp.json()["metrics"]
        self.assertTrue(metrics)
        self.assertEqual(metrics[0]["project"], "demo-project")

        # Query via project endpoint
        resp = self.request(
            "GET",
            "/api/projects/demo-project/metrics?model_name=classifier-v1",
        )
        self.assertEqual(resp.status_code, 200)
        project_metrics = resp.json()["metrics"]
        self.assertEqual(len(project_metrics), 2)  # precision + recall

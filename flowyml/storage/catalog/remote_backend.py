"""Remote Catalog Backend — HTTP client for remote FlowyML API server.

Used when FlowyML is deployed with a centralized API server.
The backend selection is automatic based on the active stack configuration.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from flowyml.storage.catalog.backend import CatalogBackend, CatalogEntry

logger = logging.getLogger(__name__)


class RemoteCatalogBackend(CatalogBackend):
    """HTTP-backed artifact catalog for remote/distributed deployments.

    Calls the FlowyML API server for all catalog operations. Used
    automatically when the active stack has a `catalog_endpoint` configured.

    Args:
        endpoint: Base URL of the FlowyML catalog API
                  e.g., "https://flowyml.example.com/api/v1/catalog"
        api_key: Optional API key for authentication
        timeout: HTTP request timeout in seconds
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        timeout: int = 30,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the catalog API.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            path: API path (e.g., "/artifacts")
            data: Request body data
            params: Query parameters

        Returns:
            Response data as dict
        """
        import urllib.request
        import urllib.error
        import urllib.parse

        url = f"{self.endpoint}{path}"
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError(f"Insecure URL scheme: {url}")

        if params:
            query_string = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None},
            )
            url = f"{url}?{query_string}"

        body = json.dumps(data).encode("utf-8") if data else None

        req = urllib.request.Request(  # noqa: S310
            url,
            data=body,
            headers=self._headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.error(f"Catalog API error {e.code}: {error_body}")
            raise RuntimeError(
                f"Catalog API error {e.code}: {error_body}",
            ) from e
        except urllib.error.URLError as e:
            logger.error(f"Catalog API connection error: {e}")
            raise RuntimeError(
                f"Cannot connect to catalog API at {self.endpoint}: {e}",
            ) from e

    def register(self, entry: CatalogEntry) -> str:
        """Register a new artifact via the remote API."""
        result = self._request("POST", "/artifacts", data=entry.to_dict())
        return result.get("artifact_id", entry.artifact_id)

    def get(self, artifact_id: str) -> CatalogEntry | None:
        """Get an artifact by ID from the remote API."""
        try:
            result = self._request("GET", f"/artifacts/{artifact_id}")
            return CatalogEntry.from_dict(result)
        except RuntimeError:
            return None

    def list_artifacts(
        self,
        artifact_type: str | None = None,
        source_pipeline: str | None = None,
        source_step: str | None = None,
        tags: dict[str, str] | None = None,
        limit: int = 100,
    ) -> list[CatalogEntry]:
        """List artifacts from the remote API."""
        params = {
            "artifact_type": artifact_type,
            "source_pipeline": source_pipeline,
            "source_step": source_step,
            "limit": str(limit),
        }
        if tags:
            params["tags"] = json.dumps(tags)

        result = self._request("GET", "/artifacts", params=params)
        items = result.get("items", result) if isinstance(result, dict) else result
        return [CatalogEntry.from_dict(item) for item in items]

    def tag(self, artifact_id: str, tags: dict[str, str]) -> None:
        """Add tags to an artifact via the remote API."""
        self._request("PUT", f"/artifacts/{artifact_id}/tags", data=tags)

    def search(self, query: str, limit: int = 50) -> list[CatalogEntry]:
        """Search artifacts via the remote API."""
        result = self._request(
            "GET",
            "/artifacts/search",
            params={"q": query, "limit": str(limit)},
        )
        items = result.get("items", result) if isinstance(result, dict) else result
        return [CatalogEntry.from_dict(item) for item in items]

    def get_lineage(self, artifact_id: str) -> dict[str, Any]:
        """Get lineage information from the remote API."""
        return self._request("GET", f"/artifacts/{artifact_id}/lineage")

    def find_by_content_hash(self, content_hash: str) -> CatalogEntry | None:
        """Find artifact by content hash via the remote API."""
        try:
            result = self._request(
                "GET",
                "/artifacts/by-hash",
                params={"hash": content_hash},
            )
            return CatalogEntry.from_dict(result) if result else None
        except RuntimeError:
            return None

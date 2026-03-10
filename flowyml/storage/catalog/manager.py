"""Artifact Catalog Manager — Facade for catalog operations.

Auto-selects the correct backend (local SQLite or remote HTTP) based on
the active stack configuration. This follows FlowyML's existing pattern
where the stack determines execution infrastructure.

Usage:
    from flowyml.storage.catalog import ArtifactCatalog

    catalog = ArtifactCatalog()  # Auto-selects backend
    catalog.register(entry)
    results = catalog.search("model")
    lineage = catalog.get_lineage(artifact_id)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from flowyml.storage.catalog.backend import CatalogBackend, CatalogEntry

logger = logging.getLogger(__name__)


class ArtifactCatalog:
    """Unified artifact catalog with automatic backend selection.

    The catalog auto-selects its backend:
    - If the active stack has a `catalog_endpoint` → RemoteCatalogBackend
    - Otherwise → LocalCatalogBackend (SQLite, zero-config)

    This ensures the catalog works seamlessly in:
    - Local development: file-based, no server needed
    - Remote execution: HTTP calls to FlowyML API server
    - Hybrid: local during dev, remote in production (stack-controlled)

    Args:
        backend: Explicit backend override (skips auto-detection)
        db_path: Path for local SQLite DB (only used if no remote endpoint)
    """

    def __init__(
        self,
        backend: CatalogBackend | None = None,
        db_path: str = ".flowyml/catalog.db",
    ):
        if backend:
            self._backend = backend
        else:
            self._backend = self._auto_select_backend(db_path)

    def _auto_select_backend(self, db_path: str) -> CatalogBackend:
        """Auto-select the catalog backend based on active stack.

        Args:
            db_path: Default path for local SQLite DB

        Returns:
            An appropriate CatalogBackend instance
        """
        # Try to get catalog endpoint from active stack
        try:
            from flowyml.stacks.registry import get_active_stack

            stack = get_active_stack()
            if stack:
                catalog_endpoint = getattr(stack, "catalog_endpoint", None)
                if catalog_endpoint:
                    from flowyml.storage.catalog.remote_backend import (
                        RemoteCatalogBackend,
                    )

                    api_key = getattr(stack, "catalog_api_key", None)
                    logger.info(
                        f"Using remote catalog backend: {catalog_endpoint}",
                    )
                    return RemoteCatalogBackend(
                        endpoint=catalog_endpoint,
                        api_key=api_key,
                    )
        except (ImportError, Exception) as e:
            logger.debug(f"Stack detection skipped: {e}")

        # Check environment variable
        import os

        env_endpoint = os.environ.get("FLOWYML_CATALOG_ENDPOINT")
        if env_endpoint:
            from flowyml.storage.catalog.remote_backend import RemoteCatalogBackend

            api_key = os.environ.get("FLOWYML_CATALOG_API_KEY")
            logger.info(f"Using remote catalog backend from env: {env_endpoint}")
            return RemoteCatalogBackend(endpoint=env_endpoint, api_key=api_key)

        # Default to local
        from flowyml.storage.catalog.local_backend import LocalCatalogBackend

        logger.debug(f"Using local catalog backend: {db_path}")
        return LocalCatalogBackend(db_path=db_path)

    @property
    def backend(self) -> CatalogBackend:
        """Get the active backend."""
        return self._backend

    def register(
        self,
        name: str,
        artifact_type: str,
        data: Any = None,
        source_step: str = "",
        source_run_id: str = "",
        source_pipeline: str = "",
        parent_ids: list[str] | None = None,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
        uri: str = "",
        version: str | None = None,
    ) -> str:
        """Register a new artifact in the catalog.

        Args:
            name: Human-readable artifact name
            artifact_type: Type string (Model, Dataset, Metrics, etc.)
            data: The actual artifact data (used for content hashing)
            source_step: Step that produced this artifact
            source_run_id: Run ID
            source_pipeline: Pipeline name
            parent_ids: IDs of parent artifacts
            tags: Discovery tags
            metadata: Additional metadata
            uri: Storage URI
            version: Optional version string

        Returns:
            Artifact ID
        """
        # Compute content hash if data is provided
        content_hash = ""
        if data is not None:
            content_hash = self._compute_hash(data)

            # Check for duplicate
            existing = self._backend.find_by_content_hash(content_hash)
            if existing:
                logger.info(
                    f"Artifact with same content already exists: '{existing.name}' ({existing.artifact_id})",
                )

        entry = CatalogEntry(
            name=name,
            artifact_type=artifact_type,
            content_hash=content_hash,
            source_step=source_step,
            source_run_id=source_run_id,
            source_pipeline=source_pipeline,
            parent_ids=parent_ids or [],
            tags=tags or {},
            metadata=metadata or {},
            uri=uri,
            version=version,
        )

        return self._backend.register(entry)

    def get(self, artifact_id: str) -> CatalogEntry | None:
        """Get an artifact by ID."""
        return self._backend.get(artifact_id)

    def list_artifacts(self, **filters) -> list[CatalogEntry]:
        """List artifacts with optional filters."""
        return self._backend.list_artifacts(**filters)

    def tag(self, artifact_id: str, **tags: str) -> None:
        """Add or update tags on an artifact."""
        self._backend.tag(artifact_id, tags)

    def search(self, query: str, limit: int = 50) -> list[CatalogEntry]:
        """Search artifacts."""
        return self._backend.search(query, limit)

    def get_lineage(self, artifact_id: str) -> dict[str, Any]:
        """Get full lineage tree for an artifact."""
        return self._backend.get_lineage(artifact_id)

    def find_by_hash(self, content_hash: str) -> CatalogEntry | None:
        """Find an artifact by content hash (deduplication lookup)."""
        return self._backend.find_by_content_hash(content_hash)

    def _compute_hash(self, data: Any) -> str:
        """Compute a content hash for artifact deduplication.

        Args:
            data: The artifact data to hash

        Returns:
            SHA-256 hex digest
        """
        try:
            # Try JSON serialization first
            serialized = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode()).hexdigest()
        except (TypeError, ValueError):
            # Fall back to repr
            return hashlib.sha256(repr(data).encode()).hexdigest()

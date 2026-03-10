"""Catalog Backend — Abstract protocol for artifact catalog storage.

Defines the abstract interface that both local (SQLite) and remote (HTTP)
backends implement. This follows FlowyML's existing pattern of
LocalOrchestrator / RemoteOrchestrator abstraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CatalogEntry:
    """An entry in the artifact catalog.

    Attributes:
        artifact_id: Unique identifier for the artifact
        name: Human-readable artifact name
        artifact_type: Type of artifact (Model, Dataset, Metrics, etc.)
        content_hash: Hash of the artifact content for deduplication
        source_step: Name of the step that produced this artifact
        source_run_id: ID of the run that produced this artifact
        source_pipeline: Name of the pipeline that produced this artifact
        parent_ids: IDs of parent artifacts (inputs to the producing step)
        tags: User-defined tags for discovery
        metadata: Additional metadata
        uri: Storage URI of the artifact
        created_at: When the artifact was registered
        version: Optional version string
    """

    artifact_id: str = ""
    name: str = ""
    artifact_type: str = ""
    content_hash: str = ""
    source_step: str = ""
    source_run_id: str = ""
    source_pipeline: str = ""
    parent_ids: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    uri: str = ""
    created_at: str = ""
    version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "artifact_type": self.artifact_type,
            "content_hash": self.content_hash,
            "source_step": self.source_step,
            "source_run_id": self.source_run_id,
            "source_pipeline": self.source_pipeline,
            "parent_ids": self.parent_ids,
            "tags": self.tags,
            "metadata": self.metadata,
            "uri": self.uri,
            "created_at": self.created_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CatalogEntry:
        """Deserialize from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CatalogBackend(ABC):
    """Abstract backend for the artifact catalog.

    Implementations:
    - LocalCatalogBackend: SQLite-based for local development
    - RemoteCatalogBackend: HTTP client for remote FlowyML API server
    """

    @abstractmethod
    def register(self, entry: CatalogEntry) -> str:
        """Register a new artifact in the catalog.

        Args:
            entry: CatalogEntry with artifact metadata

        Returns:
            Artifact ID
        """
        ...

    @abstractmethod
    def get(self, artifact_id: str) -> CatalogEntry | None:
        """Get an artifact by ID.

        Args:
            artifact_id: Unique artifact identifier

        Returns:
            CatalogEntry or None if not found
        """
        ...

    @abstractmethod
    def list_artifacts(
        self,
        artifact_type: str | None = None,
        source_pipeline: str | None = None,
        source_step: str | None = None,
        tags: dict[str, str] | None = None,
        limit: int = 100,
    ) -> list[CatalogEntry]:
        """List artifacts with optional filtering.

        Args:
            artifact_type: Filter by artifact type
            source_pipeline: Filter by source pipeline
            source_step: Filter by source step
            tags: Filter by tags (all must match)
            limit: Maximum number of results

        Returns:
            List of matching CatalogEntry objects
        """
        ...

    @abstractmethod
    def tag(self, artifact_id: str, tags: dict[str, str]) -> None:
        """Add or update tags on an artifact.

        Args:
            artifact_id: Artifact to tag
            tags: Tags to add/update
        """
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 50) -> list[CatalogEntry]:
        """Search artifacts by name, type, or tag values.

        Args:
            query: Search query string
            limit: Maximum results

        Returns:
            Matching CatalogEntry objects
        """
        ...

    @abstractmethod
    def get_lineage(self, artifact_id: str) -> dict[str, Any]:
        """Get lineage information for an artifact.

        Returns a tree structure showing what produced this artifact
        and what downstream artifacts consumed it.

        Args:
            artifact_id: Artifact to trace lineage for

        Returns:
            Lineage tree dict with 'parents' and 'children' lists
        """
        ...

    @abstractmethod
    def find_by_content_hash(self, content_hash: str) -> CatalogEntry | None:
        """Find an artifact by its content hash (deduplication).

        Args:
            content_hash: SHA-256 hash of the artifact content

        Returns:
            CatalogEntry or None if no match
        """
        ...

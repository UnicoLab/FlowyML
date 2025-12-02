"""Metadata storage backends for flowyml."""

from abc import ABC, abstractmethod
from flowyml.storage.sql import SQLMetadataStore


class MetadataStore(ABC):
    """Base class for metadata storage backends."""

    @abstractmethod
    def save_run(self, run_id: str, metadata: dict) -> None:
        """Save run metadata."""
        pass

    @abstractmethod
    def load_run(self, run_id: str) -> dict | None:
        """Load run metadata."""
        pass

    @abstractmethod
    def list_runs(self, limit: int | None = None) -> list[dict]:
        """List all runs."""
        pass

    @abstractmethod
    def list_pipelines(self) -> list[str]:
        """List all unique pipeline names."""
        pass

    @abstractmethod
    def save_artifact(self, artifact_id: str, metadata: dict) -> None:
        """Save artifact metadata."""
        pass

    @abstractmethod
    def load_artifact(self, artifact_id: str) -> dict | None:
        """Load artifact metadata."""
        pass

    @abstractmethod
    def list_assets(self, limit: int | None = None, **filters) -> list[dict]:
        """List assets with optional filters."""
        pass

    @abstractmethod
    def query(self, **filters) -> list[dict]:
        """Query runs with filters."""
        pass


# Alias for backward compatibility
SQLiteMetadataStore = SQLMetadataStore

"""Artifact storage backends for UniFlow."""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional
import pickle


class ArtifactStore(ABC):
    """Base class for artifact storage backends."""

    @abstractmethod
    def save(self, artifact: Any, path: str, metadata: Optional[dict] = None) -> str:
        """Save an artifact to storage.

        Args:
            artifact: The artifact to save
            path: Storage path for the artifact
            metadata: Optional metadata dictionary

        Returns:
            Full path where artifact was saved
        """
        pass

    @abstractmethod
    def load(self, path: str) -> Any:
        """Load an artifact from storage.

        Args:
            path: Storage path of the artifact

        Returns:
            The loaded artifact
        """
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if artifact exists at path."""
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete artifact at path."""
        pass

    @abstractmethod
    def list(self, prefix: str = "") -> list[str]:
        """List all artifacts with optional prefix filter."""
        pass


class LocalArtifactStore(ArtifactStore):
    """Local filesystem artifact storage."""

    def __init__(self, base_path: str = ".uniflow/artifacts"):
        """Initialize local artifact store.

        Args:
            base_path: Base directory for storing artifacts
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, artifact: Any, path: str, metadata: Optional[dict] = None) -> str:
        """Save artifact to local filesystem.

        Args:
            artifact: The artifact to save
            path: Relative path for the artifact
            metadata: Optional metadata dictionary

        Returns:
            Full path where artifact was saved
        """
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Save artifact using pickle by default
        with open(full_path, 'wb') as f:
            pickle.dump(artifact, f)

        # Save metadata if provided
        if metadata:
            metadata_path = full_path.with_suffix('.meta.json')
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        return str(full_path)

    def load(self, path: str) -> Any:
        """Load artifact from local filesystem.

        Args:
            path: Relative or absolute path to the artifact

        Returns:
            The loaded artifact
        """
        full_path = Path(path) if Path(path).is_absolute() else self.base_path / path

        if not full_path.exists():
            raise FileNotFoundError(f"Artifact not found at {full_path}")

        with open(full_path, 'rb') as f:
            return pickle.load(f)

    def exists(self, path: str) -> bool:
        """Check if artifact exists.

        Args:
            path: Relative path to check

        Returns:
            True if artifact exists, False otherwise
        """
        full_path = self.base_path / path
        return full_path.exists()

    def delete(self, path: str) -> None:
        """Delete artifact from filesystem.

        Args:
            path: Relative path to delete
        """
        full_path = self.base_path / path
        if full_path.exists():
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()

            # Also delete metadata if exists
            metadata_path = full_path.with_suffix('.meta.json')
            if metadata_path.exists():
                metadata_path.unlink()

    def list(self, prefix: str = "") -> list[str]:
        """List all artifacts with optional prefix.

        Args:
            prefix: Optional prefix filter

        Returns:
            List of artifact paths
        """
        search_path = self.base_path / prefix if prefix else self.base_path

        if not search_path.exists():
            return []

        artifacts = []
        for item in search_path.rglob('*'):
            if item.is_file() and not item.name.endswith('.meta.json'):
                rel_path = item.relative_to(self.base_path)
                artifacts.append(str(rel_path))

        return sorted(artifacts)

    def get_metadata(self, path: str) -> Optional[dict]:
        """Get metadata for an artifact.

        Args:
            path: Relative path to the artifact

        Returns:
            Metadata dictionary or None if no metadata exists
        """
        full_path = self.base_path / path
        metadata_path = full_path.with_suffix('.meta.json')

        if not metadata_path.exists():
            return None

        import json
        with open(metadata_path, 'r') as f:
            return json.load(f)

    def size(self, path: str) -> int:
        """Get size of artifact in bytes.

        Args:
            path: Relative path to the artifact

        Returns:
            Size in bytes
        """
        full_path = self.base_path / path
        if full_path.exists():
            return full_path.stat().st_size
        return 0

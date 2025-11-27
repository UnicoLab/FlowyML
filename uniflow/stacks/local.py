"""Local Stack - For local development and testing."""

from pathlib import Path
from uniflow.stacks.base import Stack
from uniflow.core.executor import LocalExecutor
from uniflow.storage.artifacts import LocalArtifactStore
from uniflow.storage.metadata import SQLiteMetadataStore


class LocalStack(Stack):
    """Local stack for development and testing.

    This stack uses:
    - LocalExecutor for running steps locally
    - LocalArtifactStore for filesystem-based artifact storage
    - SQLiteMetadataStore for metadata storage

    Example:
        ```python
        from uniflow import LocalStack, Pipeline

        # Create local stack
        stack = LocalStack(name="local", artifact_path=".uniflow/artifacts", metadata_path=".uniflow/metadata.db")

        # Use with pipeline
        pipeline = Pipeline("my_pipeline", stack=stack)
        result = pipeline.run()
        ```
    """

    def __init__(
        self,
        name: str = "local",
        artifact_path: str = ".uniflow/artifacts",
        metadata_path: str = ".uniflow/metadata.db",
    ):
        """Initialize LocalStack.

        Args:
            name: Stack name
            artifact_path: Path for artifact storage
            metadata_path: Path for metadata database
        """
        # Create storage backends
        executor = LocalExecutor()
        artifact_store = LocalArtifactStore(artifact_path)
        metadata_store = SQLiteMetadataStore(metadata_path)

        # Initialize base stack
        super().__init__(
            name=name,
            executor=executor,
            artifact_store=artifact_store,
            metadata_store=metadata_store,
        )

        # Ensure directories exist
        Path(artifact_path).mkdir(parents=True, exist_ok=True)
        Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        """Validate stack configuration.

        Returns:
            True if stack is valid
        """
        # Check artifact store path exists and is writable
        artifact_path = Path(self.artifact_store.base_path)
        if not artifact_path.exists():
            artifact_path.mkdir(parents=True, exist_ok=True)

        # Check metadata store path parent exists
        metadata_path = Path(self.metadata_store.db_path)
        if not metadata_path.parent.exists():
            metadata_path.parent.mkdir(parents=True, exist_ok=True)

        return True

    def cleanup(self) -> None:
        """Clean up stack resources."""
        # Could implement cache cleanup, temp file removal, etc.
        pass

    def get_stats(self) -> dict:
        """Get stack usage statistics.

        Returns:
            Dictionary with stack statistics
        """
        from pathlib import Path

        artifact_path = Path(self.artifact_store.base_path)
        metadata_path = Path(self.metadata_store.db_path)

        # Calculate artifact storage size
        artifact_size = sum(f.stat().st_size for f in artifact_path.rglob("*") if f.is_file())

        # Get metadata size
        metadata_size = metadata_path.stat().st_size if metadata_path.exists() else 0

        # Get metadata stats from store
        metadata_stats = self.metadata_store.get_statistics()

        return {
            "name": self.name,
            "artifact_storage_mb": artifact_size / (1024 * 1024),
            "metadata_storage_mb": metadata_size / (1024 * 1024),
            "total_runs": metadata_stats.get("total_runs", 0),
            "total_artifacts": metadata_stats.get("total_artifacts", 0),
            "total_metrics": metadata_stats.get("total_metrics", 0),
            "total_pipelines": metadata_stats.get("total_pipelines", 0),
        }

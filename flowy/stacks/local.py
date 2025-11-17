"""
Local Stack - For local development and testing.
"""

from pathlib import Path
from flowy.stacks.base import Stack
from flowy.core.executor import LocalExecutor


class LocalFileStore:
    """Local filesystem artifact store."""
    
    def __init__(self, path: str = ".flowy/artifacts"):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
    
    def save(self, key: str, data: any):
        """Save artifact to local filesystem."""
        # Simplified - real implementation would serialize properly
        pass
    
    def load(self, key: str):
        """Load artifact from local filesystem."""
        pass


class SQLiteStore:
    """SQLite metadata store."""
    
    def __init__(self, path: str = ".flowy/metadata.db"):
        self.path = path
    
    def save_run(self, run_data: dict):
        """Save run metadata."""
        pass
    
    def get_run(self, run_id: str):
        """Get run metadata."""
        pass


class LocalStack(Stack):
    """
    Local stack for development and testing.
    
    Example:
        >>> stack = LocalStack(name="local")
        >>> pipeline = Pipeline("my_pipeline", stack=stack)
    """
    
    def __init__(
        self,
        name: str = "local",
        artifact_path: str = ".flowy/artifacts",
        metadata_path: str = ".flowy/metadata.db"
    ):
        executor = LocalExecutor()
        artifact_store = LocalFileStore(artifact_path)
        metadata_store = SQLiteStore(metadata_path)
        
        super().__init__(
            name=name,
            executor=executor,
            artifact_store=artifact_store,
            metadata_store=metadata_store
        )

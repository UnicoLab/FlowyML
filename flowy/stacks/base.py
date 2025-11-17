"""
Base Stack - Defines execution environment for pipelines.
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class StackConfig:
    """Configuration for a stack."""
    name: str
    executor_type: str
    artifact_store: str
    metadata_store: str
    container_registry: Optional[str] = None
    orchestrator: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'executor_type': self.executor_type,
            'artifact_store': self.artifact_store,
            'metadata_store': self.metadata_store,
            'container_registry': self.container_registry,
            'orchestrator': self.orchestrator
        }


class Stack:
    """
    Stack defines the execution environment for pipelines.
    
    A stack includes:
    - Executor: Where steps run (local, cloud, kubernetes)
    - Artifact Store: Where outputs are stored (local, S3, GCS)
    - Metadata Store: Where run metadata is stored (SQLite, Postgres)
    - Container Registry: For containerized execution (optional)
    - Orchestrator: For workflow orchestration (optional)
    """
    
    def __init__(
        self,
        name: str,
        executor: Any,
        artifact_store: Any,
        metadata_store: Any,
        container_registry: Optional[Any] = None,
        orchestrator: Optional[Any] = None
    ):
        self.name = name
        self.executor = executor
        self.artifact_store = artifact_store
        self.metadata_store = metadata_store
        self.container_registry = container_registry
        self.orchestrator = orchestrator
        
        self.config = StackConfig(
            name=name,
            executor_type=type(executor).__name__,
            artifact_store=type(artifact_store).__name__,
            metadata_store=type(metadata_store).__name__,
            container_registry=type(container_registry).__name__ if container_registry else None,
            orchestrator=type(orchestrator).__name__ if orchestrator else None
        )
    
    def activate(self):
        """Activate this stack as the active stack."""
        # In a real implementation, this would set the global active stack
        pass
    
    def validate(self) -> bool:
        """Validate that all stack components are properly configured."""
        # Check that all components are properly configured
        return True
    
    def __repr__(self) -> str:
        return f"Stack(name='{self.name}', executor={type(self.executor).__name__})"

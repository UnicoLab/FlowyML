"""Stack Components - Reusable building blocks for stacks.

This module provides base classes for orchestrators, artifact stores,
container registries, and other stack components.
"""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass, field
from enum import Enum


class ComponentType(Enum):
    """Types of stack components."""

    ORCHESTRATOR = "orchestrator"
    ARTIFACT_STORE = "artifact_store"
    CONTAINER_REGISTRY = "container_registry"
    METADATA_STORE = "metadata_store"
    EXECUTOR = "executor"


@dataclass
class ResourceConfig:
    """Configuration for compute resources."""

    cpu: str = "1"  # e.g., "2", "4", "8"
    memory: str = "2Gi"  # e.g., "4Gi", "8Gi", "16Gi"
    gpu: str | None = None  # e.g., "nvidia-tesla-t4", "nvidia-tesla-v100"
    gpu_count: int = 0
    disk_size: str = "10Gi"
    machine_type: str | None = None  # Cloud-specific machine type

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu": self.cpu,
            "memory": self.memory,
            "gpu": self.gpu,
            "gpu_count": self.gpu_count,
            "disk_size": self.disk_size,
            "machine_type": self.machine_type,
        }


@dataclass
class DockerConfig:
    """Configuration for Docker containerization."""

    image: str | None = None  # e.g., "gcr.io/myproject/flowyml:latest"
    dockerfile: str | None = None  # Path to Dockerfile
    build_context: str = "."
    requirements: list[str] | None = None  # Python requirements
    base_image: str = "python:3.11-slim"
    env_vars: dict[str, str] = field(default_factory=dict)
    build_args: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "image": self.image,
            "dockerfile": self.dockerfile,
            "build_context": self.build_context,
            "requirements": self.requirements or [],
            "base_image": self.base_image,
            "env_vars": self.env_vars,
            "build_args": self.build_args,
        }


class StackComponent(ABC):
    """Base class for all stack components."""

    def __init__(self, name: str):
        self.name = name

    @property
    @abstractmethod
    def component_type(self) -> ComponentType:
        """Return the type of this component."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate component configuration."""
        pass

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert component to dictionary."""
        pass


class Orchestrator(StackComponent):
    """Base class for orchestrators."""

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.ORCHESTRATOR

    @abstractmethod
    def run_pipeline(
        self,
        pipeline: Any,
        run_id: str,
        resources: "ResourceConfig | None" = None,
        docker_config: "DockerConfig | None" = None,
        inputs: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs,
    ) -> Any:
        """Run a pipeline on this orchestrator.

        Args:
            pipeline: The pipeline to run.
            run_id: The unique run identifier.
            resources: Resource configuration.
            docker_config: Docker configuration.
            inputs: Input data.
            context: Context variables.
            **kwargs: Additional arguments.

        Returns:
            The run result or job ID.
        """
        pass

    @abstractmethod
    def get_run_status(self, run_id: str) -> str:
        """Get status of a pipeline run."""
        pass


class ArtifactStore(StackComponent):
    """Base class for artifact stores."""

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.ARTIFACT_STORE

    @abstractmethod
    def save(self, artifact: Any, path: str) -> str:
        """Save artifact to store."""
        pass

    @abstractmethod
    def load(self, path: str) -> Any:
        """Load artifact from store."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if artifact exists."""
        pass


class ContainerRegistry(StackComponent):
    """Base class for container registries."""

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.CONTAINER_REGISTRY

    @abstractmethod
    def push_image(self, image_name: str, tag: str = "latest") -> str:
        """Push Docker image to registry."""
        pass

    @abstractmethod
    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        """Pull Docker image from registry."""
        pass

    @abstractmethod
    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        """Get full URI for an image."""
        pass

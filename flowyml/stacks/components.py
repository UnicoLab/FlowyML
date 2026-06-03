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
    MODEL_DEPLOYER = "model_deployer"
    MODEL_REGISTRY = "model_registry"
    EXPERIMENT_TRACKER = "experiment_tracker"


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
    """Configuration for Docker containerization.

    Controls all aspects of Docker image generation for FlowyML pipelines
    including base image selection, dependency management, GPU support,
    build optimization, and image tagging.

    Attributes:
        image: Pre-built image URI (skips build when set).
        dockerfile: Path to an existing Dockerfile to use instead of
            auto-generating one.
        build_context: Root directory for the Docker build context.
        requirements: Inline list of Python packages to install.
        base_image: Base Docker image (overridden when *gpu_enabled* is set).
        env_vars: Environment variables injected into the container.
        build_args: Docker build-time arguments (``--build-arg``).
        command: Container ``CMD`` directive.
        args: Additional arguments appended to *command*.
        apt_packages: System packages installed via ``apt-get``.
        platform: Target platform for cross-compilation
            (e.g. ``linux/amd64``, ``linux/arm64``).
        gpu_enabled: When ``True``, selects an NVIDIA CUDA base image.
        cuda_version: Explicit CUDA version (e.g. ``"12.4"``).
            Defaults to ``12.4`` when *gpu_enabled* is set.
        requirements_file: Explicit path to a ``requirements.txt`` file.
        use_poetry: Use Poetry for dependency management.
        use_uv: Use *uv* for dependency management (preferred default).
        use_conda: Use Conda/Mamba for dependency management.
        conda_file: Path to a ``conda.yaml`` or ``environment.yml`` file.
        multi_stage: Enable multi-stage Docker builds for smaller images.
        cache_pip: Enable BuildKit cache mounts for pip / uv / conda.
        entrypoint: Custom ``ENTRYPOINT`` directive
            (e.g. ``"flowyml step-runner"``).
        tag_strategy: Image tagging strategy.  One of ``content-hash``,
            ``git-sha``, ``latest``, or ``semver``.
        replicate_local_env: Freeze the local Python environment via
            ``pip freeze`` and replicate it inside the container.
        exclude_patterns: Additional glob patterns for ``.dockerignore``.
    """

    # ── Core image settings ───────────────────────────────────────────
    image: str | None = None
    dockerfile: str | None = None
    build_context: str = "."
    requirements: list[str] | None = None
    base_image: str = "python:3.11-slim"
    env_vars: dict[str, str] = field(default_factory=dict)
    build_args: dict[str, str] = field(default_factory=dict)
    command: list[str] | None = None
    args: list[str] | None = None

    # ── System packages ───────────────────────────────────────────────
    apt_packages: list[str] | None = None

    # ── Platform targeting ────────────────────────────────────────────
    platform: str = "linux/amd64"

    # ── GPU support ───────────────────────────────────────────────────
    gpu_enabled: bool = False
    cuda_version: str | None = None

    # ── Dependency manager control ────────────────────────────────────
    requirements_file: str | None = None
    use_poetry: bool = False
    use_uv: bool = True
    use_conda: bool = False
    conda_file: str | None = None

    # ── Build optimisation ────────────────────────────────────────────
    multi_stage: bool = True
    cache_pip: bool = True

    # ── Entrypoint ────────────────────────────────────────────────────
    entrypoint: str | None = None

    # ── Image tagging strategy ────────────────────────────────────────
    tag_strategy: str = "content-hash"

    # ── Local env replication ─────────────────────────────────────────
    replicate_local_env: bool = False

    # ── .dockerignore patterns ────────────────────────────────────────
    exclude_patterns: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a plain dictionary.

        Returns:
            A dictionary representation suitable for serialisation.
        """
        return {
            "image": self.image,
            "dockerfile": self.dockerfile,
            "build_context": self.build_context,
            "requirements": self.requirements or [],
            "base_image": self.base_image,
            "env_vars": self.env_vars,
            "build_args": self.build_args,
            "command": self.command,
            "args": self.args,
            "apt_packages": self.apt_packages or [],
            "platform": self.platform,
            "gpu_enabled": self.gpu_enabled,
            "cuda_version": self.cuda_version,
            "requirements_file": self.requirements_file,
            "use_poetry": self.use_poetry,
            "use_uv": self.use_uv,
            "use_conda": self.use_conda,
            "conda_file": self.conda_file,
            "multi_stage": self.multi_stage,
            "cache_pip": self.cache_pip,
            "entrypoint": self.entrypoint,
            "tag_strategy": self.tag_strategy,
            "replicate_local_env": self.replicate_local_env,
            "exclude_patterns": self.exclude_patterns or [],
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

    def get_run_logs(self, run_id: str) -> str:
        """Get logs for a pipeline run.

        Args:
            run_id: The run identifier.

        Returns:
            String containing the logs.
        """
        return "Logs not available for this orchestrator."


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

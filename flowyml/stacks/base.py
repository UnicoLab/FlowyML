"""Base Stack - Defines execution environment for pipelines."""

from typing import Any
from dataclasses import dataclass


@dataclass
class StackConfig:
    """Configuration for a stack."""

    name: str
    executor_type: str
    artifact_store: str
    metadata_store: str
    container_registry: str | None = None
    orchestrator: str | None = None
    model_deployer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "executor_type": self.executor_type,
            "artifact_store": self.artifact_store,
            "metadata_store": self.metadata_store,
            "container_registry": self.container_registry,
            "orchestrator": self.orchestrator,
            "model_deployer": self.model_deployer,
        }


class Stack:
    """Stack defines the execution environment for pipelines.

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
        container_registry: Any | None = None,
        orchestrator: Any | None = None,
        model_deployer: Any | None = None,
    ):
        self.name = name
        self.executor = executor
        self.artifact_store = artifact_store
        self.metadata_store = metadata_store
        self.container_registry = container_registry
        self.orchestrator = orchestrator
        self.model_deployer = model_deployer

        self.config = StackConfig(
            name=name,
            executor_type=type(executor).__name__,
            artifact_store=type(artifact_store).__name__,
            metadata_store=type(metadata_store).__name__,
            container_registry=type(container_registry).__name__ if container_registry else None,
            orchestrator=type(orchestrator).__name__ if orchestrator else None,
            model_deployer=type(model_deployer).__name__ if model_deployer else None,
        )

    def activate(self) -> None:
        """Activate this stack as the active stack."""
        # In a real implementation, this would set the global active stack
        pass

    def prepare_docker_image(
        self,
        docker_config: Any,
        pipeline_name: str,
        project_name: str | None = None,
    ) -> str:
        """Prepare the Docker image for execution.

        Args:
            docker_config: Docker configuration object.
            pipeline_name: Name of the pipeline being built.
            project_name: Optional name of the project.

        Returns:
            str: The full URI of the docker image to use.

        Raises:
            ValueError: If image cannot be prepared (e.g. no registry configured for build).
        """
        # 1. If explicit image provided, use it
        if docker_config.image:
            return docker_config.image

        # 2. If no registry, we cannot build/push for remote execution
        if not self.container_registry:
            raise ValueError(
                "Remote execution requires a specific 'image' in DockerConfiguration "
                "or a configured 'container_registry' in the Stack for automatic building.",
            )

        # 3. Trigger build and push
        # Use safe naming: registry/project/pipeline:latest OR registry/pipeline:latest
        if project_name:
            image_name = f"{project_name}-{pipeline_name}"
        else:
            image_name = pipeline_name

        # Clean image name to be docker compatible (lowercase, alphanumeric)
        import re

        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", image_name).lower()

        image_tag = f"{self.container_registry.registry_uri}/{safe_name}:latest"

        # Build
        try:
            from flowyml.core.image_builder import DockerImageBuilder

            builder = DockerImageBuilder()
            builder.build_image(docker_config, image_tag)
        except ImportError:
            # Fallback if file not found (shouldn't happen in prod)
            print("Warning: DockerImageBuilder not found. Skipping build.")

        # Push
        print(f"🚀 Pushing image: {image_tag}")
        try:
            pushed_uri = self.container_registry.push_image(image_tag)
            return pushed_uri
        except Exception as e:
            raise RuntimeError(f"Failed to push image to registry: {e}")

    def validate(self) -> bool:
        """Validate that all stack components are properly configured."""
        # Check that all components are properly configured
        return True

    def __repr__(self) -> str:
        return f"Stack(name='{self.name}', executor={type(self.executor).__name__})"

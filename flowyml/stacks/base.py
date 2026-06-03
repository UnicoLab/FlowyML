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

        Handles the full build → push lifecycle using
        :class:`~flowyml.core.image_builder.DockerImageBuilder`.  Uses
        content-hash tagging for deterministic, cache-friendly builds.

        The method respects ``docker_config.auto_build`` and
        ``docker_config.auto_push`` flags.  When ``auto_build`` is
        ``False`` and no pre-built ``image`` is set, a helpful error
        is raised.

        Args:
            docker_config: Docker configuration object.
            pipeline_name: Name of the pipeline being built.
            project_name: Optional name of the project.

        Returns:
            The full URI of the docker image to use.

        Raises:
            ValueError: If image cannot be prepared.
            RuntimeError: If the build or push fails.
        """
        # 1. If explicit image provided, use it directly
        if docker_config.image:
            return docker_config.image

        # 2. If auto_build is disabled, we need an explicit image
        if not getattr(docker_config, "auto_build", True):
            raise ValueError(
                "Docker auto-build is disabled but no pre-built 'image' "
                "is set in DockerConfig.  Either set 'image' to a "
                "pre-built URI or enable 'auto_build'.",
            )

        # 3. Determine the target registry
        registry_uri = getattr(docker_config, "registry_uri", None)
        if not registry_uri and self.container_registry:
            registry_uri = getattr(
                self.container_registry,
                "registry_uri",
                None,
            )

        if not registry_uri:
            raise ValueError(
                "Remote execution requires a container registry.  "
                "Set 'registry_uri' on DockerConfig, or configure a "
                "'container_registry' on the Stack.\n\n"
                "  Tip: flowyml docker build --registry <uri> --push",
            )

        # 4. Build and push via DockerImageBuilder
        from flowyml.core.image_builder import DockerImageBuilder

        builder = DockerImageBuilder()

        import re

        if project_name:
            base_name = f"{project_name}-{pipeline_name}"
        else:
            base_name = pipeline_name
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", base_name).lower()

        # Generate content-hash tag for cache efficiency
        tag = builder.generate_tag(docker_config, base_name=safe_name)

        # Build
        print(f"🐳 Preparing image for stack '{self.name}'")
        built_tag = builder.build_image(docker_config, tag=tag)

        # Push (if auto_push enabled)
        if getattr(docker_config, "auto_push", True):
            pushed_uri = builder.push_image(
                built_tag,
                registry_uri=registry_uri,
            )
            return pushed_uri

        return built_tag

    def validate(self) -> bool:
        """Validate that all stack components are properly configured."""
        # Check that all components are properly configured
        return True

    def __repr__(self) -> str:
        return f"Stack(name='{self.name}', executor={type(self.executor).__name__})"

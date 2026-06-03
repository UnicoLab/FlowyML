"""Project-level configuration for the Enterprise Stack Registry.

Reads ``flowyml.yaml`` project files and provides ``ProjectConfig``,
``EnvironmentConfig``, ``DefaultsConfig``, ``ProjectInfo``, and
``RegistryConfig`` used by the stack resolver to determine which stack
to use for a given environment.

Configuration file format::

    project:
      name: churn-modeling
      owner: ml-platform-team

    defaults:
      stack: local_dev
      environment: dev

    environments:
      dev:
        stack: local_dev
      staging:
        stack: aml_cpu_small
        requireLock: true
      production:
        stack: aml_gpu_large
        requireLock: true
        requirePolicyValidation: true

    registry:
      sources:
        - github://my-org/flowyml-stacks@v1

Example::

    from flowyml.stacks.enterprise.project_config import (
        load_project_config,
        resolve_environment,
    )

    config = load_project_config()
    env = resolve_environment(config, "production")
"""

from __future__ import annotations

import logging
from typing import Any
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from flowyml.stacks.enterprise.exceptions import StackValidationError

logger = logging.getLogger(__name__)

__all__ = [
    "EnvironmentConfig",
    "DefaultsConfig",
    "ProjectInfo",
    "RegistryConfig",
    "DockerDefaults",
    "ProjectConfig",
    "load_project_config",
    "resolve_environment",
]

# Maximum number of parent directories to search when discovering
# ``flowyml.yaml`` from the current working directory.
_MAX_SEARCH_DEPTH = 5


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class EnvironmentConfig(BaseModel):
    """Configuration for a single deployment environment.

    Attributes:
        stack: Stack name or URI to use in this environment.
        require_lock: When ``True``, a valid lock file entry must exist
            for the stack before execution is allowed.
        require_policy_validation: When ``True``, the policy engine must
            run and pass before execution.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    stack: str
    require_lock: bool = Field(
        alias="requireLock",
        default=False,
        description="Whether a lock file entry is required.",
    )
    require_policy_validation: bool = Field(
        alias="requirePolicyValidation",
        default=False,
        description="Whether policy validation must pass.",
    )


class DefaultsConfig(BaseModel):
    """Default values applied when no explicit override is given.

    Attributes:
        stack: Default stack name if no environment-specific stack is set.
        environment: Default environment name when none is specified.
    """

    model_config = ConfigDict(extra="forbid")

    stack: str = Field(
        default="local_dev",
        description="Default stack name.",
    )
    environment: str = Field(
        default="dev",
        description="Default environment name.",
    )


class ProjectInfo(BaseModel):
    """Basic metadata about the FlowyML project.

    Attributes:
        name: Unique project identifier.
        owner: Team or individual responsible for the project.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Unique project identifier.")
    owner: str = Field(
        default="",
        description="Team or individual responsible for this project.",
    )


class RegistryConfig(BaseModel):
    """Registry section of the project configuration.

    Attributes:
        sources: Ordered list of source URIs to search for stacks.
    """

    model_config = ConfigDict(extra="forbid")

    sources: list[str] = Field(
        default_factory=list,
        description="Ordered list of registry source URIs.",
    )


class DockerDefaults(BaseModel):
    """Docker configuration defaults for the project.

    These are applied as defaults when building Docker images,
    unless overridden by the stack definition or CLI flags.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    base_image: str | None = Field(
        alias="baseImage",
        default=None,
        description="Default Docker base image.",
    )
    dependency_manager: str | None = Field(
        alias="dependencyManager",
        default=None,
        description="Default dependency manager: auto, pip, uv, poetry, conda, pipenv.",
    )
    gpu: bool = Field(
        default=False,
        description="Enable GPU support by default.",
    )
    multi_stage: bool = Field(
        alias="multiStage",
        default=True,
        description="Use multi-stage Docker builds.",
    )
    auto_build: bool = Field(
        alias="autoBuild",
        default=True,
        description="Automatically build images for remote execution.",
    )
    auto_push: bool = Field(
        alias="autoPush",
        default=True,
        description="Automatically push images after build.",
    )
    registry_uri: str | None = Field(
        alias="registryUri",
        default=None,
        description="Default container registry URI.",
    )
    health_check: str | None = Field(
        alias="healthCheck",
        default=None,
        description="Default HEALTHCHECK CMD.",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Default OCI image labels.",
    )
    exclude_patterns: list[str] = Field(
        alias="excludePatterns",
        default_factory=list,
        description="Default .dockerignore patterns.",
    )


# ---------------------------------------------------------------------------
# Top-level project config
# ---------------------------------------------------------------------------


class ProjectConfig(BaseModel):
    """FlowyML project configuration loaded from ``flowyml.yaml``.

    This is the single source of truth for project-level settings: which
    stacks to use per environment, where to resolve stacks from, and
    what governance controls (locking, policy validation) are enforced.

    Example ``flowyml.yaml``::

        project:
          name: churn-modeling
          owner: ml-platform-team
        defaults:
          stack: local_dev
          environment: dev
        environments:
          dev:
            stack: local_dev
          production:
            stack: aml_gpu_large
            requireLock: true
            requirePolicyValidation: true
        registry:
          sources:
            - github://my-org/flowyml-stacks@v1

    Attributes:
        project: Basic project metadata.
        defaults: Default values for stack and environment.
        environments: Per-environment stack and governance settings.
        registry: Registry sources for stack resolution.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    project: ProjectInfo
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    environments: dict[str, EnvironmentConfig] = Field(default_factory=dict)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    docker: DockerDefaults = Field(
        default_factory=DockerDefaults,
        description="Docker build defaults for the project.",
    )

    def to_docker_config(self) -> Any:
        """Convert project docker defaults to a DockerConfig.

        Maps the high-level :class:`DockerDefaults` into a
        :class:`~flowyml.stacks.components.DockerConfig` instance,
        translating ``dependency_manager`` strings into the
        corresponding boolean flags.

        Returns:
            A fully populated ``DockerConfig`` ready for use by the
            Docker build pipeline.
        """
        from flowyml.stacks.components import DockerConfig

        kwargs: dict[str, Any] = {}
        d = self.docker

        if d.base_image:
            kwargs["base_image"] = d.base_image
        if d.dependency_manager == "poetry":
            kwargs["use_poetry"] = True
        elif d.dependency_manager == "conda":
            kwargs["use_conda"] = True
        elif d.dependency_manager == "pipenv":
            kwargs["use_pipenv"] = True
        elif d.dependency_manager == "uv":
            kwargs["use_uv"] = True
        elif d.dependency_manager == "pip":
            kwargs["use_uv"] = False

        kwargs["gpu_enabled"] = d.gpu
        kwargs["multi_stage"] = d.multi_stage
        kwargs["auto_build"] = d.auto_build
        kwargs["auto_push"] = d.auto_push

        if d.registry_uri:
            kwargs["registry_uri"] = d.registry_uri
        if d.health_check:
            kwargs["health_check"] = d.health_check
        if d.labels:
            kwargs["labels"] = d.labels
        if d.exclude_patterns:
            kwargs["exclude_patterns"] = d.exclude_patterns

        return DockerConfig(**kwargs)


# ---------------------------------------------------------------------------
# Loader functions
# ---------------------------------------------------------------------------


def load_project_config(path: str | None = None) -> ProjectConfig | None:
    """Load the FlowyML project configuration.

    When *path* is given, the file at that location is loaded directly.
    Otherwise, the function searches for ``flowyml.yaml`` starting from
    the current working directory and walking up to 5 parent directories.

    Args:
        path: Explicit path to the project config file.  When ``None``,
            automatic discovery is performed.

    Returns:
        A validated ``ProjectConfig``, or ``None`` if no config file was
        found during automatic discovery.

    Raises:
        FileNotFoundError: If *path* is given but the file does not exist.
        StackValidationError: If the YAML content is invalid.
    """
    if path is not None:
        return _load_from_path(Path(path))

    return _discover_config()


def resolve_environment(
    config: ProjectConfig,
    env_name: str,
) -> EnvironmentConfig:
    """Resolve the ``EnvironmentConfig`` for a named environment.

    If *env_name* is not defined in the project configuration, a default
    ``EnvironmentConfig`` is returned using the project's default stack.

    Args:
        config: The loaded project configuration.
        env_name: Name of the environment to resolve (e.g. ``"production"``).

    Returns:
        The ``EnvironmentConfig`` for *env_name*, or a synthesised default
        if the environment is not explicitly configured.
    """
    env = config.environments.get(env_name)
    if env is not None:
        return env

    logger.debug(
        "Environment '%s' not found in project config; using defaults.",
        env_name,
    )
    return EnvironmentConfig(stack=config.defaults.stack)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_from_path(file_path: Path) -> ProjectConfig:
    """Load and validate a project config from an explicit path.

    Args:
        file_path: Path to the ``flowyml.yaml`` file.

    Returns:
        Validated ``ProjectConfig``.

    Raises:
        FileNotFoundError: If the file does not exist.
        StackValidationError: If parsing or validation fails.
    """
    if not file_path.exists():
        raise FileNotFoundError(
            f"Project config not found: {file_path}",
        )

    return _parse_yaml(file_path)


def _discover_config() -> ProjectConfig | None:
    """Search for ``flowyml.yaml`` in the directory tree.

    Walks from the current working directory upward through at most
    :data:`_MAX_SEARCH_DEPTH` parent directories.

    Returns:
        Validated ``ProjectConfig``, or ``None`` if no file was found.
    """
    current = Path.cwd()
    searched: list[Path] = [current]

    # Check CWD first, then up to _MAX_SEARCH_DEPTH parents.
    candidate = current / "flowyml.yaml"
    if candidate.exists():
        logger.debug("Discovered project config at %s", candidate)
        return _parse_yaml(candidate)

    for depth, parent in enumerate(current.parents):
        if depth >= _MAX_SEARCH_DEPTH:
            break
        searched.append(parent)
        candidate = parent / "flowyml.yaml"
        if candidate.exists():
            logger.debug("Discovered project config at %s", candidate)
            return _parse_yaml(candidate)

    logger.debug(
        "No flowyml.yaml found in %d directories: %s",
        len(searched),
        [str(p) for p in searched],
    )
    return None


def _parse_yaml(file_path: Path) -> ProjectConfig:
    """Parse and validate a YAML file into a ``ProjectConfig``.

    Args:
        file_path: Path to the YAML file.

    Returns:
        Validated ``ProjectConfig``.

    Raises:
        StackValidationError: If the content is not valid YAML or does
            not conform to the ``ProjectConfig`` schema.
    """
    try:
        with open(file_path) as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise StackValidationError(
            stack_name=str(file_path),
            field="(root)",
            reason=f"Failed to parse YAML: {exc}",
            suggestion=("Ensure the file contains valid YAML syntax. " "Use a YAML linter to find formatting errors."),
        ) from exc

    if not isinstance(data, dict):
        raise StackValidationError(
            stack_name=str(file_path),
            field="(root)",
            reason=("Project config file must contain a YAML mapping, " "not a scalar or list."),
            suggestion=("Ensure the file starts with 'project:' and contains " "the expected structure."),
        )

    try:
        return ProjectConfig.model_validate(data)
    except Exception as exc:
        project_name = (
            data.get("project", {}).get("name", str(file_path))
            if isinstance(data.get("project"), dict)
            else str(file_path)
        )
        raise StackValidationError(
            stack_name=project_name,
            reason=str(exc),
            suggestion=(
                "Check the project config against the expected schema. "
                "Refer to the FlowyML documentation for valid "
                "flowyml.yaml examples."
            ),
        ) from exc

"""Pydantic v2 models for enterprise stack definitions.

This module provides the strongly-typed schema for declarative stack
definitions that platform teams create in YAML and data scientists consume
via the Enterprise Stack Registry.

Example YAML::

    apiVersion: flowyml.io/v1
    kind: Stack
    metadata:
      name: aml_cpu_small
      version: 1.2.0
      description: Approved AzureML CPU stack
      owner: ml-platform-team
      tags: [azureml, cpu, production]
    spec:
      backend: azureml
      runtime:
        pythonVersion: "3.11"
        baseImage: "myregistry.azurecr.io/flowyml/sklearn:1.2.0"
      compute:
        type: cpu
        size: Standard_DS3_v2
        region: francecentral
      ...
"""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_VERSION = "flowyml.io/v1"
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$",
)

SUPPORTED_BACKENDS = frozenset(
    {
        "local",
        "azureml",
        "kubernetes",
        "ray",
        "databricks",
        "gcp",
        "aws",
        "custom",
    },
)

SUPPORTED_COMPUTE_TYPES = frozenset({"cpu", "gpu", "tpu"})

SUPPORTED_SECRET_PROVIDERS = frozenset(
    {
        "azure_key_vault",
        "aws_secrets_manager",
        "gcp_secret_manager",
        "hashicorp_vault",
        "env",
        "local",
    },
)

SUPPORTED_ARTIFACT_STORES = frozenset(
    {
        "local",
        "azure_blob",
        "s3",
        "gcs",
        "minio",
    },
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StackKind(str, Enum):
    """Kind field values for stack-related documents."""

    STACK = "Stack"
    STACK_LOCK = "StackLock"
    STACK_REGISTRY = "StackRegistry"


# ---------------------------------------------------------------------------
# Sub-models for StackSpec
# ---------------------------------------------------------------------------


class RuntimeConfig(BaseModel):
    """Runtime environment configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    python_version: str = Field(
        alias="pythonVersion",
        default="3.11",
        description="Python version for the execution environment.",
    )
    base_image: str | None = Field(
        alias="baseImage",
        default=None,
        description="Docker base image URI.",
    )
    dependency_lock_file: str | None = Field(
        alias="dependencyLockFile",
        default=None,
        description="Path to dependency lock file (e.g. requirements.lock).",
    )
    dependency_manager: str | None = Field(
        alias="dependencyManager",
        default=None,
        description="Dependency manager to use: pip, uv, poetry, conda, pipenv. Auto-detected if None.",
    )
    dependency_file: str | None = Field(
        alias="dependencyFile",
        default=None,
        description="Explicit dependency file path (e.g. requirements.txt, Pipfile).",
    )
    dockerfile: str | None = Field(
        alias="dockerfile",
        default=None,
        description="Path to a custom Dockerfile.",
    )
    apt_packages: list[str] = Field(
        alias="aptPackages",
        default_factory=list,
        description="System packages to install via apt-get.",
    )
    gpu_enabled: bool = Field(
        alias="gpuEnabled",
        default=False,
        description="Enable GPU/CUDA support in the container image.",
    )
    cuda_version: str | None = Field(
        alias="cudaVersion",
        default=None,
        description="CUDA version when GPU is enabled (e.g. '12.4').",
    )
    auto_build: bool = Field(
        alias="autoBuild",
        default=True,
        description="Automatically build Docker image for remote execution.",
    )
    auto_push: bool = Field(
        alias="autoPush",
        default=True,
        description="Automatically push Docker image after build.",
    )
    multi_stage: bool = Field(
        alias="multiStage",
        default=True,
        description="Use multi-stage Docker builds for smaller images.",
    )
    health_check: str | None = Field(
        alias="healthCheck",
        default=None,
        description="Docker HEALTHCHECK CMD for the container.",
    )
    entrypoint: str | None = Field(
        alias="entrypoint",
        default=None,
        description="Custom container ENTRYPOINT.",
    )
    labels: dict[str, str] = Field(
        alias="labels",
        default_factory=dict,
        description="OCI image labels.",
    )

    @field_validator("python_version")
    @classmethod
    def validate_python_version(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+(\.\d+)?$", v):
            raise ValueError(
                f"Invalid Python version '{v}'. " f"Expected format: '3.11' or '3.11.5'.",
            )
        return v


class ComputeConfig(BaseModel):
    """Compute resource configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: str = Field(  # noqa: A003
        default="cpu",
        description="Compute type: cpu, gpu, or tpu.",
    )
    size: str | None = Field(
        default=None,
        description="Machine size (e.g. Standard_DS3_v2, n1-standard-4).",
    )
    min_instances: int = Field(
        alias="minInstances",
        default=0,
        ge=0,
        description="Minimum number of compute instances.",
    )
    max_instances: int = Field(
        alias="maxInstances",
        default=1,
        ge=1,
        description="Maximum number of compute instances.",
    )
    region: str | None = Field(
        default=None,
        description="Cloud region for compute placement.",
    )

    @field_validator("type")
    @classmethod
    def validate_compute_type(cls, v: str) -> str:
        if v not in SUPPORTED_COMPUTE_TYPES:
            raise ValueError(
                f"Unsupported compute type '{v}'. " f"Supported: {', '.join(sorted(SUPPORTED_COMPUTE_TYPES))}.",
            )
        return v

    @model_validator(mode="after")
    def validate_instance_range(self) -> ComputeConfig:
        if self.min_instances > self.max_instances:
            raise ValueError(
                f"minInstances ({self.min_instances}) cannot exceed " f"maxInstances ({self.max_instances}).",
            )
        return self


class StorageConfig(BaseModel):
    """Artifact storage configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    artifact_store: str = Field(
        alias="artifactStore",
        default="local",
        description="Artifact store type.",
    )
    uri: str | None = Field(
        default=None,
        description="Storage URI (e.g. az://bucket/path, s3://bucket/path).",
    )

    @field_validator("artifact_store")
    @classmethod
    def validate_artifact_store(cls, v: str) -> str:
        if v not in SUPPORTED_ARTIFACT_STORES:
            raise ValueError(
                f"Unsupported artifact store '{v}'. " f"Supported: {', '.join(sorted(SUPPORTED_ARTIFACT_STORES))}.",
            )
        return v


class SecretsConfig(BaseModel):
    """Secrets provider configuration."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(default="env", description="Secrets provider type.")
    scope: str | None = Field(default=None, description="Secrets scope or namespace.")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in SUPPORTED_SECRET_PROVIDERS:
            raise ValueError(
                f"Unsupported secrets provider '{v}'. " f"Supported: {', '.join(sorted(SUPPORTED_SECRET_PROVIDERS))}.",
            )
        return v


class ObservabilityConfig(BaseModel):
    """Observability settings."""

    model_config = ConfigDict(extra="forbid")

    logs: bool = Field(default=True, description="Enable log collection.")
    metrics: bool = Field(default=True, description="Enable metrics collection.")
    traces: bool = Field(default=False, description="Enable distributed tracing.")


class PolicyConfig(BaseModel):
    """Policy constraints for execution governance."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    allow_external_network: bool = Field(
        alias="allowExternalNetwork",
        default=True,
        description="Whether external network access is allowed.",
    )
    allow_custom_docker_image: bool = Field(
        alias="allowCustomDockerImage",
        default=True,
        description="Whether custom Docker images are allowed.",
    )
    allowed_python_packages: list[str] = Field(
        alias="allowedPythonPackages",
        default_factory=list,
        description="Allowlist of Python packages. Empty means all allowed.",
    )
    denied_python_packages: list[str] = Field(
        alias="deniedPythonPackages",
        default_factory=list,
        description="Denylist of Python packages.",
    )
    max_runtime_minutes: int | None = Field(
        alias="maxRuntimeMinutes",
        default=None,
        ge=1,
        description="Maximum pipeline runtime in minutes.",
    )
    max_estimated_cost_usd: float | None = Field(
        alias="maxEstimatedCostUsd",
        default=None,
        ge=0,
        description="Maximum estimated cost in USD.",
    )
    require_signed_stack: bool = Field(
        alias="requireSignedStack",
        default=False,
        description="Whether stack signature verification is required.",
    )

    @model_validator(mode="after")
    def validate_package_lists(self) -> PolicyConfig:
        overlap = set(self.allowed_python_packages) & set(self.denied_python_packages)
        if overlap:
            raise ValueError(
                f"Packages appear in both allowed and denied lists: "
                f"{', '.join(sorted(overlap))}. "
                f"A package cannot be both allowed and denied.",
            )
        return self


class PermissionsConfig(BaseModel):
    """Access control configuration."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    allowed_groups: list[str] = Field(
        alias="allowedGroups",
        default_factory=list,
        description="Groups allowed to use this stack. Empty means all.",
    )
    allowed_projects: list[str] = Field(
        alias="allowedProjects",
        default_factory=list,
        description="Projects allowed to use this stack. Empty means all.",
    )


class SignatureConfig(BaseModel):
    """Stack signature verification configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False, description="Whether signature verification is enabled.")
    provider: str = Field(default="cosign", description="Signature verification provider.")


class SecurityConfig(BaseModel):
    """Security configuration."""

    model_config = ConfigDict(extra="forbid")

    signature: SignatureConfig = Field(
        default_factory=SignatureConfig,
        description="Signature verification settings.",
    )


# ---------------------------------------------------------------------------
# Top-level models
# ---------------------------------------------------------------------------


class StackMetadata(BaseModel):
    """Metadata for a stack definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Unique stack name. Must start with a letter.",
    )
    version: str = Field(
        ...,
        description="Semantic version (e.g. 1.2.0).",
    )
    description: str = Field(
        default="",
        description="Human-readable description.",
    )
    owner: str = Field(
        default="",
        description="Team or person who owns this stack.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and discovery.",
    )

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        if not SEMVER_PATTERN.match(v):
            raise ValueError(
                f"Invalid semantic version '{v}'. " f"Expected format: MAJOR.MINOR.PATCH (e.g. 1.2.0, 2.0.0-beta.1).",
            )
        return v


class StackSpec(BaseModel):
    """Specification of a stack's execution environment."""

    model_config = ConfigDict(extra="forbid")

    backend: str = Field(
        ...,
        description="Backend execution platform.",
    )
    runtime: RuntimeConfig = Field(
        default_factory=RuntimeConfig,
        description="Runtime environment configuration.",
    )
    compute: ComputeConfig = Field(
        default_factory=ComputeConfig,
        description="Compute resource configuration.",
    )
    storage: StorageConfig = Field(
        default_factory=StorageConfig,
        description="Artifact storage configuration.",
    )
    secrets: SecretsConfig = Field(
        default_factory=SecretsConfig,
        description="Secrets provider configuration.",
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability settings.",
    )
    policies: PolicyConfig = Field(
        default_factory=PolicyConfig,
        description="Policy constraints.",
    )
    permissions: PermissionsConfig = Field(
        default_factory=PermissionsConfig,
        description="Access control.",
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="Security settings.",
    )

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, v: str) -> str:
        if v not in SUPPORTED_BACKENDS:
            raise ValueError(
                f"Unsupported backend '{v}'. " f"Supported: {', '.join(sorted(SUPPORTED_BACKENDS))}.",
            )
        return v


class StackDefinition(BaseModel):
    """Complete stack definition loaded from YAML.

    This is the primary model for enterprise stack definitions. It represents
    the full declarative specification that platform teams create and data
    scientists consume.

    Example::

        stack = StackDefinition.from_yaml("stacks/aml_cpu_small.yaml")
        pipeline.run(stack=stack.to_stack())
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_version: str = Field(
        alias="apiVersion",
        default=API_VERSION,
        description="API version for schema compatibility.",
    )
    kind: str = Field(
        default=StackKind.STACK.value,
        description="Document kind.",
    )
    metadata: StackMetadata = Field(
        ...,
        description="Stack metadata.",
    )
    spec: StackSpec = Field(
        ...,
        description="Stack specification.",
    )

    @field_validator("api_version")
    @classmethod
    def validate_api_version(cls, v: str) -> str:
        if v != API_VERSION:
            raise ValueError(
                f"Unsupported apiVersion '{v}'. Expected '{API_VERSION}'.",
            )
        return v

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v != StackKind.STACK.value:
            raise ValueError(
                f"Invalid kind '{v}' for StackDefinition. Expected 'Stack'.",
            )
        return v

    # --- Convenience properties ------------------------------------------------

    @property
    def name(self) -> str:
        """Stack name shortcut."""
        return self.metadata.name

    @property
    def version(self) -> str:
        """Stack version shortcut."""
        return self.metadata.version

    @property
    def backend(self) -> str:
        """Backend shortcut."""
        return self.spec.backend

    # --- Methods ---------------------------------------------------------------

    def compute_digest(self) -> str:
        """Compute a SHA-256 digest of the normalized stack definition.

        The digest is deterministic: same content always produces the same
        hash regardless of field ordering in the source YAML.

        Returns:
            SHA-256 hex digest string prefixed with ``sha256:``.
        """
        # Use model_dump with sorted keys for deterministic serialization
        data = self.model_dump(mode="json", by_alias=True, exclude_none=True)
        normalized = yaml.safe_dump(data, sort_keys=True, default_flow_style=False)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def to_docker_config(self) -> Any:
        """Convert the stack definition's runtime config to a DockerConfig.

        This creates a DockerConfig instance that reflects the enterprise
        stack's runtime settings, enabling seamless Docker image builds
        from enterprise stack definitions.

        Returns:
            A DockerConfig instance, or None if no runtime config.
        """
        from flowyml.stacks.components import DockerConfig

        runtime = self.spec.runtime
        if runtime is None:
            return None

        kwargs: dict[str, Any] = {}

        if runtime.base_image:
            kwargs["base_image"] = runtime.base_image
        if runtime.dependency_lock_file:
            kwargs["requirements_file"] = runtime.dependency_lock_file
        if runtime.dockerfile:
            kwargs["dockerfile"] = runtime.dockerfile
        if runtime.apt_packages:
            kwargs["apt_packages"] = runtime.apt_packages
        if runtime.gpu_enabled:
            kwargs["gpu_enabled"] = True
        if runtime.cuda_version:
            kwargs["cuda_version"] = runtime.cuda_version
        if runtime.health_check:
            kwargs["health_check"] = runtime.health_check
        if runtime.entrypoint:
            kwargs["entrypoint"] = runtime.entrypoint
        if runtime.labels:
            kwargs["labels"] = runtime.labels
        if runtime.dependency_file:
            kwargs["requirements_file"] = runtime.dependency_file

        # Map dependency manager string to DockerConfig flags
        mgr = runtime.dependency_manager
        if mgr == "poetry":
            kwargs["use_poetry"] = True
        elif mgr == "conda":
            kwargs["use_conda"] = True
        elif mgr == "pipenv":
            kwargs["use_pipenv"] = True
        elif mgr == "uv":
            kwargs["use_uv"] = True
        elif mgr == "pip":
            kwargs["use_uv"] = False

        kwargs["auto_build"] = runtime.auto_build
        kwargs["auto_push"] = runtime.auto_push
        kwargs["multi_stage"] = runtime.multi_stage

        return DockerConfig(**kwargs)

    def to_stack(self) -> Any:
        """Convert this declarative definition to a runtime ``Stack`` instance.

        This bridges the declarative enterprise model to the existing FlowyML
        ``Stack`` class for backward-compatible execution.

        Backend mapping:
            - ``local`` → ``LocalStack``
            - ``gcp`` → ``GCPStack`` (Vertex AI + GCS + GCR)
            - ``aws`` → ``AWSStack`` (Batch/SageMaker + S3 + ECR)
            - ``azureml`` → ``AzureMLStack`` (AzureML + Blob + ACR)
            - ``kubernetes``, ``ray``, ``databricks`` → raise with guidance

        Returns:
            A ``flowyml.stacks.base.Stack`` (or subclass) instance.

        Raises:
            NotImplementedError: For backends without a Stack implementation.
        """
        backend = self.spec.backend
        compute = self.spec.compute
        storage = self.spec.storage
        _runtime = self.spec.runtime  # noqa: F841 — reserved for future base_image propagation

        # -----------------------------------------------------------
        # Local backend
        # -----------------------------------------------------------
        if backend == "local":
            from flowyml.stacks.local import LocalStack

            return LocalStack(name=self.name)

        # -----------------------------------------------------------
        # GCP / Vertex AI
        # -----------------------------------------------------------
        if backend == "gcp":
            try:
                from flowyml.stacks.gcp import GCPStack
            except ImportError as exc:
                raise ImportError(
                    "GCP stack requires google-cloud-aiplatform and "
                    "google-cloud-storage. Install with: "
                    "pip install flowyml[gcp]",
                ) from exc

            # Extract GCP-specific config from the StackDefinition
            gcp_kwargs: dict[str, Any] = {
                "name": self.name,
                "region": compute.region or "us-central1",
            }

            # Extract project_id from storage URI (gs://bucket/...) or build args
            if storage.uri and storage.uri.startswith("gs://"):
                parts = storage.uri.replace("gs://", "").split("/", 1)
                gcp_kwargs["bucket_name"] = parts[0]

            return GCPStack(**gcp_kwargs)

        # -----------------------------------------------------------
        # AWS (Batch / SageMaker)
        # -----------------------------------------------------------
        if backend == "aws":
            try:
                from flowyml.stacks.aws import AWSStack
            except ImportError as exc:
                raise ImportError(
                    "AWS stack requires boto3. Install with: " "pip install flowyml[aws]",
                ) from exc

            aws_kwargs: dict[str, Any] = {
                "name": self.name,
                "region": compute.region or "us-east-1",
            }

            # Extract bucket from storage URI (s3://bucket/...)
            if storage.uri and storage.uri.startswith("s3://"):
                parts = storage.uri.replace("s3://", "").split("/", 1)
                aws_kwargs["bucket_name"] = parts[0]

            return AWSStack(**aws_kwargs)

        # -----------------------------------------------------------
        # Azure ML
        # -----------------------------------------------------------
        if backend == "azureml":
            try:
                from flowyml.stacks.azure import AzureMLStack
            except ImportError as exc:
                raise ImportError(
                    "AzureML stack requires azure-ai-ml. Install with: " "pip install flowyml[azure]",
                ) from exc

            azure_kwargs: dict[str, Any] = {
                "name": self.name,
            }

            # Map enterprise spec fields to AzureMLStack constructor params
            if compute.target:
                azure_kwargs["compute"] = compute.target

            return AzureMLStack(**azure_kwargs)

        # -----------------------------------------------------------
        # Not yet supported backends
        # -----------------------------------------------------------
        if backend in ("kubernetes", "ray", "databricks", "custom"):
            # Create a basic stack with local executor as a fallback.
            # Enterprise BackendAdapters can handle actual submission.
            from flowyml.stacks.base import Stack
            from flowyml.core.executor import LocalExecutor
            from flowyml.storage.artifacts import LocalArtifactStore
            from flowyml.storage.metadata import SQLiteMetadataStore

            import logging

            logging.getLogger(__name__).warning(
                "Backend '%s' does not have a dedicated Stack class yet. "
                "Creating a local fallback stack. Use a BackendAdapter for "
                "actual remote execution.",
                backend,
            )

            return Stack(
                name=self.name,
                executor=LocalExecutor(),
                artifact_store=LocalArtifactStore(".flowyml/artifacts"),
                metadata_store=SQLiteMetadataStore(".flowyml/metadata.db"),
            )

        # Unknown backend — should never reach here due to validator
        raise ValueError(f"Unknown backend: '{backend}'")

    @classmethod
    def from_yaml(cls, path: str) -> StackDefinition:
        """Load a stack definition from a YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            Validated StackDefinition.

        Raises:
            StackValidationError: If the YAML is invalid.
            FileNotFoundError: If the file doesn't exist.
        """
        from pathlib import Path as PathLib

        from flowyml.stacks.enterprise.exceptions import StackValidationError

        file_path = PathLib(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Stack definition file not found: {path}")

        with open(file_path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise StackValidationError(
                stack_name=str(path),
                field="(root)",
                reason="YAML file must contain a mapping, not a scalar or list.",
                suggestion="Ensure the file starts with 'apiVersion:' and 'kind:'.",
            )

        try:
            return cls.model_validate(data)
        except Exception as e:
            # Extract useful info from Pydantic validation errors
            name = data.get("metadata", {}).get("name", str(path))
            raise StackValidationError(
                stack_name=name,
                reason=str(e),
                suggestion="Check the stack definition against the schema documentation.",
            ) from e

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StackDefinition:
        """Create a StackDefinition from a dictionary.

        Args:
            data: Dictionary matching the stack YAML schema.

        Returns:
            Validated StackDefinition.
        """
        return cls.model_validate(data)


# ---------------------------------------------------------------------------
# Stack Reference (lightweight pointer to a stack)
# ---------------------------------------------------------------------------


class StackReference(BaseModel):
    """Lightweight reference to a stack, used in listings and indexes."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Stack name.")
    version: str | None = Field(default=None, description="Stack version.")
    source: str | None = Field(default=None, description="Source URI.")
    path: str | None = Field(default=None, description="File path within source.")


# ---------------------------------------------------------------------------
# Stack Lock
# ---------------------------------------------------------------------------


class StackLockEntry(BaseModel):
    """A single resolved stack entry in the lock file."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    source: str = Field(..., description="Source URI where the stack was resolved from.")
    commit: str | None = Field(default=None, description="Git commit hash (for Git sources).")
    digest: str = Field(..., description="SHA-256 digest of the stack definition.")
    resolved_at: str = Field(
        ...,
        alias="resolvedAt",
        description="ISO 8601 timestamp when the stack was resolved.",
    )


class StackLockRuntime(BaseModel):
    """Runtime section of the lock file."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    python_version: str | None = Field(
        alias="pythonVersion",
        default=None,
        description="Locked Python version.",
    )
    dependency_digest: str | None = Field(
        alias="dependencyDigest",
        default=None,
        description="Digest of dependency lock file.",
    )


class StackLockPolicies(BaseModel):
    """Policies section of the lock file."""

    model_config = ConfigDict(extra="forbid")

    digest: str | None = Field(default=None, description="Digest of policy configuration.")


class StackLock(BaseModel):
    """Lock file model for reproducible stack resolution.

    Default file: ``flowyml.lock``

    Example::

        apiVersion: flowyml.io/v1
        kind: StackLock
        project: churn-modeling
        resolvedStacks:
          aml_cpu_small:
            source: github://my-org/flowyml-stacks@v1.2.0
            commit: "abc123..."
            digest: "sha256:..."
            resolvedAt: "2026-06-03T10:00:00Z"
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_version: str = Field(
        alias="apiVersion",
        default=API_VERSION,
    )
    kind: str = Field(default=StackKind.STACK_LOCK.value)
    project: str = Field(..., description="Project name.")
    resolved_stacks: dict[str, StackLockEntry] = Field(
        alias="resolvedStacks",
        default_factory=dict,
        description="Map of stack name to resolved lock entry.",
    )
    runtime: StackLockRuntime = Field(
        default_factory=StackLockRuntime,
        description="Runtime lock information.",
    )
    policies: StackLockPolicies = Field(
        default_factory=StackLockPolicies,
        description="Policy lock information.",
    )

    @classmethod
    def from_yaml(cls, path: str) -> StackLock:
        """Load a lock file from YAML."""
        from pathlib import Path as PathLib

        file_path = PathLib(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Lock file not found: {path}")

        with open(file_path) as f:
            data = yaml.safe_load(f)

        return cls.model_validate(data)

    def to_yaml(self, path: str) -> None:
        """Save the lock file to YAML."""
        data = self.model_dump(mode="json", by_alias=True, exclude_none=True)
        with open(path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


# ---------------------------------------------------------------------------
# Registry Index
# ---------------------------------------------------------------------------


class RegistryIndexEntry(BaseModel):
    """Entry in a registry index file."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Stack name.")
    path: str = Field(..., description="Relative path to stack YAML file.")


class RegistryIndexMetadata(BaseModel):
    """Metadata for a registry index."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Registry name.")
    version: str = Field(default="1.0.0", description="Registry version.")


class RegistryIndex(BaseModel):
    """Registry index file that maps stack names to file paths.

    Example::

        apiVersion: flowyml.io/v1
        kind: StackRegistry
        metadata:
          name: company-approved-stacks
          version: 1.0.0
        stacks:
          - name: aml_cpu_small
            path: stacks/aml_cpu_small.yaml
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_version: str = Field(alias="apiVersion", default=API_VERSION)
    kind: str = Field(default=StackKind.STACK_REGISTRY.value)
    metadata: RegistryIndexMetadata = Field(...)
    stacks: list[RegistryIndexEntry] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> RegistryIndex:
        """Load a registry index from YAML."""
        from pathlib import Path as PathLib

        file_path = PathLib(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Registry index not found: {path}")

        with open(file_path) as f:
            data = yaml.safe_load(f)

        return cls.model_validate(data)

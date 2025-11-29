"""Pydantic schemas and validation utilities for flowyml."""

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class CacheStrategy(str, Enum):
    """Cache strategy options."""

    CODE_HASH = "code_hash"
    INPUT_HASH = "input_hash"
    SEMANTIC = "semantic"
    CUSTOM = "custom"
    NONE = "none"


class ResourceRequirements(BaseModel):
    """Resource requirements for step execution."""

    model_config = ConfigDict(extra="forbid")

    cpus: int | None = Field(None, ge=1, description="Number of CPUs required")
    memory: str | None = Field(None, description="Memory required (e.g., '4GB', '512MB')")
    gpus: int | None = Field(None, ge=0, description="Number of GPUs required")
    disk: str | None = Field(None, description="Disk space required")

    @field_validator("memory", "disk")
    @classmethod
    def validate_size_format(cls, v: str | None) -> str | None:
        """Validate memory/disk size format."""
        if v is None:
            return v

        valid_units = ["B", "KB", "MB", "GB", "TB"]
        v_upper = v.upper()

        for unit in valid_units:
            if v_upper.endswith(unit):
                try:
                    size_val = v_upper[: -len(unit)]
                    float(size_val)
                    return v
                except ValueError:
                    raise ValueError(f"Invalid size format: {v}. Expected format: <number><unit> (e.g., '4GB')")

        raise ValueError(f"Invalid size unit. Must be one of: {', '.join(valid_units)}")


class RetryConfig(BaseModel):
    """Retry configuration for step execution."""

    model_config = ConfigDict(extra="forbid")

    max_attempts: int = Field(3, ge=1, le=10, description="Maximum number of retry attempts")
    initial_delay: float = Field(1.0, ge=0, description="Initial delay in seconds")
    max_delay: float = Field(60.0, ge=0, description="Maximum delay in seconds")
    exponential_base: float = Field(2.0, ge=1.0, description="Exponential backoff base")
    retry_on: list[str] | None = Field(None, description="Exception types to retry on")
    not_retry_on: list[str] | None = Field(None, description="Exception types not to retry on")

    @field_validator("max_delay")
    @classmethod
    def max_delay_greater_than_initial(cls, v: float, info) -> float:
        """Validate max_delay is greater than initial_delay."""
        if "initial_delay" in info.data and v < info.data["initial_delay"]:
            raise ValueError("max_delay must be greater than or equal to initial_delay")
        return v


class StepConfig(BaseModel):
    """Configuration for pipeline steps."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, description="Step name")
    inputs: list[str] = Field(default_factory=list, description="Input asset names")
    outputs: list[str] = Field(default_factory=list, description="Output asset names")
    cache: CacheStrategy | bool = Field(True, description="Caching strategy")
    retry: RetryConfig | None = Field(None, description="Retry configuration")
    timeout: int | None = Field(None, ge=1, description="Timeout in seconds")
    resources: ResourceRequirements | None = Field(None, description="Resource requirements")
    tags: dict[str, str] = Field(default_factory=dict, description="Step tags")
    enable_cache: bool = Field(True, description="Enable caching for this step")


class PipelineConfig(BaseModel):
    """Configuration for pipelines."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields for flexibility

    name: str = Field(..., min_length=1, description="Pipeline name")
    description: str | None = Field(None, description="Pipeline description")
    version: str | None = Field(None, description="Pipeline version")
    tags: dict[str, str] = Field(default_factory=dict, description="Pipeline tags")
    enable_cache: bool = Field(True, description="Enable caching globally")
    fail_fast: bool = Field(True, description="Stop on first error")
    max_parallel: int | None = Field(None, ge=1, description="Maximum parallel steps")


class ContextConfig(BaseModel):
    """Configuration for pipeline context."""

    model_config = ConfigDict(extra="allow")  # Allow arbitrary parameters

    # Common ML parameters
    learning_rate: float | None = Field(None, gt=0, lt=1, description="Learning rate")
    batch_size: int | None = Field(None, ge=1, description="Batch size")
    epochs: int | None = Field(None, ge=1, description="Number of epochs")
    seed: int | None = Field(None, description="Random seed")

    # Infrastructure parameters
    device: str | None = Field(None, description="Device (cpu/cuda/mps)")
    num_workers: int | None = Field(None, ge=0, description="Number of workers")

    # Experiment metadata
    experiment_name: str | None = Field(None, description="Experiment name")
    run_name: str | None = Field(None, description="Run name")
    tags: dict[str, Any] = Field(default_factory=dict, description="Context tags")

    @field_validator("device")
    @classmethod
    def validate_device(cls, v: str | None) -> str | None:
        """Validate device string."""
        if v is None:
            return v

        valid_devices = ["cpu", "cuda", "mps", "tpu"]
        if v.lower() not in valid_devices and not v.startswith("cuda:"):
            raise ValueError(f"Invalid device. Must be one of: {', '.join(valid_devices)} or 'cuda:N'")

        return v.lower()


class StackConfig(BaseModel):
    """Configuration for execution stacks."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, description="Stack name")
    executor_type: Literal["local", "aws", "gcp", "azure", "kubernetes"] = Field(
        "local",
        description="Executor type",
    )
    artifact_store_path: str = Field(".flowyml/artifacts", description="Artifact storage path")
    metadata_store_path: str = Field(".flowyml/metadata.db", description="Metadata storage path")
    container_registry: str | None = Field(None, description="Container registry URL")
    enable_caching: bool = Field(True, description="Enable caching")


class DatasetSchema(BaseModel):
    """Schema for dataset validation."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Dataset name")
    version: str | None = Field(None, description="Dataset version")
    num_samples: int | None = Field(None, ge=0, description="Number of samples")
    num_features: int | None = Field(None, ge=0, description="Number of features")
    feature_names: list[str] | None = Field(None, description="Feature names")
    target_column: str | None = Field(None, description="Target column name")
    task_type: Literal["classification", "regression", "clustering", "other"] | None = Field(
        None,
        description="ML task type",
    )


class ModelSchema(BaseModel):
    """Schema for model validation."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Model name")
    framework: Literal["pytorch", "tensorflow", "sklearn", "xgboost", "lightgbm", "other"] = Field(
        ...,
        description="ML framework",
    )
    architecture: str | None = Field(None, description="Model architecture")
    input_shape: list[int] | None = Field(None, description="Input shape")
    output_shape: list[int] | None = Field(None, description="Output shape")
    num_parameters: int | None = Field(None, ge=0, description="Number of parameters")


class MetricsSchema(BaseModel):
    """Schema for metrics validation."""

    model_config = ConfigDict(extra="allow")

    accuracy: float | None = Field(None, ge=0, le=1, description="Accuracy")
    precision: float | None = Field(None, ge=0, le=1, description="Precision")
    recall: float | None = Field(None, ge=0, le=1, description="Recall")
    f1_score: float | None = Field(None, ge=0, le=1, description="F1 score")
    loss: float | None = Field(None, ge=0, description="Loss")
    mse: float | None = Field(None, ge=0, description="Mean squared error")
    mae: float | None = Field(None, ge=0, description="Mean absolute error")
    r2_score: float | None = Field(None, description="R2 score")


class ExperimentConfig(BaseModel):
    """Configuration for experiments."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Experiment name")
    description: str | None = Field(None, description="Experiment description")
    tags: dict[str, str] = Field(default_factory=dict, description="Experiment tags")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Experiment parameters")
    track_code: bool = Field(True, description="Track code changes")
    track_environment: bool = Field(True, description="Track environment")
    track_system: bool = Field(True, description="Track system info")


def validate_step_config(config: dict[str, Any]) -> StepConfig:
    """Validate step configuration.

    Args:
        config: Step configuration dictionary

    Returns:
        Validated StepConfig instance

    Raises:
        ValidationError: If validation fails
    """
    return StepConfig(**config)


def validate_pipeline_config(config: dict[str, Any]) -> PipelineConfig:
    """Validate pipeline configuration.

    Args:
        config: Pipeline configuration dictionary

    Returns:
        Validated PipelineConfig instance

    Raises:
        ValidationError: If validation fails
    """
    return PipelineConfig(**config)


def validate_context_config(config: dict[str, Any]) -> ContextConfig:
    """Validate context configuration.

    Args:
        config: Context configuration dictionary

    Returns:
        Validated ContextConfig instance

    Raises:
        ValidationError: If validation fails
    """
    return ContextConfig(**config)


def validate_metrics(metrics: dict[str, Any]) -> MetricsSchema:
    """Validate metrics.

    Args:
        metrics: Metrics dictionary

    Returns:
        Validated MetricsSchema instance

    Raises:
        ValidationError: If validation fails
    """
    return MetricsSchema(**metrics)

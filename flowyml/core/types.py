"""FlowyML Core Types - Artifact Types for Automatic Routing.

This module defines artifact types that enable automatic routing to appropriate
infrastructure based on type annotations. Just annotate your step outputs with
these types, and FlowyML will route them to the correct stores and registries.

Usage:
    from flowyml.core import step, Model, Dataset, Metrics

    @step
    def train_model(data: Dataset) -> Model:
        model = train(data)
        return Model(model, name="my_classifier", version="1.0.0")

    @step
    def evaluate(model: Model) -> Metrics:
        return Metrics({"accuracy": 0.95, "f1": 0.92})

The stack configuration determines where each type is routed:
    - Model → artifact_store + optional model_registry
    - Dataset → artifact_store
    - Metrics → experiment_tracker
"""

from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# BASE ARTIFACT TYPE
# =============================================================================


@dataclass
class Artifact(ABC):  # noqa: B024
    """Base artifact type for automatic routing.

    All routable artifacts inherit from this class. The runtime inspects
    step return types and routes outputs based on their artifact type.

    Attributes:
        data: The actual artifact data (model, dataset, etc.)
        name: Optional name for the artifact
        metadata: Additional metadata to store with the artifact
        uri: URI where the artifact is stored (set after saving)
    """

    data: Any = None
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    uri: str | None = None

    def __post_init__(self):
        """Validate artifact after initialization."""
        if self.metadata is None:
            self.metadata = {}

    def with_metadata(self, **kwargs) -> "Artifact":
        """Add metadata to the artifact.

        Args:
            **kwargs: Key-value pairs to add to metadata.

        Returns:
            Self for method chaining.
        """
        self.metadata.update(kwargs)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact metadata to dictionary.

        Returns:
            Dictionary representation (excluding the data itself).
        """
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "metadata": self.metadata,
            "uri": self.uri,
        }


# =============================================================================
# MODEL ARTIFACT
# =============================================================================


@dataclass
class Model(Artifact):
    """ML model artifact - routes to artifact store + optional model registry.

    Use this type for step outputs that are machine learning models.
    When configured, models are automatically:
    1. Saved to the artifact store (GCS, S3, local)
    2. Registered in the model registry (Vertex AI, SageMaker, MLflow)

    Attributes:
        data: The model object (sklearn, pytorch, tensorflow, etc.)
        name: Model name for registry
        version: Optional version string
        framework: ML framework (auto-detected if not provided)
        serving_config: Optional serving configuration

    Example:
        @step
        def train() -> Model:
            clf = RandomForestClassifier().fit(X, y)
            return Model(
                data=clf,
                name="fraud_detector",
                version="1.0.0",
                framework="sklearn"
            )
    """

    version: str | None = None
    framework: str | None = None
    serving_config: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None

    def __post_init__(self):
        """Auto-detect framework if not provided."""
        super().__post_init__()
        if self.framework is None and self.data is not None:
            self.framework = self._detect_framework()

    def _detect_framework(self) -> str:
        """Detect the ML framework from the model object."""
        model = self.data
        model_type = type(model).__module__

        if "sklearn" in model_type:
            return "sklearn"
        elif "torch" in model_type:
            return "pytorch"
        elif "tensorflow" in model_type or "keras" in model_type:
            return "tensorflow"
        elif "xgboost" in model_type:
            return "xgboost"
        elif "lightgbm" in model_type:
            return "lightgbm"
        elif "catboost" in model_type:
            return "catboost"
        else:
            return "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Serialize model metadata."""
        base = super().to_dict()
        base.update(
            {
                "version": self.version,
                "framework": self.framework,
                "serving_config": self.serving_config,
                "input_schema": self.input_schema,
                "output_schema": self.output_schema,
            },
        )
        return base


# =============================================================================
# DATASET ARTIFACT
# =============================================================================


@dataclass
class Dataset(Artifact):
    """Dataset artifact - routes to artifact store.

    Use this type for step outputs that are datasets (training data,
    feature tables, processed data, etc.).

    Attributes:
        data: The dataset (DataFrame, numpy array, file path, etc.)
        name: Dataset name
        format: Data format (parquet, csv, json, etc.)
        schema: Optional schema definition
        statistics: Optional statistics about the dataset

    Example:
        @step
        def preprocess(raw_data: pd.DataFrame) -> Dataset:
            processed = clean_and_transform(raw_data)
            return Dataset(
                data=processed,
                name="training_features",
                format="parquet",
                statistics={"rows": len(processed)}
            )
    """

    format: str | None = None  # noqa: A003
    schema: dict[str, Any] | None = None
    statistics: dict[str, Any] | None = None
    num_rows: int | None = None
    num_columns: int | None = None

    def __post_init__(self):
        """Auto-detect format and compute statistics if possible."""
        super().__post_init__()
        if self.data is not None:
            self._detect_properties()

    def _detect_properties(self):
        """Detect dataset properties from the data."""
        data = self.data

        # Detect format
        if self.format is None:
            if hasattr(data, "to_parquet"):
                self.format = "parquet"
            elif hasattr(data, "to_csv"):
                self.format = "csv"
            elif isinstance(data, (str, Path)):
                path = Path(data)
                self.format = path.suffix.lstrip(".")

        # Detect dimensions
        if hasattr(data, "shape"):
            shape = data.shape
            self.num_rows = shape[0] if len(shape) > 0 else None
            self.num_columns = shape[1] if len(shape) > 1 else None
        elif hasattr(data, "__len__"):
            self.num_rows = len(data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize dataset metadata."""
        base = super().to_dict()
        base.update(
            {
                "format": self.format,
                "schema": self.schema,
                "statistics": self.statistics,
                "num_rows": self.num_rows,
                "num_columns": self.num_columns,
            },
        )
        return base


# =============================================================================
# METRICS ARTIFACT
# =============================================================================


class Metrics(dict):
    """Metrics dictionary - routes to experiment tracker.

    Use this type for step outputs that are evaluation metrics.
    Metrics are automatically logged to the configured experiment
    tracker (MLflow, Vertex AI Experiments, etc.).

    This is a dict subclass for easy use - just return a Metrics dict
    from your step and it will be automatically logged.

    Example:
        @step
        def evaluate(model: Model, test_data: Dataset) -> Metrics:
            predictions = model.predict(test_data)
            return Metrics({
                "accuracy": accuracy_score(y_true, predictions),
                "f1": f1_score(y_true, predictions),
                "precision": precision_score(y_true, predictions),
            })
    """

    def __init__(self, data: dict[str, Union[int, float]] | None = None, **kwargs):
        """Initialize metrics.

        Args:
            data: Dictionary of metric names to values.
            **kwargs: Additional metrics as keyword arguments.
        """
        if data is None:
            data = {}
        super().__init__(data)
        self.update(kwargs)
        self._step: int | None = None
        self._run_id: str | None = None
        self._metadata: dict[str, Any] = {}

    def at_step(self, step: int) -> "Metrics":
        """Set the step number for these metrics.

        Args:
            step: Step/epoch number.

        Returns:
            Self for method chaining.
        """
        self._step = step
        return self

    def with_metadata(self, **kwargs) -> "Metrics":
        """Add metadata to the metrics.

        Args:
            **kwargs: Key-value pairs to add to metadata.

        Returns:
            Self for method chaining.
        """
        self._metadata.update(kwargs)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize metrics to dictionary."""
        return {
            "type": "Metrics",
            "values": dict(self),
            "step": self._step,
            "run_id": self._run_id,
            "metadata": self._metadata,
        }


# =============================================================================
# PARAMETERS ARTIFACT
# =============================================================================


class Parameters(dict):
    """Parameters dictionary - logs to experiment tracker as params.

    Use this type for step inputs/outputs that are hyperparameters
    or configuration values. Parameters are logged for reproducibility.

    Example:
        @step
        def train(params: Parameters) -> Model:
            model = RandomForestClassifier(**params)
            return Model(model.fit(X, y))
    """

    def __init__(self, data: dict[str, Any] | None = None, **kwargs):
        """Initialize parameters.

        Args:
            data: Dictionary of parameter names to values.
            **kwargs: Additional parameters as keyword arguments.
        """
        if data is None:
            data = {}
        super().__init__(data)
        self.update(kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize parameters to dictionary."""
        return {
            "type": "Parameters",
            "values": dict(self),
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def is_artifact_type(obj: Any) -> bool:
    """Check if an object is a FlowyML artifact type.

    Args:
        obj: Object or type to check.

    Returns:
        True if it's an artifact type or instance.
    """
    if isinstance(obj, type):
        return issubclass(obj, (Artifact, Metrics, Parameters))
    return isinstance(obj, (Artifact, Metrics, Parameters))


def get_artifact_type_name(obj: Any) -> str | None:
    """Get the artifact type name for routing.

    Args:
        obj: Artifact instance or type.

    Returns:
        Type name string or None.
    """
    if isinstance(obj, type):
        if issubclass(obj, Artifact) or obj in (Metrics, Parameters):
            return obj.__name__
    elif isinstance(obj, (Artifact, Metrics, Parameters)):
        return type(obj).__name__
    return None


# =============================================================================
# TYPE ALIASES FOR CONVENIENCE
# =============================================================================

# Common type aliases
ModelArtifact = Model
DatasetArtifact = Dataset
MetricsDict = Metrics
ParamsDict = Parameters

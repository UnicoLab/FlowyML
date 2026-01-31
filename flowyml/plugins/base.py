"""FlowyML Plugin System - Base Classes.

This module defines the base classes for all FlowyML plugins, providing
a consistent interface for extending FlowyML with custom components.

Usage:
    from flowyml.plugins.base import ExperimentTracker, FeatureStore

    class MyTracker(ExperimentTracker):
        def log_params(self, params: dict):
            ...
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import logging

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins available in FlowyML."""

    # Core MLOps Components
    EXPERIMENT_TRACKER = "experiment_tracker"
    ARTIFACT_STORE = "artifact_store"
    ORCHESTRATOR = "orchestrator"
    CONTAINER_REGISTRY = "container_registry"
    MODEL_REGISTRY = "model_registry"

    # Data Components
    FEATURE_STORE = "feature_store"
    DATA_VALIDATOR = "data_validator"

    # Infrastructure
    STEP_OPERATOR = "step_operator"
    IMAGE_BUILDER = "image_builder"

    # Notifications & Alerts
    ALERTER = "alerter"

    # Other
    CUSTOM = "custom"


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""

    name: str
    description: str
    plugin_type: PluginType
    version: str = "1.0.0"
    author: str = "FlowyML"
    packages: list[str] = field(default_factory=list)
    documentation_url: str = ""
    tags: list[str] = field(default_factory=list)


class BasePlugin(ABC):
    """Base class for all FlowyML plugins.

    All plugins must inherit from this class and implement the required methods.
    """

    # Class-level metadata (override in subclasses)
    METADATA: PluginMetadata | None = None

    def __init__(self, name: str = None, **config):
        """Initialize the plugin.

        Args:
            name: Optional name override for this instance.
            **config: Configuration parameters for the plugin.
        """
        self._name = name or self.__class__.__name__
        self._config = config
        self._is_initialized = False

    @property
    def name(self) -> str:
        """Get the plugin instance name."""
        return self._name

    @property
    def config(self) -> dict[str, Any]:
        """Get the plugin configuration."""
        return self._config

    @property
    @abstractmethod
    def plugin_type(self) -> PluginType:
        """Return the type of this plugin."""
        pass

    def initialize(self) -> None:
        """Initialize the plugin. Called before first use.

        Override this method to perform setup operations like
        connecting to external services.
        """
        self._is_initialized = True

    def cleanup(self) -> None:
        """Cleanup resources used by the plugin.

        Override this method to close connections, flush buffers, etc.
        """
        self._is_initialized = False

    def validate(self) -> bool:
        """Validate that the plugin is properly configured.

        Returns:
            True if the plugin is valid and ready to use.
        """
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize the plugin configuration to a dictionary.

        Returns:
            Dictionary representation of the plugin.
        """
        return {
            "name": self._name,
            "type": self.plugin_type.value,
            "config": self._config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BasePlugin":
        """Create a plugin instance from a dictionary.

        Args:
            data: Dictionary containing plugin configuration.

        Returns:
            A new plugin instance.
        """
        config = data.get("config", {})
        name = data.get("name")
        return cls(name=name, **config)


# ============================================================================
# EXPERIMENT TRACKERS
# ============================================================================


class ExperimentTracker(BasePlugin):
    """Base class for experiment tracking plugins.

    Experiment trackers record parameters, metrics, and artifacts
    from ML experiments for reproducibility and comparison.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.EXPERIMENT_TRACKER

    @abstractmethod
    def start_run(self, run_name: str, experiment_name: str = None, tags: dict = None) -> str:
        """Start a new experiment run.

        Args:
            run_name: Name for this run.
            experiment_name: Name of the experiment to log to.
            tags: Optional tags for the run.

        Returns:
            Run ID.
        """
        pass

    @abstractmethod
    def end_run(self, status: str = "FINISHED") -> None:
        """End the current run.

        Args:
            status: Final status of the run (FINISHED, FAILED, etc.)
        """
        pass

    @abstractmethod
    def log_params(self, params: dict[str, Any]) -> None:
        """Log parameters for the current run.

        Args:
            params: Dictionary of parameter names and values.
        """
        pass

    @abstractmethod
    def log_metrics(self, metrics: dict[str, float], step: int = None) -> None:
        """Log metrics for the current run.

        Args:
            metrics: Dictionary of metric names and values.
            step: Optional step number for the metrics.
        """
        pass

    def log_artifact(self, local_path: str, artifact_path: str = None) -> None:
        """Log an artifact (file) for the current run.

        Args:
            local_path: Path to the local file to log.
            artifact_path: Optional path within the artifact store.
        """
        pass

    def log_model(self, model: Any, artifact_path: str, model_type: str = None) -> None:
        """Log a model for the current run.

        Args:
            model: The model object to log.
            artifact_path: Path within the artifact store.
            model_type: Type of model (sklearn, pytorch, tensorflow, etc.)
        """
        pass

    def get_tracking_uri(self) -> str:
        """Get the tracking URI for this tracker.

        Returns:
            The tracking URI.
        """
        return self._config.get("tracking_uri", "")


# ============================================================================
# ARTIFACT STORES
# ============================================================================


class ArtifactStorePlugin(BasePlugin):
    """Base class for artifact storage plugins.

    Artifact stores handle the persistence of artifacts like
    datasets, models, and other files.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.ARTIFACT_STORE

    @abstractmethod
    def save(self, artifact: Any, path: str) -> str:
        """Save an artifact to the store.

        Args:
            artifact: The artifact to save.
            path: Path within the store.

        Returns:
            Full URI of the saved artifact.
        """
        pass

    @abstractmethod
    def load(self, path: str) -> Any:
        """Load an artifact from the store.

        Args:
            path: Path to the artifact.

        Returns:
            The loaded artifact.
        """
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if an artifact exists.

        Args:
            path: Path to check.

        Returns:
            True if the artifact exists.
        """
        pass

    def delete(self, path: str) -> bool:
        """Delete an artifact from the store.

        Args:
            path: Path to delete.

        Returns:
            True if deletion was successful.
        """
        return False

    def list(self, path: str = "") -> list[str]:  # noqa: A003
        """List artifacts in a directory.

        Args:
            path: Directory path to list.

        Returns:
            List of artifact paths.
        """
        return []

    @property
    def root_path(self) -> str:
        """Get the root path of the artifact store."""
        return self._config.get("path", "")


# ============================================================================
# ORCHESTRATORS
# ============================================================================


class OrchestratorPlugin(BasePlugin):
    """Base class for orchestrator plugins.

    Orchestrators manage the execution of pipeline steps,
    handling scheduling, resource allocation, and monitoring.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.ORCHESTRATOR

    @abstractmethod
    def run_pipeline(
        self,
        pipeline: Any,
        run_id: str,
        context: dict[str, Any] = None,
        **kwargs,
    ) -> Any:
        """Run a pipeline.

        Args:
            pipeline: The pipeline to run.
            run_id: Unique identifier for this run.
            context: Optional context dictionary.
            **kwargs: Additional orchestrator-specific arguments.

        Returns:
            Run result or status.
        """
        pass

    def get_run_status(self, run_id: str) -> str:
        """Get the status of a pipeline run.

        Args:
            run_id: The run identifier.

        Returns:
            Run status string.
        """
        return "unknown"

    def cancel_run(self, run_id: str) -> bool:
        """Cancel a running pipeline.

        Args:
            run_id: The run identifier.

        Returns:
            True if cancellation was successful.
        """
        return False

    def list_runs(self, pipeline_name: str = None, limit: int = 100) -> list[dict]:
        """List pipeline runs.

        Args:
            pipeline_name: Optional filter by pipeline name.
            limit: Maximum number of runs to return.

        Returns:
            List of run dictionaries.
        """
        return []


# ============================================================================
# CONTAINER REGISTRIES
# ============================================================================


class ContainerRegistryPlugin(BasePlugin):
    """Base class for container registry plugins.

    Container registries store and manage Docker images
    for pipeline execution.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.CONTAINER_REGISTRY

    @abstractmethod
    def push_image(self, image_name: str, tag: str = "latest") -> str:
        """Push an image to the registry.

        Args:
            image_name: Name of the image.
            tag: Image tag.

        Returns:
            Full image URI.
        """
        pass

    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        """Pull an image from the registry.

        Args:
            image_name: Name of the image.
            tag: Image tag.
        """
        pass

    @abstractmethod
    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        """Get the full URI for an image.

        Args:
            image_name: Name of the image.
            tag: Image tag.

        Returns:
            Full image URI.
        """
        pass

    @property
    def registry_uri(self) -> str:
        """Get the registry URI."""
        return self._config.get("uri", "")


# ============================================================================
# FEATURE STORES
# ============================================================================


class FeatureStorePlugin(BasePlugin):
    """Base class for feature store plugins.

    Feature stores manage ML features for training and inference,
    providing versioning, serving, and discovery capabilities.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.FEATURE_STORE

    @abstractmethod
    def get_feature_view(self, name: str, version: str = None) -> Any:
        """Get a feature view by name.

        Args:
            name: Name of the feature view.
            version: Optional version.

        Returns:
            The feature view.
        """
        pass

    @abstractmethod
    def get_online_features(
        self,
        feature_refs: list[str],
        entity_rows: list[dict],
    ) -> dict[str, list]:
        """Get online (real-time) features.

        Args:
            feature_refs: List of feature references (feature_view:feature).
            entity_rows: Entity key-value pairs.

        Returns:
            Dictionary of feature names to value lists.
        """
        pass

    def get_historical_features(
        self,
        feature_refs: list[str],
        entity_df: Any,
    ) -> Any:
        """Get historical features for training.

        Args:
            feature_refs: List of feature references.
            entity_df: DataFrame with entity keys and timestamps.

        Returns:
            DataFrame with features.
        """
        pass


# ============================================================================
# DATA VALIDATORS
# ============================================================================


class DataValidatorPlugin(BasePlugin):
    """Base class for data validation plugins.

    Data validators check data quality, schema conformance,
    and detect anomalies in datasets.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.DATA_VALIDATOR

    @abstractmethod
    def validate(self, data: Any, expectations: Any = None) -> dict[str, Any]:
        """Validate data against expectations.

        Args:
            data: The data to validate.
            expectations: Validation rules/expectations.

        Returns:
            Validation results dictionary.
        """
        pass

    def get_data_profile(self, data: Any) -> dict[str, Any]:
        """Generate a profile of the data.

        Args:
            data: The data to profile.

        Returns:
            Data profile dictionary.
        """
        return {}


# ============================================================================
# MODEL REGISTRY
# ============================================================================


class ModelRegistryPlugin(BasePlugin):
    """Base class for model registry plugins.

    Model registries track, version, and manage ML models
    throughout their lifecycle.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.MODEL_REGISTRY

    @abstractmethod
    def register_model(
        self,
        name: str,
        model_uri: str,
        version: str = None,
        metadata: dict = None,
    ) -> str:
        """Register a model.

        Args:
            name: Model name.
            model_uri: URI to the model artifact.
            version: Optional version string.
            metadata: Optional metadata dictionary.

        Returns:
            Model version identifier.
        """
        pass

    @abstractmethod
    def get_model(self, name: str, version: str = None) -> Any:
        """Get a model by name.

        Args:
            name: Model name.
            version: Optional version (defaults to latest).

        Returns:
            The model.
        """
        pass

    def list_models(self, name: str = None) -> list[dict]:
        """List registered models.

        Args:
            name: Optional filter by model name.

        Returns:
            List of model metadata dictionaries.
        """
        return []

    def transition_model_stage(
        self,
        name: str,
        version: str,
        stage: str,
    ) -> None:
        """Transition a model to a new stage.

        Args:
            name: Model name.
            version: Model version.
            stage: Target stage (staging, production, archived).
        """
        pass


# ============================================================================
# ALERTERS
# ============================================================================


class AlerterPlugin(BasePlugin):
    """Base class for alerter plugins.

    Alerters send notifications about pipeline events,
    errors, and other important occurrences.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.ALERTER

    @abstractmethod
    def send_alert(
        self,
        title: str,
        message: str,
        level: str = "info",
        **kwargs,
    ) -> bool:
        """Send an alert notification.

        Args:
            title: Alert title.
            message: Alert message body.
            level: Alert level (info, warning, error, critical).
            **kwargs: Additional alerter-specific parameters.

        Returns:
            True if alert was sent successfully.
        """
        pass

    def send_success(self, title: str, message: str) -> bool:
        """Send a success notification."""
        return self.send_alert(title, message, level="success")

    def send_error(self, title: str, message: str) -> bool:
        """Send an error notification."""
        return self.send_alert(title, message, level="error")


# ============================================================================
# MODEL DEPLOYER
# ============================================================================


class ModelDeployerPlugin(BasePlugin):
    """Base class for model deployment plugins.

    Model deployers handle deploying ML models to inference endpoints
    for serving predictions.
    """

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.CUSTOM  # Will be MODEL_DEPLOYER when added to enum

    @abstractmethod
    def deploy(
        self,
        model: Any,
        endpoint_name: str,
        model_name: str = None,
        **config,
    ) -> str:
        """Deploy a model to an endpoint.

        Args:
            model: The model to deploy (URI, artifact, or object).
            endpoint_name: Name for the endpoint.
            model_name: Optional model name in registry.
            **config: Deployment configuration.

        Returns:
            Endpoint URI or identifier.
        """
        pass

    @abstractmethod
    def predict(self, endpoint: str, data: Any) -> Any:
        """Make predictions using a deployed model.

        Args:
            endpoint: Endpoint URI or identifier.
            data: Input data for prediction.

        Returns:
            Prediction results.
        """
        pass

    def undeploy(self, endpoint: str) -> bool:
        """Undeploy a model endpoint.

        Args:
            endpoint: Endpoint URI or identifier.

        Returns:
            True if successful.
        """
        return False

    def list_endpoints(self) -> list[dict]:
        """List all deployed endpoints.

        Returns:
            List of endpoint metadata dictionaries.
        """
        return []

    def get_endpoint_status(self, endpoint: str) -> dict[str, Any]:
        """Get the status of an endpoint.

        Args:
            endpoint: Endpoint URI or identifier.

        Returns:
            Status dictionary.
        """
        return {"status": "unknown"}

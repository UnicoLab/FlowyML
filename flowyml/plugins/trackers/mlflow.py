"""MLflow Experiment Tracker - Native FlowyML Plugin.

This is a native FlowyML implementation that uses MLflow directly,
without requiring any external framework dependencies.

Usage:
    from flowyml.plugins import get_plugin

    tracker = get_plugin("mlflow", tracking_uri="http://localhost:5000")

    tracker.start_run("my_experiment", experiment_name="training")
    tracker.log_params({"learning_rate": 0.001, "epochs": 100})
    tracker.log_metrics({"accuracy": 0.95, "loss": 0.05})
    tracker.end_run()
"""

import logging
from typing import Any
from pathlib import Path

from flowyml.plugins.base import ExperimentTracker, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class MLflowTracker(ExperimentTracker):
    """Native MLflow experiment tracker for FlowyML.

    This tracker integrates directly with MLflow without any
    intermediate framework, providing full control over the
    tracking experience.

    Args:
        tracking_uri: MLflow tracking server URI. If not provided,
            uses a local mlruns directory.
        experiment_name: Default experiment name.
        artifact_location: Custom artifact storage location.
        registry_uri: Model registry URI (if different from tracking).

    Example:
        tracker = MLflowTracker(
            tracking_uri="http://localhost:5000",
            experiment_name="my_experiments"
        )

        run_id = tracker.start_run("training_v1")
        tracker.log_params({"lr": 0.001})
        tracker.log_metrics({"accuracy": 0.95})
        tracker.log_artifact("model.pkl")
        tracker.end_run()
    """

    METADATA = PluginMetadata(
        name="mlflow",
        description="MLflow experiment tracking and model registry",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        version="1.0.0",
        author="FlowyML",
        packages=["mlflow>=2.0"],
        documentation_url="https://mlflow.org/docs/latest/index.html",
        tags=["experiment-tracking", "model-registry", "popular"],
    )

    def __init__(
        self,
        tracking_uri: str = None,
        experiment_name: str = None,
        artifact_location: str = None,
        registry_uri: str = None,
        **kwargs,
    ):
        """Initialize the MLflow tracker."""
        super().__init__(
            name=kwargs.pop("name", "mlflow"),
            tracking_uri=tracking_uri,
            experiment_name=experiment_name,
            artifact_location=artifact_location,
            registry_uri=registry_uri,
            **kwargs,
        )

        self._mlflow = None
        self._current_run = None
        self._experiment_name = experiment_name
        self._artifact_location = artifact_location

    def initialize(self) -> None:
        """Initialize MLflow connection."""
        try:
            import mlflow

            self._mlflow = mlflow

            # Set tracking URI
            tracking_uri = self._config.get("tracking_uri") or self._local_backend()
            mlflow.set_tracking_uri(tracking_uri)

            # Set registry URI if provided
            registry_uri = self._config.get("registry_uri")
            if registry_uri:
                mlflow.set_registry_uri(registry_uri)

            self._is_initialized = True
            logger.info(f"MLflow initialized with tracking URI: {tracking_uri}")

        except ImportError:
            raise ImportError(
                "MLflow is not installed. Run: flowyml plugin install mlflow",
            )

    def _local_backend(self) -> str:
        """Get the local MLflow backend path."""
        mlruns_path = Path.cwd() / "mlruns"
        mlruns_path.mkdir(parents=True, exist_ok=True)
        return f"file:{mlruns_path}"

    def _ensure_initialized(self) -> None:
        """Ensure MLflow is initialized."""
        if not self._is_initialized:
            self.initialize()

    def start_run(
        self,
        run_name: str,
        experiment_name: str = None,
        tags: dict = None,
    ) -> str:
        """Start a new MLflow run.

        Args:
            run_name: Name for this run.
            experiment_name: Experiment to log to. Uses default if not provided.
            tags: Optional tags for the run.

        Returns:
            The run ID.
        """
        self._ensure_initialized()

        # Set experiment
        exp_name = experiment_name or self._experiment_name or "default"
        self._mlflow.set_experiment(exp_name)

        # Start run
        run = self._mlflow.start_run(run_name=run_name, tags=tags)
        self._current_run = run

        logger.info(f"Started MLflow run '{run_name}' (ID: {run.info.run_id})")
        return run.info.run_id

    def end_run(self, status: str = "FINISHED") -> None:
        """End the current run.

        Args:
            status: Final status (FINISHED, FAILED, KILLED).
        """
        self._ensure_initialized()

        mlflow_status = {
            "FINISHED": "FINISHED",
            "FAILED": "FAILED",
            "KILLED": "KILLED",
        }.get(status.upper(), "FINISHED")

        self._mlflow.end_run(status=mlflow_status)
        self._current_run = None
        logger.info(f"Ended MLflow run with status: {mlflow_status}")

    def log_params(self, params: dict[str, Any]) -> None:
        """Log parameters to the current run.

        Args:
            params: Dictionary of parameter names and values.
        """
        self._ensure_initialized()
        self._mlflow.log_params(params)

    def log_metrics(self, metrics: dict[str, float], step: int = None) -> None:
        """Log metrics to the current run.

        Args:
            metrics: Dictionary of metric names and values.
            step: Optional step number.
        """
        self._ensure_initialized()
        self._mlflow.log_metrics(metrics, step=step)

    def log_artifact(self, local_path: str, artifact_path: str = None) -> None:
        """Log an artifact file.

        Args:
            local_path: Path to the local file.
            artifact_path: Optional subdirectory in artifacts.
        """
        self._ensure_initialized()
        self._mlflow.log_artifact(local_path, artifact_path)

    def log_artifacts(self, local_dir: str, artifact_path: str = None) -> None:
        """Log all files in a directory as artifacts.

        Args:
            local_dir: Path to the local directory.
            artifact_path: Optional subdirectory in artifacts.
        """
        self._ensure_initialized()
        self._mlflow.log_artifacts(local_dir, artifact_path)

    def log_model(
        self,
        model: Any,
        artifact_path: str,
        model_type: str = None,
        registered_model_name: str = None,
    ) -> None:
        """Log a model to the current run.

        Args:
            model: The model object.
            artifact_path: Path within artifacts.
            model_type: Type of model (sklearn, pytorch, tensorflow, keras).
            registered_model_name: Optional name to register in model registry.
        """
        self._ensure_initialized()

        # Auto-detect model type if not provided
        if model_type is None:
            model_type = self._detect_model_type(model)

        # Log using appropriate MLflow flavor
        if model_type == "sklearn":
            self._mlflow.sklearn.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
            )
        elif model_type == "pytorch":
            self._mlflow.pytorch.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
            )
        elif model_type == "tensorflow" or model_type == "keras":
            self._mlflow.keras.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
            )
        elif model_type == "xgboost":
            self._mlflow.xgboost.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name,
            )
        else:
            # Fallback to generic pickling
            self._mlflow.pyfunc.log_model(
                artifact_path,
                python_model=model,
                registered_model_name=registered_model_name,
            )

    def _detect_model_type(self, model: Any) -> str:
        """Detect the type of ML model."""
        model_class = type(model).__module__

        if "sklearn" in model_class:
            return "sklearn"
        elif "torch" in model_class:
            return "pytorch"
        elif "tensorflow" in model_class or "keras" in model_class:
            return "keras"
        elif "xgboost" in model_class:
            return "xgboost"
        else:
            return "generic"

    def get_tracking_uri(self) -> str:
        """Get the current tracking URI."""
        self._ensure_initialized()
        return self._mlflow.get_tracking_uri()

    def get_run_id(self) -> str | None:
        """Get the current run ID."""
        if self._current_run:
            return self._current_run.info.run_id
        return None

    def set_tag(self, key: str, value: str) -> None:
        """Set a tag on the current run."""
        self._ensure_initialized()
        self._mlflow.set_tag(key, value)

    def set_tags(self, tags: dict[str, str]) -> None:
        """Set multiple tags on the current run."""
        self._ensure_initialized()
        self._mlflow.set_tags(tags)

    def autolog(self, framework: str = None) -> None:
        """Enable MLflow autologging.

        Args:
            framework: Specific framework to enable (sklearn, pytorch, etc.)
                      If None, enables for all supported frameworks.
        """
        self._ensure_initialized()

        if framework:
            getattr(self._mlflow, framework).autolog()
        else:
            self._mlflow.autolog()

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self._current_run:
            self.end_run()
        self._is_initialized = False

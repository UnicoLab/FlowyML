"""FlowyML Stack - Unified Interface for ML Operations.

This module provides a unified, intuitive API for common ML operations.
Just configure your stack in flowyml.yaml and use these functions -
FlowyML automatically routes to the configured plugins.

Usage:
    # flowyml.yaml
    plugins:
      experiment_tracker:
        type: mlflow
        tracking_uri: http://localhost:5000
      artifact_store:
        type: gcs
        bucket: my-ml-artifacts
      container_registry:
        type: gcr
        project: my-gcp-project

    # In code - intuitive API, no plugin knowledge needed
    from flowyml.plugins.stack import (
        start_run, end_run,
        log_params, log_metrics,
        save_artifact, load_artifact,
        save_model, load_model,
    )

    # Just use - FlowyML routes to your configured plugins
    start_run("training_v1")
    log_params({"lr": 0.001, "epochs": 100})

    # Train model...
    log_metrics({"accuracy": 0.95})
    save_artifact(test_data, "data/test.pkl")
    save_model(model, "models/classifier")

    end_run()
"""

import logging
from typing import Any
from contextlib import contextmanager

from flowyml.plugins.config import (
    get_config,
    get_tracker,
    get_artifact_store,
    get_container_registry,
    get_orchestrator,
    get_alerter,
)

logger = logging.getLogger(__name__)


# =============================================================================
# EXPERIMENT TRACKING (Auto-routes to configured tracker)
# =============================================================================

_current_run_id: str | None = None


def start_run(
    run_name: str,
    experiment_name: str = None,
    tags: dict = None,
) -> str | None:
    """Start a new experiment run.

    Uses the experiment_tracker configured in flowyml.yaml.

    Args:
        run_name: Name for this run.
        experiment_name: Optional experiment name.
        tags: Optional tags for the run.

    Returns:
        Run ID if successful, None otherwise.

    Example:
        start_run("training_v1", experiment_name="image_classification")
    """
    global _current_run_id
    tracker = get_tracker()

    if tracker:
        _current_run_id = tracker.start_run(run_name, experiment_name, tags)
        return _current_run_id
    else:
        logger.warning("No experiment_tracker configured in flowyml.yaml")
        return None


def end_run(status: str = "FINISHED") -> None:
    """End the current experiment run.

    Args:
        status: Final status (FINISHED, FAILED, etc.)
    """
    global _current_run_id
    tracker = get_tracker()

    if tracker:
        tracker.end_run(status)
        _current_run_id = None
    else:
        logger.warning("No experiment_tracker configured")


@contextmanager
def run(run_name: str, experiment_name: str = None, tags: dict = None):
    """Context manager for experiment runs.

    Usage:
        with run("my_training"):
            log_params({"lr": 0.001})
            # Train model...
            log_metrics({"accuracy": 0.95})
    """
    try:
        start_run(run_name, experiment_name, tags)
        yield
        end_run("FINISHED")
    except Exception:
        end_run("FAILED")
        raise


def log_params(params: dict[str, Any]) -> None:
    """Log parameters to the current run.

    Args:
        params: Dictionary of parameter names and values.

    Example:
        log_params({"learning_rate": 0.001, "batch_size": 32})
    """
    tracker = get_tracker()
    if tracker:
        tracker.log_params(params)


def log_metrics(metrics: dict[str, float], step: int = None) -> None:
    """Log metrics to the current run.

    Args:
        metrics: Dictionary of metric names and values.
        step: Optional step number.

    Example:
        log_metrics({"accuracy": 0.95, "loss": 0.05}, step=100)
    """
    tracker = get_tracker()
    if tracker:
        tracker.log_metrics(metrics, step)


def log_artifact(local_path: str, artifact_path: str = None) -> None:
    """Log an artifact file to the current run.

    Args:
        local_path: Path to the local file.
        artifact_path: Optional subdirectory in artifacts.
    """
    tracker = get_tracker()
    if tracker and hasattr(tracker, "log_artifact"):
        tracker.log_artifact(local_path, artifact_path)


def set_tag(key: str, value: str) -> None:
    """Set a tag on the current run."""
    tracker = get_tracker()
    if tracker and hasattr(tracker, "set_tag"):
        tracker.set_tag(key, value)


def set_tags(tags: dict[str, str]) -> None:
    """Set multiple tags on the current run."""
    tracker = get_tracker()
    if tracker and hasattr(tracker, "set_tags"):
        tracker.set_tags(tags)


# =============================================================================
# ARTIFACT STORAGE (Auto-routes to configured store)
# =============================================================================


def save_artifact(artifact: Any, path: str) -> str | None:
    """Save an artifact to the configured artifact store.

    Uses the artifact_store configured in flowyml.yaml.

    Args:
        artifact: The artifact to save (model, data, etc.)
        path: Path within the store.

    Returns:
        Full URI of the saved artifact.

    Example:
        save_artifact(processed_data, "data/processed.pkl")
        save_artifact({"config": config}, "configs/training.json")
    """
    store = get_artifact_store()

    if store:
        return store.save(artifact, path)
    else:
        logger.warning("No artifact_store configured in flowyml.yaml")
        return None


def load_artifact(path: str) -> Any | None:
    """Load an artifact from the configured artifact store.

    Args:
        path: Path to the artifact.

    Returns:
        The loaded artifact.

    Example:
        data = load_artifact("data/processed.pkl")
    """
    store = get_artifact_store()

    if store:
        return store.load(path)
    else:
        logger.warning("No artifact_store configured")
        return None


def artifact_exists(path: str) -> bool:
    """Check if an artifact exists in the store.

    Args:
        path: Path to check.

    Returns:
        True if the artifact exists.
    """
    store = get_artifact_store()
    return store.exists(path) if store else False


def list_artifacts(path: str = "") -> list[str]:
    """List artifacts in a directory.

    Args:
        path: Directory path to list.

    Returns:
        List of artifact paths.
    """
    store = get_artifact_store()
    return store.list(path) if store else []


def delete_artifact(path: str) -> bool:
    """Delete an artifact from the store.

    Args:
        path: Path to delete.

    Returns:
        True if deletion was successful.
    """
    store = get_artifact_store()
    return store.delete(path) if store else False


# =============================================================================
# MODEL MANAGEMENT (Uses both artifact store and tracker)
# =============================================================================


def save_model(
    model: Any,
    path: str,
    model_type: str = None,
    register: bool = True,
    model_name: str = None,
) -> str | None:
    """Save a model to the artifact store with tracking.

    This is the recommended way to save models - it automatically:
    1. Saves the model to the artifact store
    2. Logs it to the experiment tracker (if in a run)
    3. Optionally registers in model registry

    Args:
        model: The model object.
        path: Path within the artifact store.
        model_type: Type of model (sklearn, pytorch, tensorflow, etc.)
        register: If True, register in model registry (if configured).
        model_name: Name for model registry (uses path if not provided).

    Returns:
        Full URI of the saved model.

    Example:
        # Simple save
        save_model(clf, "models/classifier")

        # With explicit type
        save_model(model, "models/neural_net", model_type="pytorch")
    """
    # Save to artifact store
    store = get_artifact_store()
    uri = None

    if store:
        uri = store.save(model, path)
        logger.info(f"Model saved to: {uri}")

    # Log to tracker if in a run
    tracker = get_tracker()
    if tracker and _current_run_id:
        if hasattr(tracker, "log_model"):
            tracker.log_model(model, path, model_type=model_type)
        if uri:
            set_tag("model_uri", uri)

    return uri


def load_model(path: str) -> Any | None:
    """Load a model from the artifact store.

    Args:
        path: Path to the model.

    Returns:
        The loaded model.

    Example:
        model = load_model("models/classifier.pkl")
    """
    return load_artifact(path)


# =============================================================================
# CONTAINER REGISTRY (Auto-routes to configured registry)
# =============================================================================


def push_image(image_name: str, tag: str = "latest", local_image: str = None) -> str | None:
    """Push a Docker image to the configured registry.

    Args:
        image_name: Name for the image in the registry.
        tag: Image tag.
        local_image: Local image name to push.

    Returns:
        Full image URI.

    Example:
        push_image("ml-training", tag="v1.0", local_image="my-local-image")
    """
    registry = get_container_registry()

    if registry:
        return registry.push_image(image_name, tag, local_image)
    else:
        logger.warning("No container_registry configured in flowyml.yaml")
        return None


def get_image_uri(image_name: str, tag: str = "latest") -> str | None:
    """Get the full URI for an image.

    Args:
        image_name: Name of the image.
        tag: Image tag.

    Returns:
        Full image URI.
    """
    registry = get_container_registry()
    return registry.get_image_uri(image_name, tag) if registry else None


# =============================================================================
# PIPELINE ORCHESTRATION (Auto-routes to configured orchestrator)
# =============================================================================


def run_pipeline(
    pipeline: Any,
    run_id: str,
    parameters: dict = None,
    **kwargs,
) -> Any | None:
    """Run a pipeline on the configured orchestrator.

    Args:
        pipeline: The pipeline to run.
        run_id: Unique identifier for this run.
        parameters: Pipeline parameters.
        **kwargs: Additional orchestrator-specific arguments.

    Returns:
        Run result/job object.

    Example:
        run_pipeline(my_training_pipeline, "training-001",
                    parameters={"epochs": 100})
    """
    orchestrator = get_orchestrator()

    if orchestrator:
        return orchestrator.run_pipeline(pipeline, run_id, parameters=parameters, **kwargs)
    else:
        logger.warning("No orchestrator configured in flowyml.yaml")
        return None


# =============================================================================
# ALERTS (Auto-routes to configured alerter)
# =============================================================================


def send_alert(title: str, message: str, level: str = "info") -> bool:
    """Send an alert notification.

    Args:
        title: Alert title.
        message: Alert message.
        level: Alert level (info, warning, error, critical).

    Returns:
        True if alert was sent successfully.

    Example:
        send_alert("Training Complete", "Model accuracy: 95%", level="success")
    """
    alerter = get_alerter()

    if alerter:
        return alerter.send_alert(title, message, level)
    else:
        logger.info(f"[{level.upper()}] {title}: {message}")
        return True


# =============================================================================
# STACK INFO
# =============================================================================


def show_stack() -> dict[str, str]:
    """Show the currently configured stack.

    Returns:
        Dictionary of configured plugins.

    Example:
        stack = show_stack()
        print(stack)
        # {'experiment_tracker': 'mlflow', 'artifact_store': 'gcs', ...}
    """
    config = get_config()
    plugins_config = config.plugins_config

    stack = {}
    for role, conf in plugins_config.items():
        if isinstance(conf, dict):
            stack[role] = conf.get("type", "unknown")

    return stack


def validate_stack() -> dict[str, bool]:
    """Validate that all configured plugins are installed.

    Returns:
        Dictionary mapping plugin roles to installation status.
    """
    from flowyml.plugins import is_installed

    config = get_config()
    plugins_config = config.plugins_config

    results = {}
    for role, conf in plugins_config.items():
        if isinstance(conf, dict):
            plugin_type = conf.get("type")
            if plugin_type:
                results[role] = is_installed(plugin_type)

    return results

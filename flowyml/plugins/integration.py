"""FlowyML Pipeline-Plugin Integration.

This module integrates the native plugin system with FlowyML pipelines,
allowing pipelines to automatically use the configured stack for:
- Experiment tracking (log params, metrics)
- Artifact storage (save outputs)
- Model registry (register models)
- Orchestration (run on configured platform)

Usage:
    # flowyml.yaml
    plugins:
      experiment_tracker:
        type: mlflow
      artifact_store:
        type: gcs
        bucket: my-ml-artifacts

    # In code - pipeline automatically uses configured stack
    from flowyml import pipeline, step
    from flowyml.plugins.integration import run_with_stack

    @pipeline
    def training_pipeline():
        data = load_data()
        model = train(data)
        return model

    # Run with automatic tracking and artifact storage
    result = run_with_stack(training_pipeline)
"""

import logging
from typing import Any
from functools import wraps
import time

from flowyml.plugins.stack import (
    start_run,
    end_run,
    log_params,
    log_metrics,
    set_tag,
    save_artifact,
    save_model,
)

logger = logging.getLogger(__name__)


class StackContext:
    """Context manager for running code with automatic stack integration.

    Automatically:
    - Starts an experiment run
    - Logs timing and metadata
    - Saves artifacts to configured store
    - Ends the run with appropriate status

    Example:
        with StackContext("my_training") as ctx:
            # Your code here - automatically tracked
            model = train()
            ctx.log_model(model, "classifier")
    """

    def __init__(
        self,
        run_name: str,
        experiment_name: str = None,
        tags: dict = None,
        log_system_info: bool = True,
    ):
        """Initialize the stack context.

        Args:
            run_name: Name for this run.
            experiment_name: Optional experiment name.
            tags: Optional tags for the run.
            log_system_info: If True, log system information.
        """
        self.run_name = run_name
        self.experiment_name = experiment_name
        self.tags = tags or {}
        self.log_system_info = log_system_info
        self._run_id = None
        self._start_time = None
        self._artifacts = []
        self._models = []

    def __enter__(self) -> "StackContext":
        """Start the run."""
        self._start_time = time.time()
        self._run_id = start_run(
            self.run_name,
            experiment_name=self.experiment_name,
            tags=self.tags,
        )

        if self.log_system_info:
            self._log_system_info()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the run."""
        duration = time.time() - self._start_time

        # Log final metrics
        log_metrics({"duration_seconds": duration})

        if exc_type:
            set_tag("status", "FAILED")
            set_tag("error_type", exc_type.__name__)
            end_run("FAILED")
        else:
            set_tag("status", "COMPLETED")
            end_run("FINISHED")

        return False  # Don't suppress exceptions

    def _log_system_info(self):
        """Log system information."""
        import platform
        import sys

        try:
            log_params(
                {
                    "python_version": sys.version.split()[0],
                    "platform": platform.system(),
                    "machine": platform.machine(),
                },
            )
        except Exception as e:
            logger.debug(f"Could not log system info: {e}")

    def log_params(self, params: dict) -> None:
        """Log parameters."""
        log_params(params)

    def log_metrics(self, metrics: dict, step: int = None) -> None:
        """Log metrics."""
        log_metrics(metrics, step)

    def save_artifact(self, artifact: Any, path: str) -> str:
        """Save an artifact and track it.

        Returns:
            URI of the saved artifact.
        """
        uri = save_artifact(artifact, path)
        if uri:
            self._artifacts.append(uri)
            set_tag(f"artifact_{len(self._artifacts)}", uri)
        return uri

    def save_model(self, model: Any, path: str, model_type: str = None) -> str:
        """Save a model and track it.

        Returns:
            URI of the saved model.
        """
        uri = save_model(model, path, model_type=model_type)
        if uri:
            self._models.append(uri)
            set_tag(f"model_{len(self._models)}", uri)
        return uri


def run_with_stack(
    pipeline_or_func,
    run_name: str = None,
    experiment_name: str = None,
    parameters: dict = None,
    tags: dict = None,
):
    """Run a pipeline or function with automatic stack integration.

    This wraps the execution with:
    - Automatic experiment tracking
    - Parameter logging
    - Timing and metrics
    - Error handling

    Args:
        pipeline_or_func: Pipeline or callable to run.
        run_name: Name for this run (defaults to function name).
        experiment_name: Optional experiment name.
        parameters: Parameters to pass and log.
        tags: Optional tags for the run.

    Returns:
        Result of the pipeline/function.

    Example:
        @pipeline
        def my_training():
            ...

        # Run with full stack integration
        result = run_with_stack(
            my_training,
            run_name="training_v1",
            parameters={"lr": 0.001}
        )
    """
    # Determine run name
    if run_name is None:
        if hasattr(pipeline_or_func, "name"):
            run_name = pipeline_or_func.name
        elif hasattr(pipeline_or_func, "__name__"):
            run_name = pipeline_or_func.__name__
        else:
            run_name = "unnamed_run"

    parameters = parameters or {}
    tags = tags or {}

    with StackContext(run_name, experiment_name, tags) as ctx:
        # Log parameters
        if parameters:
            ctx.log_params(parameters)

        # Execute
        if parameters:
            result = pipeline_or_func(**parameters)
        else:
            result = pipeline_or_func()

        return result


def tracked(
    experiment_name: str = None,
    log_params: bool = True,
    log_result: bool = True,
):
    """Decorator to add automatic tracking to any function.

    The decorated function will automatically:
    - Start an experiment run
    - Log function parameters
    - Log execution time
    - End the run with status

    Args:
        experiment_name: Optional experiment name.
        log_params: If True, log function parameters.
        log_result: If True, log result summary.

    Example:
        @tracked(experiment_name="model_training")
        def train_model(lr=0.001, epochs=100):
            model = ...
            return model
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            run_name = func.__name__

            with StackContext(run_name, experiment_name) as ctx:
                # Log parameters
                if log_params and kwargs:
                    ctx.log_params(kwargs)

                # Execute
                result = func(*args, **kwargs)

                # Log result summary if applicable
                if log_result and isinstance(result, dict):
                    metrics = {k: v for k, v in result.items() if isinstance(v, (int, float))}
                    if metrics:
                        ctx.log_metrics(metrics)

                return result

        return wrapper

    return decorator


class PipelinePluginIntegration:
    """Integration layer between FlowyML pipelines and plugins.

    This class provides hooks for the pipeline executor to automatically
    use the configured stack.
    """

    def __init__(self):
        """Initialize the integration."""
        self._current_run = None
        self._step_outputs = {}

    def on_pipeline_start(self, pipeline_name: str, context: dict = None):
        """Called when a pipeline starts."""
        self._current_run = start_run(
            pipeline_name,
            tags={"type": "pipeline"},
        )

        if context:
            log_params(context)

    def on_pipeline_end(self, success: bool, error: Exception = None):
        """Called when a pipeline ends."""
        if success:
            end_run("FINISHED")
        else:
            if error:
                set_tag("error", str(error))
            end_run("FAILED")

        self._current_run = None

    def on_step_start(self, step_name: str, inputs: dict = None):
        """Called when a step starts."""
        set_tag(f"step_{step_name}_status", "started")

        if inputs:
            # Log input sizes/shapes if applicable
            for key, value in inputs.items():
                if hasattr(value, "shape"):
                    set_tag(f"input_{key}_shape", str(value.shape))

    def on_step_end(
        self,
        step_name: str,
        outputs: dict = None,
        duration: float = None,
        cached: bool = False,
    ):
        """Called when a step ends."""
        set_tag(f"step_{step_name}_status", "completed")

        if duration:
            log_metrics({f"{step_name}_duration": duration})

        if cached:
            set_tag(f"step_{step_name}_cached", "true")

        # Store outputs for later saving
        if outputs:
            self._step_outputs[step_name] = outputs

    def on_step_error(self, step_name: str, error: Exception):
        """Called when a step errors."""
        set_tag(f"step_{step_name}_status", "failed")
        set_tag(f"step_{step_name}_error", str(error))

    def save_step_outputs(self, step_name: str, outputs: dict):
        """Save step outputs to the artifact store."""
        for output_name, value in outputs.items():
            path = f"steps/{step_name}/{output_name}"
            save_artifact(value, path)


# Global integration instance
_integration: PipelinePluginIntegration | None = None


def get_integration() -> PipelinePluginIntegration:
    """Get the global pipeline-plugin integration."""
    global _integration
    if _integration is None:
        _integration = PipelinePluginIntegration()
    return _integration

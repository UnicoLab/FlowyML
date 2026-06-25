"""FlowyML Pipeline-Plugin Integration — Transparent Dual-Write Tracking.

This module integrates the native plugin system with FlowyML pipelines,
enabling **automatic, transparent experiment tracking** on every
``pipeline.run()`` call.

Architecture (dual-write):

    Pipeline.run()
        │
        ├──► FlowyML Internal Store   (SQLite — always, for UI dashboard)
        │       └── via _save_run() / _log_experiment_metrics()
        │
        └──► External Tracker          (MLflow / WandB / etc. — from stack config)
                └── via PipelinePluginIntegration hooks

The integration automatically resolves the experiment tracker from:
    1. Stack's experiment_tracker config (flowyml.yaml → stacks → <name> → experiment_tracker)
    2. Plugin config (flowyml.yaml → plugins → experiment_tracker)
    3. Environment variable FLOWYML_TRACKER_TYPE

Usage::

    # flowyml.yaml — just configure, never touch integration code
    stacks:
      production:
        experiment_tracker:
          type: mlflow
          tracking_uri: http://mlflow:5000

    # In code — tracking is 100% transparent
    pipeline = Pipeline("training", context=ctx, stack="production")
    result = pipeline.run()  # Auto-logs params, metrics, artifacts to MLflow AND FlowyML
"""

import logging
import time
from typing import Any
from functools import wraps

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
    """Integration layer between FlowyML pipelines and external trackers.

    This class provides hooks that are called automatically during pipeline
    execution to forward tracking data to the stack-configured external
    experiment tracker (MLflow, WandB, etc.).

    The integration implements a **dual-write** pattern:
    - FlowyML's internal store (SQLite) is always written to by Pipeline._save_run()
    - This class forwards the same data to the external tracker

    The tracker is resolved lazily from:
    1. Explicit tracker passed to constructor
    2. Stack's experiment_tracker (from flowyml.yaml stacks section)
    3. Plugin config (from flowyml.yaml plugins section)
    """

    def __init__(self, tracker: Any = None):
        """Initialize the integration.

        Args:
            tracker: Optional explicit experiment tracker instance.
                     If None, auto-resolved from stack/plugin config.
        """
        self._explicit_tracker = tracker
        self._tracker = None
        self._tracker_resolved = False
        self._current_run = None
        self._step_outputs = {}
        self._pipeline_name = None
        self._run_id = None

    def _resolve_tracker(self) -> Any:
        """Lazily resolve the experiment tracker from stack or plugin config.

        Resolution order:
        1. Explicit tracker passed to constructor
        2. Stack experiment_tracker from flowyml.yaml
        3. Plugin experiment_tracker from flowyml.yaml
        """
        if self._tracker_resolved:
            return self._tracker

        self._tracker_resolved = True

        # 1. Explicit tracker
        if self._explicit_tracker is not None:
            self._tracker = self._explicit_tracker
            logger.debug("Using explicitly provided experiment tracker")
            return self._tracker

        # 2. Try stack config → plugins → experiment_tracker
        try:
            from flowyml.plugins.config import get_tracker

            tracker = get_tracker()
            if tracker:
                self._tracker = tracker
                logger.debug(
                    "Resolved experiment tracker from stack/plugin config: %s",
                    type(tracker).__name__,
                )
                return self._tracker
        except Exception as e:
            logger.debug(f"Could not resolve tracker from config: {e}")

        logger.debug("No external experiment tracker configured — FlowyML-only tracking active")
        return None

    @property
    def has_tracker(self) -> bool:
        """Check if an external tracker is available."""
        return self._resolve_tracker() is not None

    def on_pipeline_start(
        self,
        pipeline_name: str,
        run_id: str,
        context: dict = None,
        tags: dict = None,
    ) -> None:
        """Called when a pipeline starts — opens a run on the external tracker.

        Args:
            pipeline_name: Name of the pipeline.
            run_id: Unique run identifier.
            context: Pipeline context parameters to log.
            tags: Additional tags for the run.
        """
        self._pipeline_name = pipeline_name
        self._run_id = run_id

        tracker = self._resolve_tracker()
        if tracker is None:
            return

        try:
            # Build tags
            run_tags = {
                "flowyml.pipeline": pipeline_name,
                "flowyml.run_id": run_id,
                "flowyml.source": "pipeline.run()",
            }
            if tags:
                run_tags.update(tags)

            # Start run on external tracker
            tracker.start_run(
                run_name=f"{pipeline_name}_{run_id[:8]}",
                experiment_name=pipeline_name,
                tags=run_tags,
            )
            self._current_run = run_id

            # Log context parameters
            if context:
                # Flatten and stringify for tracker compatibility
                safe_params = {}
                for k, v in context.items():
                    try:
                        safe_params[k] = str(v) if not isinstance(v, (int, float, str, bool)) else v
                    except Exception:
                        safe_params[k] = repr(v)
                tracker.log_params(safe_params)

            logger.info(
                "External tracker run started: %s (tracker: %s)",
                pipeline_name,
                type(tracker).__name__,
            )
        except Exception as e:
            logger.warning("Failed to start external tracker run: %s", e)

    def on_pipeline_end(self, success: bool, result: Any = None, error: Exception = None) -> None:
        """Called when a pipeline ends — closes the run on the external tracker.

        Also forwards final metrics extracted from the pipeline result.

        Args:
            success: Whether the pipeline succeeded.
            result: PipelineResult object.
            error: Exception if the pipeline failed.
        """
        tracker = self._resolve_tracker()
        if tracker is None or self._current_run is None:
            return

        try:
            # Log final pipeline-level metrics
            if result is not None:
                final_metrics = {}

                # Duration
                if hasattr(result, "duration_seconds"):
                    final_metrics["pipeline_duration_seconds"] = result.duration_seconds

                # Step-level summary metrics
                if hasattr(result, "step_results"):
                    total_steps = len(result.step_results)
                    cached_steps = sum(1 for r in result.step_results.values() if getattr(r, "cached", False))
                    final_metrics["total_steps"] = total_steps
                    final_metrics["cached_steps"] = cached_steps

                    # Log per-step durations
                    for step_name, step_result in result.step_results.items():
                        if hasattr(step_result, "duration_seconds"):
                            final_metrics[f"step.{step_name}.duration_seconds"] = step_result.duration_seconds

                # Extract Metrics assets from outputs
                if hasattr(result, "outputs"):
                    self._forward_metrics_from_outputs(tracker, result.outputs)

                if final_metrics:
                    tracker.log_metrics(final_metrics)

            # Set final status tag
            if hasattr(tracker, "set_tag"):
                tracker.set_tag("flowyml.status", "success" if success else "failed")
                if error:
                    tracker.set_tag("flowyml.error", str(error)[:250])

            # End the run
            status = "FINISHED" if success else "FAILED"
            tracker.end_run(status)

            logger.info(
                "External tracker run ended: %s (status: %s)",
                self._pipeline_name,
                status,
            )
        except Exception as e:
            logger.warning("Failed to end external tracker run: %s", e)
        finally:
            self._current_run = None

    def _forward_metrics_from_outputs(self, tracker: Any, outputs: dict) -> None:
        """Extract Metrics assets from pipeline outputs and forward to tracker.

        Args:
            tracker: The experiment tracker to log to.
            outputs: Pipeline output dictionary.
        """
        try:
            from flowyml.assets.metrics import Metrics

            for output_name, output_value in outputs.items():
                if isinstance(output_value, Metrics):
                    # Extract numeric metrics from Metrics asset
                    metrics_dict = output_value.get_all_metrics() or output_value.data or {}
                    if isinstance(metrics_dict, dict):
                        safe_metrics = {}
                        for k, v in metrics_dict.items():
                            if isinstance(v, (int, float)):
                                # Use clean key names for top-level metrics outputs
                                if output_name in ("metrics", "eval_metrics") or output_name.endswith("/metrics"):
                                    safe_metrics[k] = v
                                else:
                                    safe_metrics[f"{output_name}.{k}"] = v
                        if safe_metrics:
                            tracker.log_metrics(safe_metrics)
                elif isinstance(output_value, dict):
                    # Check for nested Metrics objects
                    for key, val in output_value.items():
                        if isinstance(val, Metrics):
                            metrics_dict = val.get_all_metrics() or val.data or {}
                            if isinstance(metrics_dict, dict):
                                safe_metrics = {
                                    f"{key}.{k}": v for k, v in metrics_dict.items() if isinstance(v, (int, float))
                                }
                                if safe_metrics:
                                    tracker.log_metrics(safe_metrics)
        except ImportError:
            pass  # Metrics asset not available

    def on_step_start(self, step_name: str, inputs: dict = None) -> None:
        """Called when a step starts."""
        tracker = self._resolve_tracker()
        if tracker is None or self._current_run is None:
            return

        try:
            if hasattr(tracker, "set_tag"):
                tracker.set_tag(f"step.{step_name}.status", "running")
        except Exception:
            pass

    def on_step_end(
        self,
        step_name: str,
        outputs: dict = None,
        duration: float = None,
        cached: bool = False,
        auto_metrics: dict[str, float | int] | None = None,
    ) -> None:
        """Called when a step ends — logs step metrics to external tracker.

        Args:
            step_name: Name of the step.
            outputs: Step output data.
            duration: Step execution duration in seconds.
            cached: Whether the step result was from cache.
            auto_metrics: Metrics auto-extracted by AutoTracker from step output.
                These are forwarded to the external tracker in real-time.
        """
        tracker = self._resolve_tracker()
        if tracker is None or self._current_run is None:
            return

        try:
            if hasattr(tracker, "set_tag"):
                tracker.set_tag(f"step.{step_name}.status", "completed")
                if cached:
                    tracker.set_tag(f"step.{step_name}.cached", "true")

            if duration is not None:
                tracker.log_metrics({f"step.{step_name}.duration_seconds": duration})

            # Forward auto-tracked step metrics to external tracker
            if auto_metrics:
                safe_metrics = {k: v for k, v in auto_metrics.items() if isinstance(v, (int, float))}
                if safe_metrics:
                    tracker.log_metrics(safe_metrics)
        except Exception:
            pass

    def on_step_error(self, step_name: str, error: Exception) -> None:
        """Called when a step errors."""
        tracker = self._resolve_tracker()
        if tracker is None or self._current_run is None:
            return

        try:
            if hasattr(tracker, "set_tag"):
                tracker.set_tag(f"step.{step_name}.status", "failed")
                tracker.set_tag(f"step.{step_name}.error", str(error)[:250])
        except Exception:
            pass

    def save_step_outputs(self, step_name: str, outputs: dict) -> None:
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


def reset_integration() -> None:
    """Reset the global integration (useful for testing)."""
    global _integration
    _integration = None

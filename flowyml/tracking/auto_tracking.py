"""Auto-Tracking — Automatic metrics and parameter collection for pipeline runs.

This module provides the ``AutoTracker`` class that transparently collects
metrics and parameters during pipeline execution without requiring manual
instrumentation.

It gathers data from four sources:

1. **Context parameters** — all key-value pairs from the pipeline context
2. **Stack configuration** — executor type, artifact store, etc.
3. **Environment info** — Python version, key ML package versions, GPU
4. **Step outputs** — numeric scalars, dicts with numeric values, ``Metrics`` assets

Usage::

    # AutoTracker is integrated into Pipeline automatically when auto_track=True.
    # You rarely need to interact with it directly.

    pipeline = Pipeline("training", context=ctx, auto_track=True)  # default
    result = pipeline.run()
    # → All parameters, metrics, and environment info are logged automatically

    # Advanced: manual interaction
    from flowyml.tracking.auto_tracking import AutoTracker

    tracker = AutoTracker()
    tracker.collect_parameters(pipeline)
    tracker.extract_step_metrics("evaluate", step_result)
    tracker.finalize_run(result)
"""

import logging
import platform
import sys
from typing import Any

logger = logging.getLogger(__name__)


class AutoTracker:
    """Automatic metrics and parameter collection for pipeline runs.

    Collects from:
    - Pipeline context (all parameters)
    - Stack configuration (executor, artifact store, etc.)
    - System/environment info (Python version, packages, GPU)
    - Step outputs (numeric scalars, dicts, Metrics assets)
    - Step execution metadata (duration, cached, retries)

    Example::

        tracker = AutoTracker()
        tracker.collect_parameters(pipeline)

        # After each step:
        tracker.extract_step_metrics("train_model", step_result)
        tracker.extract_step_metrics("evaluate", step_result)

        # At pipeline end:
        tracker.finalize_run(pipeline_result)
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

        # Collected data
        self._parameters: dict[str, Any] = {}
        self._metrics: dict[str, float | int] = {}
        self._step_metrics: dict[str, dict[str, Any]] = {}  # step_name -> metrics
        self._tags: dict[str, str] = {}
        self._environment: dict[str, Any] = {}
        self._stack_info: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Parameter collection
    # ------------------------------------------------------------------

    def collect_parameters(self, pipeline: Any) -> dict[str, Any]:
        """Gather all trackable parameters from the pipeline.

        Collects from:
        - Pipeline context (hyperparameters, config values)
        - Stack configuration (executor, stores, etc.)
        - System/environment info

        Args:
            pipeline: Pipeline instance to collect from.

        Returns:
            Flat dict of all collected parameters.
        """
        if not self.enabled:
            return {}

        # 1. Context parameters
        if hasattr(pipeline, "context") and pipeline.context:
            context_params = self._extract_context_params(pipeline.context)
            self._parameters.update(context_params)

        # 2. Stack configuration
        if hasattr(pipeline, "stack") and pipeline.stack:
            stack_info = self.collect_stack_info(pipeline.stack)
            self._stack_info = stack_info
            # Prefix stack params to avoid collisions with context
            for k, v in stack_info.items():
                self._parameters[f"stack.{k}"] = v

        # 3. Environment info
        env_info = self.collect_environment_info()
        self._environment = env_info
        for k, v in env_info.items():
            self._parameters[f"env.{k}"] = v

        # 4. Pipeline metadata
        if hasattr(pipeline, "name"):
            self._tags["pipeline_name"] = pipeline.name
        if hasattr(pipeline, "project_name") and pipeline.project_name:
            self._tags["project_name"] = pipeline.project_name

        logger.debug(
            "AutoTracker collected %d parameters from pipeline '%s'",
            len(self._parameters),
            getattr(pipeline, "name", "unknown"),
        )

        return dict(self._parameters)

    def _extract_context_params(self, context: Any) -> dict[str, Any]:
        """Extract trackable parameters from a Context object.

        Filters out non-serializable values and truncates long strings.

        Args:
            context: Context instance.

        Returns:
            Dict of clean, serializable parameters.
        """
        raw_params = {}

        # Use to_dict() if available (handles parent inheritance)
        if hasattr(context, "to_dict"):
            raw_params = context.to_dict()
        elif hasattr(context, "_params"):
            raw_params = dict(context._params)

        # Filter and clean
        return self._make_trackable(raw_params)

    # ------------------------------------------------------------------
    # Stack & environment info
    # ------------------------------------------------------------------

    def collect_stack_info(self, stack: Any) -> dict[str, Any]:
        """Collect stack configuration as trackable parameters.

        Args:
            stack: Stack instance.

        Returns:
            Dict of stack configuration info.
        """
        info: dict[str, Any] = {}

        try:
            if hasattr(stack, "name"):
                info["name"] = str(stack.name)

            if hasattr(stack, "executor") and stack.executor:
                info["executor_type"] = type(stack.executor).__name__

            if hasattr(stack, "artifact_store") and stack.artifact_store:
                info["artifact_store_type"] = type(stack.artifact_store).__name__

            if hasattr(stack, "metadata_store") and stack.metadata_store:
                info["metadata_store_type"] = type(stack.metadata_store).__name__

            if hasattr(stack, "orchestrator") and stack.orchestrator:
                info["orchestrator_type"] = type(stack.orchestrator).__name__

            if hasattr(stack, "model_deployer") and stack.model_deployer:
                info["model_deployer_type"] = type(stack.model_deployer).__name__

            if hasattr(stack, "container_registry") and stack.container_registry:
                info["container_registry_type"] = type(stack.container_registry).__name__
        except Exception as e:
            logger.debug("Failed to collect stack info: %s", e)

        return info

    def collect_environment_info(self) -> dict[str, Any]:
        """Collect system and environment information.

        Returns:
            Dict with Python version, platform, key ML package versions,
            and GPU availability.
        """
        info: dict[str, Any] = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
        }

        # Detect key ML package versions
        for pkg_name in ("numpy", "pandas", "scikit-learn", "torch", "tensorflow", "keras", "xgboost", "lightgbm"):
            try:
                mod = __import__(pkg_name.replace("-", "_").replace("scikit_learn", "sklearn"))
                version = getattr(mod, "__version__", None)
                if version:
                    info[f"{pkg_name}_version"] = str(version)
            except ImportError:
                pass

        # GPU detection
        try:
            import torch

            if torch.cuda.is_available():
                info["gpu_available"] = True
                info["gpu_count"] = torch.cuda.device_count()
                info["gpu_name"] = torch.cuda.get_device_name(0)
            else:
                info["gpu_available"] = False
        except ImportError:
            info["gpu_available"] = False

        return info

    # ------------------------------------------------------------------
    # Step metrics extraction
    # ------------------------------------------------------------------

    def extract_step_metrics(
        self,
        step_name: str,
        step_result: Any,
        step_outputs: list[str] | None = None,
    ) -> dict[str, float | int]:
        """Extract numeric metrics from a step's result.

        Handles three output types:
        1. ``Metrics`` asset — extracts all metric values
        2. Plain dict — extracts numeric (int/float) values
        3. Scalar numeric — tracks as ``step_name.output``

        Also captures execution metadata (duration, cached, retries).

        Args:
            step_name: Name of the step.
            step_result: ExecutionResult from step execution.
            step_outputs: Optional list of declared output names.

        Returns:
            Dict of extracted metrics with namespaced keys.
        """
        if not self.enabled:
            return {}

        extracted: dict[str, float | int] = {}

        # 1. Execution metadata
        if hasattr(step_result, "duration_seconds") and step_result.duration_seconds is not None:
            extracted[f"{step_name}.duration_seconds"] = step_result.duration_seconds

        if hasattr(step_result, "cached") and step_result.cached:
            extracted[f"{step_name}.cached"] = 1

        if hasattr(step_result, "retries") and step_result.retries:
            extracted[f"{step_name}.retries"] = step_result.retries

        # 2. Output metrics extraction
        output = getattr(step_result, "output", None)
        if output is not None:
            output_metrics = self._extract_metrics_from_output(step_name, output)
            extracted.update(output_metrics)

        # Store per-step
        self._step_metrics[step_name] = extracted

        # Merge into global metrics
        self._metrics.update(extracted)

        logger.debug(
            "AutoTracker extracted %d metrics from step '%s'",
            len(extracted),
            step_name,
        )

        return extracted

    def _extract_metrics_from_output(
        self,
        step_name: str,
        output: Any,
    ) -> dict[str, float | int]:
        """Extract numeric metrics from a step output value.

        Args:
            step_name: Name of the step (used as prefix).
            output: The step's output value.

        Returns:
            Dict of extracted numeric metrics.
        """
        extracted: dict[str, float | int] = {}

        # Determine if step name should be used as prefix
        # Steps named "evaluate", "metrics", "score" etc. get clean keys
        clean_names = {"evaluate", "eval", "metrics", "score", "test", "validate"}
        use_prefix = step_name not in clean_names and not step_name.startswith("eval")

        def _make_key(metric_name: str) -> str:
            if use_prefix:
                return f"{step_name}.{metric_name}"
            return metric_name

        # Check for Metrics asset
        try:
            from flowyml.assets.metrics import Metrics

            if isinstance(output, Metrics):
                metrics_dict = output.get_all_metrics() or output.data or {}
                if isinstance(metrics_dict, dict):
                    for k, v in metrics_dict.items():
                        if isinstance(v, (int, float)):
                            extracted[_make_key(k)] = v
                return extracted
        except ImportError:
            pass

        # Plain dict — extract numeric values
        if isinstance(output, dict):
            for k, v in output.items():
                if isinstance(v, (int, float)):
                    extracted[_make_key(k)] = v
                # Check for nested Metrics
                try:
                    from flowyml.assets.metrics import Metrics

                    if isinstance(v, Metrics):
                        nested = v.get_all_metrics() or v.data or {}
                        if isinstance(nested, dict):
                            for nk, nv in nested.items():
                                if isinstance(nv, (int, float)):
                                    extracted[f"{step_name}.{k}.{nk}"] = nv
                except ImportError:
                    pass

        # Scalar numeric
        elif isinstance(output, (int, float)):
            extracted[f"{step_name}.output"] = output

        # Tuple/list — check for numeric elements
        elif isinstance(output, (list, tuple)):
            for i, v in enumerate(output):
                if isinstance(v, (int, float)):
                    extracted[f"{step_name}.output_{i}"] = v
                # Check for Metrics in tuple
                try:
                    from flowyml.assets.metrics import Metrics

                    if isinstance(v, Metrics):
                        nested = v.get_all_metrics() or v.data or {}
                        if isinstance(nested, dict):
                            for nk, nv in nested.items():
                                if isinstance(nv, (int, float)):
                                    extracted[f"{step_name}.{nk}"] = nv
                except ImportError:
                    pass

        return extracted

    # ------------------------------------------------------------------
    # Run finalization
    # ------------------------------------------------------------------

    def finalize_run(
        self,
        pipeline: Any,
        result: Any,
    ) -> tuple[dict[str, Any], dict[str, float | int]]:
        """Finalize auto-tracking for a completed pipeline run.

        Aggregates all collected parameters and metrics, logs them to
        FlowyML's internal experiment tracking system, and returns the
        collected data for external tracker forwarding.

        Args:
            pipeline: Pipeline instance.
            result: PipelineResult instance.

        Returns:
            Tuple of (parameters_dict, metrics_dict).
        """
        if not self.enabled:
            return {}, {}

        # Add pipeline-level execution metrics
        if hasattr(result, "duration_seconds") and result.duration_seconds:
            self._metrics["pipeline.duration_seconds"] = result.duration_seconds

        if hasattr(result, "step_results"):
            total_steps = len(result.step_results)
            cached_steps = sum(1 for r in result.step_results.values() if getattr(r, "cached", False))
            self._metrics["pipeline.total_steps"] = total_steps
            self._metrics["pipeline.cached_steps"] = cached_steps

        # Extract any remaining metrics from outputs not yet processed
        # (safety net for steps that might have been missed)
        if hasattr(result, "outputs"):
            for output_name, output_value in result.outputs.items():
                if output_name not in self._step_metrics:
                    self._extract_metrics_from_output(output_name, output_value)

        # Log to internal experiment tracking
        self._log_to_internal_tracker(pipeline, result)

        logger.info(
            "AutoTracker finalized: %d parameters, %d metrics for run '%s'",
            len(self._parameters),
            len(self._metrics),
            getattr(result, "run_id", "unknown"),
        )

        return dict(self._parameters), dict(self._metrics)

    def _log_to_internal_tracker(self, pipeline: Any, result: Any) -> None:
        """Log collected data to FlowyML's internal experiment tracking.

        Args:
            pipeline: Pipeline instance.
            result: PipelineResult with run_id and outputs.
        """
        if not self._parameters and not self._metrics:
            return

        try:
            from flowyml.tracking.experiment import Experiment
            from flowyml.tracking.runs import Run

            # Create or get experiment
            experiment_name = getattr(pipeline, "name", "default")
            experiment = Experiment(
                name=experiment_name,
                description=f"Auto-tracked experiment for pipeline: {experiment_name}",
            )

            run_id = getattr(result, "run_id", "unknown")

            # Log run to experiment
            experiment.log_run(
                run_id=run_id,
                metrics=self._metrics,
                parameters=self._parameters,
            )

            # Also create/update Run object
            run = Run(
                run_id=run_id,
                pipeline_name=experiment_name,
                parameters=self._parameters,
            )
            if self._metrics:
                run.log_metrics(self._metrics)
            run.complete(
                status="success" if getattr(result, "success", False) else "failed",
            )

        except Exception as e:
            import warnings

            warnings.warn(f"AutoTracker: Failed to log to internal tracker: {e}", stacklevel=2)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def parameters(self) -> dict[str, Any]:
        """All collected parameters."""
        return dict(self._parameters)

    @property
    def metrics(self) -> dict[str, float | int]:
        """All collected metrics."""
        return dict(self._metrics)

    @property
    def tags(self) -> dict[str, str]:
        """All collected tags."""
        return dict(self._tags)

    def get_step_metrics(self, step_name: str) -> dict[str, Any]:
        """Get metrics for a specific step.

        Args:
            step_name: Name of the step.

        Returns:
            Dict of metrics for that step, or empty dict.
        """
        return dict(self._step_metrics.get(step_name, {}))

    def reset(self) -> None:
        """Reset all collected data (for reuse across runs)."""
        self._parameters.clear()
        self._metrics.clear()
        self._step_metrics.clear()
        self._tags.clear()
        self._environment.clear()
        self._stack_info.clear()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_trackable(params: dict[str, Any]) -> dict[str, Any]:
        """Convert a parameter dict to tracker-safe values.

        - Filters out non-serializable values
        - Truncates long strings to 250 chars
        - Converts non-primitive types to str

        Args:
            params: Raw parameter dict.

        Returns:
            Cleaned parameter dict.
        """
        clean: dict[str, Any] = {}

        for k, v in params.items():
            # Skip private/internal keys
            if k.startswith("_"):
                continue

            if isinstance(v, (int, float, bool)):
                clean[k] = v
            elif isinstance(v, str):
                clean[k] = v[:250] if len(v) > 250 else v
            elif v is None:
                clean[k] = None
            else:
                # Try to convert to string representation
                try:
                    str_val = str(v)
                    clean[k] = str_val[:250] if len(str_val) > 250 else str_val
                except Exception:
                    clean[k] = f"<{type(v).__name__}>"

        return clean

    def __repr__(self) -> str:
        return (
            f"AutoTracker(params={len(self._parameters)}, "
            f"metrics={len(self._metrics)}, "
            f"steps={len(self._step_metrics)})"
        )

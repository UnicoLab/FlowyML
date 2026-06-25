"""Step Runner — Remote container entrypoint for executing specific steps.

This module enables per-step-group execution in remote containers (Vertex AI,
Kubernetes, etc.). The orchestrator submits a container that invokes this runner
with environment variables specifying which steps to execute.

How it works (ZenML-parity pattern):
    1. Local orchestrator analyzes DAG → splits into execution groups
    2. Builds & pushes Docker image with the full project
    3. For each group, submits a container with:
       - FLOWYML_PIPELINE_MODULE  = "payment_twin.pipelines.master_pipeline:build_master_pipeline"
       - FLOWYML_STEP_NAMES       = "data_generate,data_validate_config,..."
       - FLOWYML_RUN_ID           = "abc123"
       - FLOWYML_EXECUTION_GROUP  = "data_group"
    4. This StepRunner reads those env vars, reconstructs the pipeline,
       and runs ONLY the specified steps

Artifact passing between groups:
    - Step outputs are serialized to GCS (or local disk for development)
    - Step inputs are loaded from the artifact store on demand
    - This allows each group to run in a separate container
"""

from __future__ import annotations

import importlib
import logging
import os
import time
from typing import Any

logger = logging.getLogger("flowyml.step_runner")


class StepRunner:
    """Executes specific pipeline steps inside a remote container.

    This is the core entrypoint for per-group remote execution. It:
    1. Discovers the pipeline via a module path
    2. Filters to only the requested steps
    3. Loads inputs from artifact store (GCS for cross-group dependencies)
    4. Runs the steps in topological order
    5. Serializes outputs to artifact store for downstream groups

    Attributes:
        pipeline_module: Dotted module path to the pipeline builder function
        step_names: List of step names to execute
        run_id: Unique run identifier for artifact namespacing
        group_name: Execution group name (for logging)
    """

    def __init__(
        self,
        pipeline_module: str,
        step_names: list[str],
        run_id: str,
        group_name: str = "",
        artifact_dir: str | None = None,
        staging_bucket: str | None = None,
    ):
        self.pipeline_module = pipeline_module
        self.step_names = step_names
        self.run_id = run_id
        self.group_name = group_name
        self.artifact_dir = artifact_dir or os.environ.get(
            "FLOWYML_ARTIFACT_DIR",
            "/tmp/flowyml_artifacts",  # noqa: S108
        )
        self.staging_bucket = staging_bucket or os.environ.get(
            "FLOWYML_STAGING_BUCKET",
            "",
        )

    @classmethod
    def from_env(cls) -> StepRunner:
        """Create a StepRunner from environment variables.

        Expected env vars:
            FLOWYML_PIPELINE_MODULE: module:function (e.g., "my.mod:build_pipe")
            FLOWYML_STEP_NAMES: Comma-separated step names
            FLOWYML_RUN_ID: Run identifier
            FLOWYML_EXECUTION_GROUP: Group name (optional)
            FLOWYML_ARTIFACT_DIR: Local artifact directory (optional)
            FLOWYML_STAGING_BUCKET: GCS staging bucket for cross-group artifacts
        """
        module = os.environ.get("FLOWYML_PIPELINE_MODULE", "")
        step_names_str = os.environ.get("FLOWYML_STEP_NAMES", "")
        run_id = os.environ.get("FLOWYML_RUN_ID", "")
        group_name = os.environ.get("FLOWYML_EXECUTION_GROUP", "")
        artifact_dir = os.environ.get("FLOWYML_ARTIFACT_DIR")
        staging_bucket = os.environ.get("FLOWYML_STAGING_BUCKET", "")

        if not module:
            raise ValueError("FLOWYML_PIPELINE_MODULE environment variable is required")
        if not step_names_str:
            raise ValueError("FLOWYML_STEP_NAMES environment variable is required")
        if not run_id:
            raise ValueError("FLOWYML_RUN_ID environment variable is required")

        step_names = [s.strip() for s in step_names_str.split(",") if s.strip()]

        return cls(
            pipeline_module=module,
            step_names=step_names,
            run_id=run_id,
            group_name=group_name,
            artifact_dir=artifact_dir,
            staging_bucket=staging_bucket,
        )

    def _create_artifact_store(self) -> Any:
        """Create the appropriate artifact store (GCS or local)."""
        from flowyml.core.artifact_store import create_artifact_store

        return create_artifact_store(
            run_id=self.run_id,
            staging_bucket=self.staging_bucket if self.staging_bucket else None,
            local_dir=self.artifact_dir,
        )

    def discover_pipeline(self) -> Any:
        """Import and build the pipeline from the module path.

        Supports two formats:
            - "module.path:function_name"  → calls function()
            - "module.path:PipelineClass"  → instantiates class

        Returns:
            Built Pipeline object
        """
        if ":" not in self.pipeline_module:
            raise ValueError(
                f"Invalid pipeline module format: {self.pipeline_module!r}. Expected 'module.path:builder_function'",
            )

        module_path, attr_name = self.pipeline_module.rsplit(":", 1)
        logger.info("Importing pipeline from %s:%s", module_path, attr_name)

        mod = importlib.import_module(module_path)
        builder = getattr(mod, attr_name)

        # Call if it's a function (builder pattern)
        if callable(builder) and not isinstance(builder, type):
            pipeline = builder()
        else:
            pipeline = builder

        # Build the DAG if not already built
        if hasattr(pipeline, "_built") and not pipeline._built:
            pipeline.build()

        logger.info(
            "Pipeline '%s' discovered: %d total steps",
            pipeline.name,
            len(pipeline.steps),
        )
        return pipeline

    def run(self) -> dict[str, Any]:
        """Execute the requested steps and return their outputs.

        Returns:
            Dictionary of {step_name: result} for all executed steps
        """
        start = time.time()
        group_label = f"[{self.group_name}] " if self.group_name else ""

        logger.info(
            "%s🚀 StepRunner starting | run_id=%s | steps=%s",
            group_label,
            self.run_id,
            self.step_names,
        )

        # 1. Create artifact store
        store = self._create_artifact_store()
        store_type = "GCS" if self.staging_bucket else "local"
        logger.info("  Artifact store: %s", store_type)

        # 2. Discover pipeline
        pipeline = self.discover_pipeline()

        # 3. Filter to requested steps
        step_map = {s.name: s for s in pipeline.steps}
        requested_steps = []
        for name in self.step_names:
            if name in step_map:
                requested_steps.append(step_map[name])
            else:
                logger.warning(
                    "Step '%s' not found in pipeline '%s'. Available: %s",
                    name,
                    pipeline.name,
                    list(step_map.keys()),
                )

        if not requested_steps:
            raise ValueError(
                f"No valid steps found. Requested: {self.step_names}, Available: {list(step_map.keys())}",
            )

        # 4. Get topological order within our subset
        ordered_steps = self._topological_sort(requested_steps, pipeline)

        logger.info(
            "%s📋 Execution plan: %s",
            group_label,
            [s.name for s in ordered_steps],
        )

        # 5. Execute steps sequentially
        results: dict[str, Any] = {}
        artifacts: dict[str, Any] = {}  # In-memory artifact cache

        for i, step in enumerate(ordered_steps):
            step_start = time.time()
            logger.info(
                "%s⏳ %s running... (%d/%d)",
                group_label,
                step.name,
                i + 1,
                len(ordered_steps),
            )

            # Resolve inputs — try memory cache first, then artifact store
            kwargs = {}
            for input_name in step.inputs:
                if input_name in artifacts:
                    kwargs[input_name] = artifacts[input_name]
                else:
                    # Cross-group dependency: load from artifact store
                    try:
                        if store.exists(input_name):
                            loaded = store.load(input_name)
                            kwargs[input_name] = loaded
                            artifacts[input_name] = loaded
                        else:
                            logger.warning(
                                "  ⚠️  Input '%s' not found in artifact store",
                                input_name,
                            )
                    except Exception as e:
                        logger.warning(
                            "  ⚠️  Failed to load '%s' from artifact store: %s",
                            input_name,
                            e,
                        )

            # Execute the step function
            try:
                result = step(**kwargs)
                elapsed = time.time() - step_start
                logger.info(
                    "%s✅ %s (%.2fs)",
                    group_label,
                    step.name,
                    elapsed,
                )
            except Exception as e:
                elapsed = time.time() - step_start
                logger.error(
                    "%s❌ %s FAILED (%.2fs): %s",
                    group_label,
                    step.name,
                    elapsed,
                    e,
                )
                raise

            results[step.name] = result

            # Persist outputs to artifact store for downstream groups
            if step.outputs:
                if isinstance(result, tuple) and len(result) == len(step.outputs):
                    for out_name, val in zip(step.outputs, result, strict=False):
                        artifacts[out_name] = val
                        try:
                            store.save(out_name, val)
                        except Exception as e:
                            logger.error(
                                "  ❌ Failed to save artifact '%s' (%s): %s",
                                out_name,
                                type(val).__name__,
                                e,
                            )
                            raise RuntimeError(
                                f"Artifact '{out_name}' could not be serialized to artifact store: {e}",
                            ) from e
                elif len(step.outputs) == 1:
                    artifacts[step.outputs[0]] = result
                    try:
                        store.save(step.outputs[0], result)
                    except Exception as e:
                        logger.error(
                            "  ❌ Failed to save artifact '%s' (%s): %s",
                            step.outputs[0],
                            type(result).__name__,
                            e,
                        )
                        raise RuntimeError(
                            f"Artifact '{step.outputs[0]}' could not be serialized to artifact store: {e}",
                        ) from e
                else:
                    # Multiple declared outputs but single return value
                    # Store under first name (user responsibility to match)
                    artifacts[step.outputs[0]] = result
                    try:
                        store.save(step.outputs[0], result)
                    except Exception as e:
                        logger.error(
                            "  ❌ Failed to save artifact '%s' (%s): %s",
                            step.outputs[0],
                            type(result).__name__,
                            e,
                        )
                        raise RuntimeError(
                            f"Artifact '{step.outputs[0]}' could not be serialized to artifact store: {e}",
                        ) from e

        total = time.time() - start
        logger.info(
            "%s🎉 StepRunner complete | %d steps | %.1fs total",
            group_label,
            len(ordered_steps),
            total,
        )

        return results

    def _topological_sort(self, steps: list, pipeline: Any) -> list:
        """Sort steps in topological order based on the pipeline DAG.

        Args:
            steps: Subset of steps to sort
            pipeline: Full pipeline (for DAG reference)

        Returns:
            Steps in execution order
        """
        step_names = {s.name for s in steps}

        # Use the pipeline's DAG to get full topological order
        try:
            all_nodes = pipeline.dag.topological_sort()
            ordered_names = [n.name for n in all_nodes if n.name in step_names]
        except (AttributeError, ValueError):
            # Fallback: use the order from self.step_names
            ordered_names = [n for n in self.step_names if n in step_names]

        step_map = {s.name: s for s in steps}
        return [step_map[name] for name in ordered_names if name in step_map]


def run_steps_from_env() -> dict[str, Any]:
    """Convenience function to run steps from environment variables.

    This is the main entry point for remote containers:
        python -m flowyml.core.step_runner
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    runner = StepRunner.from_env()
    return runner.run()


if __name__ == "__main__":
    run_steps_from_env()

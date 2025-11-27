"""Pipeline Module - Main orchestration for ML pipelines."""

import json
from typing import Any
from datetime import datetime
from pathlib import Path

from uniflow.core.context import Context
from uniflow.core.step import Step
from uniflow.core.graph import DAG, Node
from uniflow.core.executor import Executor, LocalExecutor, ExecutionResult
from uniflow.core.cache import CacheStore


class PipelineResult:
    """Result of pipeline execution."""

    def __init__(self, run_id: str, pipeline_name: str):
        self.run_id = run_id
        self.pipeline_name = pipeline_name
        self.success = False
        self.step_results: dict[str, ExecutionResult] = {}
        self.outputs: dict[str, Any] = {}
        self.start_time = datetime.now()
        self.end_time: datetime | None = None
        self.duration_seconds: float = 0.0

    def add_step_result(self, result: ExecutionResult) -> None:
        """Add result from a step execution."""
        self.step_results[result.step_name] = result

        # Track outputs
        if result.success and result.output is not None:
            # Assuming single output for simplicity
            self.outputs[result.step_name] = result.output

    def finalize(self, success: bool) -> None:
        """Mark pipeline as complete."""
        self.success = success
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access to outputs."""
        return self.outputs.get(key)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "success": self.success,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "steps": {
                name: {
                    "success": result.success,
                    "duration": result.duration_seconds,
                    "cached": result.cached,
                    "retries": result.retries,
                    "error": result.error,
                }
                for name, result in self.step_results.items()
            },
        }

    def summary(self) -> str:
        """Generate execution summary."""
        lines = [
            f"Pipeline: {self.pipeline_name}",
            f"Run ID: {self.run_id}",
            f"Status: {'✓ SUCCESS' if self.success else '✗ FAILED'}",
            f"Duration: {self.duration_seconds:.2f}s",
            "",
            "Steps:",
        ]

        for name, result in self.step_results.items():
            status = "✓" if result.success else "✗"
            cached = " (cached)" if result.cached else ""
            retries = f" [{result.retries} retries]" if result.retries > 0 else ""
            lines.append(
                f"  {status} {name}: {result.duration_seconds:.2f}s{cached}{retries}",
            )
            if result.error:
                lines.append(f"     Error: {result.error.split(chr(10))[0]}")

        return "\n".join(lines)


class Pipeline:
    """Main pipeline class for orchestrating ML workflows.

    Example:
        >>> from uniflow import Pipeline, step, context
        >>> ctx = context(learning_rate=0.001, epochs=10)
        >>> @step(outputs=["model/trained"])
        ... def train(learning_rate: float, epochs: int):
        ...     return train_model(learning_rate, epochs)
        >>> pipeline = Pipeline("my_pipeline", context=ctx)
        >>> pipeline.add_step(train)
        >>> result = pipeline.run()
    """

    def __init__(
        self,
        name: str,
        context: Context | None = None,
        executor: Executor | None = None,
        enable_cache: bool = True,
        cache_dir: str | None = None,
        stack: Any | None = None,  # Stack instance
        project: str | None = None,  # Project name to attach to
    ):
        """Args:
        name: Name of the pipeline
        context: Optional context for parameter injection
        executor: Optional executor (defaults to LocalExecutor)
        enable_cache: Whether to enable caching
        cache_dir: Optional directory for cache
        stack: Optional stack instance to run on
        project: Optional project name to attach this pipeline to.
        """
        self.name = name
        self.context = context or Context()
        self.enable_cache = enable_cache
        self.stack = stack  # Store stack instance

        self.steps: list[Step] = []
        self.dag = DAG()

        # Storage
        if cache_dir is None:
            from uniflow.utils.config import get_config

            cache_dir = str(get_config().cache_dir)

        self.cache_store = CacheStore(cache_dir) if enable_cache else None

        from uniflow.utils.config import get_config

        self.runs_dir = get_config().runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components from stack or defaults
        if self.stack:
            self.executor = executor or self.stack.executor
            self.metadata_store = self.stack.metadata_store
        else:
            self.executor = executor or LocalExecutor()
            # Metadata store for UI integration
            from uniflow.storage.metadata import SQLiteMetadataStore

            self.metadata_store = SQLiteMetadataStore()

        # Handle Project Attachment
        if project:
            from uniflow.core.project import ProjectManager

            manager = ProjectManager()
            # Get or create project
            proj = manager.get_project(project)
            if not proj:
                proj = manager.create_project(project)

            # Configure pipeline with project settings
            self.runs_dir = proj.runs_dir
            self.metadata_store = proj.metadata_store

            # Register pipeline with project
            if name not in proj.metadata["pipelines"]:
                proj.metadata["pipelines"].append(name)
                proj._save_metadata()

        # State
        self._built = False

    def add_step(self, step: Step) -> "Pipeline":
        """Add a step to the pipeline.

        Args:
            step: Step to add

        Returns:
            Self for chaining
        """
        self.steps.append(step)
        self._built = False
        return self

    def build(self) -> None:
        """Build the execution DAG."""
        if self._built:
            return

        # Clear previous DAG
        self.dag = DAG()

        # Add nodes
        for step in self.steps:
            node = Node(
                name=step.name,
                step=step,
                inputs=step.inputs,
                outputs=step.outputs,
            )
            self.dag.add_node(node)

        # Build edges
        self.dag.build_edges()

        # Validate
        errors = self.dag.validate()
        if errors:
            raise ValueError("Pipeline validation failed:\n" + "\n".join(errors))

        self._built = True

    def run(
        self,
        inputs: dict[str, Any] | None = None,
        debug: bool = False,
        stack: Any | None = None,  # Stack override
        resources: Any | None = None,  # ResourceConfig
        docker_config: Any | None = None,  # DockerConfig
        context: dict[str, Any] | None = None,  # Context vars override
    ) -> PipelineResult:
        """Execute the pipeline.

        Args:
            inputs: Optional input data for the pipeline
            debug: Enable debug mode with detailed logging
            stack: Stack override (uses self.stack if not provided)
            resources: Resource configuration for execution
            docker_config: Docker configuration for containerized execution
            context: Context variables override

        Returns:
            PipelineResult with outputs and execution info
        """
        import uuid

        run_id = str(uuid.uuid4())

        # Use provided stack or instance stack
        if stack is not None:
            self.stack = stack
            # Update components from new stack
            self.executor = self.stack.executor
            self.metadata_store = self.stack.metadata_store

        # Determine artifact store
        artifact_store = None
        if self.stack:
            artifact_store = self.stack.artifact_store

        # Update context with provided values
        if context:
            self.context.update(context)

        # Build DAG if needed
        if not self._built:
            self.build()

        # Initialize result
        result = PipelineResult(run_id, self.name)
        step_outputs = inputs or {}

        # Get execution order
        execution_order = self.dag.topological_sort()

        # Map step names to step objects for easier lookup
        self.steps_dict = {step.name: step for step in self.steps}

        if debug:
            pass
        else:
            # Always print the run URL for better UX
            pass

        # Execute steps in order
        for node in execution_order:
            step = node.step

            if debug:
                pass

            # Validate context parameters
            missing_params = self.context.validate_for_step(step.func, exclude=step.inputs)
            if missing_params:
                if debug:
                    pass
                error_msg = f"Missing required parameters: {missing_params}"
                step_result = ExecutionResult(
                    step_name=step.name,
                    success=False,
                    error=error_msg,
                )
                result.add_step_result(step_result)
                result.finalize(success=False)
                self._save_run(result)  # Save run before returning
                return result

            # Prepare step inputs
            step_inputs = {}
            for input_name in step.inputs:
                if input_name in step_outputs:
                    step_inputs[input_name] = step_outputs[input_name]
                else:
                    # Input might be parameter name, not asset name
                    # This is simplified - real implementation would be smarter
                    pass

            # Get context parameters for this step
            context_params = self.context.inject_params(step.func)

            # Execute step
            step_result = self.executor.execute_step(
                step,
                step_inputs,
                context_params,
                self.cache_store,
                artifact_store=artifact_store,
                run_id=run_id,
                project_name=self.name,
            )

            result.add_step_result(step_result)

            if debug:
                pass

            # Handle failure
            if not step_result.success:
                if debug and not step_result.error:
                    pass
                result.finalize(success=False)
                self._save_run(result)
                return result

            # Store outputs for next steps
            if step_result.output is not None:
                if len(step.outputs) == 1:
                    step_outputs[step.outputs[0]] = step_result.output
                    result.outputs[step.outputs[0]] = step_result.output
                elif isinstance(step_result.output, (list, tuple)) and len(step_result.output) == len(step.outputs):
                    for name, val in zip(step.outputs, step_result.output, strict=False):
                        step_outputs[name] = val
                        result.outputs[name] = val
                elif isinstance(step_result.output, dict):
                    for name in step.outputs:
                        if name in step_result.output:
                            step_outputs[name] = step_result.output[name]
                            result.outputs[name] = step_result.output[name]
                else:
                    # Fallback: assign to first output if available
                    if step.outputs:
                        step_outputs[step.outputs[0]] = step_result.output
                        result.outputs[step.outputs[0]] = step_result.output

        # Success!
        result.finalize(success=True)

        if debug:
            pass

        self._save_run(result)
        return result

    def _save_run(self, result: PipelineResult) -> None:
        """Save run results to disk and metadata database."""
        # Save to JSON file
        run_file = self.runs_dir / f"{result.run_id}.json"
        with open(run_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

        # Serialize DAG structure for UI
        dag_data = {
            "nodes": [
                {
                    "id": node.name,
                    "name": node.name,
                    "inputs": node.inputs,
                    "outputs": node.outputs,
                }
                for node in self.dag.nodes.values()
            ],
            "edges": [
                {
                    "source": dep,
                    "target": node_name,
                }
                for node_name, deps in self.dag.edges.items()
                for dep in deps
            ],
        }

        # Collect step metadata including source code
        steps_metadata = {}
        for step in self.steps:
            step_result = result.step_results.get(step.name)
            steps_metadata[step.name] = {
                "success": step_result.success if step_result else False,
                "duration": step_result.duration_seconds if step_result else 0,
                "cached": step_result.cached if step_result else False,
                "retries": step_result.retries if step_result else 0,
                "error": step_result.error if step_result else None,
                "source_code": step.source_code,
                "inputs": step.inputs,
                "outputs": step.outputs,
                "tags": step.tags,
                "resources": step.resources,
            }

        # Save to metadata database for UI
        metadata = {
            "run_id": result.run_id,
            "pipeline_name": result.pipeline_name,
            "status": "completed" if result.success else "failed",
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration": result.duration_seconds,
            "success": result.success,
            "context": self.context._params if hasattr(self.context, "_params") else {},
            "steps": steps_metadata,
            "dag": dag_data,
        }
        self.metadata_store.save_run(result.run_id, metadata)

        # Save artifacts and metrics
        for step_name, step_result in result.step_results.items():
            if step_result.success and step_result.output is not None:
                # Find step definition to get output names
                step_def = next((s for s in self.steps if s.name == step_name), None)
                output_names = step_def.outputs if step_def else []

                # Normalize outputs to a dictionary
                outputs_to_save = {}

                # Case 1: Dictionary output (common for metrics)
                if isinstance(step_result.output, dict):
                    # If step has defined outputs, try to map them
                    if output_names and len(output_names) == 1:
                        outputs_to_save[output_names[0]] = step_result.output
                    else:
                        # Otherwise treat keys as output names if they match, or just save whole dict
                        outputs_to_save[f"{step_name}_output"] = step_result.output

                    # Also save individual numeric values as metrics
                    for k, v in step_result.output.items():
                        if isinstance(v, (int, float)):
                            self.metadata_store.save_metric(result.run_id, k, float(v))

                # Case 2: Tuple/List output matching output names
                elif isinstance(step_result.output, (list, tuple)) and len(output_names) == len(step_result.output):
                    for name, val in zip(output_names, step_result.output, strict=False):
                        outputs_to_save[name] = val

                # Case 3: Single output
                else:
                    name = output_names[0] if output_names else f"{step_name}_output"
                    outputs_to_save[name] = step_result.output

                # Save artifacts
                for name, value in outputs_to_save.items():
                    artifact_id = f"{result.run_id}_{step_name}_{name}"

                    # Check if it's a UniFlow Asset
                    is_asset = hasattr(value, "metadata") and hasattr(value, "data")

                    if is_asset:
                        # Handle UniFlow Asset
                        asset_type = value.__class__.__name__
                        artifact_metadata = {
                            "artifact_id": artifact_id,
                            "name": value.name,
                            "type": asset_type,
                            "run_id": result.run_id,
                            "step": step_name,
                            "path": None,
                            "value": str(value.data)[:1000] if value.data else None,
                            "created_at": datetime.now().isoformat(),
                            "properties": self._sanitize_for_json(value.metadata.properties)
                            if hasattr(value.metadata, "properties")
                            else {},
                        }
                        self.metadata_store.save_artifact(artifact_id, artifact_metadata)

                        # Special handling for Metrics asset
                        if asset_type == "Metrics" and isinstance(value.data, dict):
                            for k, v in value.data.items():
                                if isinstance(v, (int, float)):
                                    self.metadata_store.save_metric(result.run_id, k, float(v))
                    else:
                        # Handle standard Python objects
                        artifact_metadata = {
                            "artifact_id": artifact_id,
                            "name": name,
                            "type": type(value).__name__,
                            "run_id": result.run_id,
                            "step": step_name,
                            "path": str(value) if isinstance(value, (str, Path)) and len(str(value)) < 255 else None,
                            "value": str(value)[:1000],  # Preview
                            "created_at": datetime.now().isoformat(),
                        }
                        self.metadata_store.save_artifact(artifact_id, artifact_metadata)

                        # Save single value metric if applicable
                        if isinstance(value, (int, float)):
                            self.metadata_store.save_metric(result.run_id, name, float(value))

    def _sanitize_for_json(self, obj: Any) -> Any:
        """Helper to make objects JSON serializable."""
        if hasattr(obj, "id") and hasattr(obj, "name"):  # Asset-like
            return {"type": obj.__class__.__name__, "id": obj.id, "name": obj.name}
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(v) for v in obj]
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        return str(obj)

    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if self.cache_store:
            return self.cache_store.stats()
        return {}

    def invalidate_cache(
        self,
        step: str | None = None,
        before: str | None = None,
    ) -> None:
        """Invalidate cache entries.

        Args:
            step: Invalidate cache for specific step
            before: Invalidate cache entries before date
        """
        if self.cache_store:
            if step:
                self.cache_store.invalidate(step_name=step)
            else:
                self.cache_store.clear()

    def visualize(self) -> str:
        """Generate pipeline visualization."""
        if not self._built:
            self.build()
        return self.dag.visualize()

    def __repr__(self) -> str:
        return f"Pipeline(name='{self.name}', steps={len(self.steps)})"

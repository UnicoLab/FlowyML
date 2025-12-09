"""Pipeline Module - Main orchestration for ML pipelines."""

import json
from typing import Any
from datetime import datetime
from pathlib import Path

from flowyml.core.context import Context
from flowyml.core.step import Step
from flowyml.core.graph import DAG, Node
from flowyml.core.executor import Executor, LocalExecutor, ExecutionResult
from flowyml.core.cache import CacheStore


class PipelineResult:
    """Result of pipeline execution."""

    def __init__(self, run_id: str, pipeline_name: str):
        self.run_id = run_id
        self.pipeline_name = pipeline_name
        self.success = False
        self.state = "pending"
        self.step_results: dict[str, ExecutionResult] = {}
        self.outputs: dict[str, Any] = {}
        self.start_time = datetime.now()
        self.end_time: datetime | None = None
        self.duration_seconds: float = 0.0
        self.resource_config: Any | None = None
        self.docker_config: Any | None = None
        self.remote_job_id: str | None = None

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
        self.state = "completed" if success else "failed"
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def attach_configs(self, resource_config: Any | None, docker_config: Any | None) -> None:
        """Store execution configs for downstream inspection."""
        self.resource_config = resource_config
        self.docker_config = docker_config

    def mark_submitted(self, job_id: str) -> None:
        """Mark result as remotely submitted."""
        self.success = True
        self.state = "submitted"
        self.remote_job_id = job_id

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access to outputs."""
        return self.outputs.get(key)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "success": self.success,
            "state": self.state,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "resource_config": self.resource_config.to_dict()
            if hasattr(self.resource_config, "to_dict")
            else self.resource_config,
            "docker_config": self.docker_config.to_dict()
            if hasattr(self.docker_config, "to_dict")
            else self.docker_config,
            "remote_job_id": self.remote_job_id,
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
        if self.state == "submitted":
            status_line = f"Status: ⏳ SUBMITTED (job: {self.remote_job_id})"
        elif self.success:
            status_line = "Status: ✓ SUCCESS"
        elif self.state == "failed":
            status_line = "Status: ✗ FAILED"
        else:
            status_line = f"Status: {self.state.upper()}"

        lines = [
            f"Pipeline: {self.pipeline_name}",
            f"Run ID: {self.run_id}",
            status_line,
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
        >>> from flowyml import Pipeline, step, context
        >>> ctx = context(learning_rate=0.001, epochs=10)
        >>> @step(outputs=["model/trained"])
        ... def train(learning_rate: float, epochs: int):
        ...     return train_model(learning_rate, epochs)
        >>> pipeline = Pipeline("my_pipeline", context=ctx)
        >>> pipeline.add_step(train)
        >>> result = pipeline.run()

        # With project_name, automatically creates/attaches to project
        >>> pipeline = Pipeline("my_pipeline", context=ctx, project_name="ml_project")

        # With version parameter, automatically creates VersionedPipeline
        >>> pipeline = Pipeline("my_pipeline", context=ctx, version="v1.0.1", project_name="ml_project")
    """

    def __new__(
        cls,
        name: str,
        version: str | None = None,
        project_name: str | None = None,
        project: str | None = None,  # For backward compatibility
        **kwargs,
    ):
        """Create a Pipeline or VersionedPipeline instance.

        If version is provided, automatically returns a VersionedPipeline instance.
        Otherwise, returns a regular Pipeline instance.
        """
        if version is not None:
            from flowyml.core.versioning import VersionedPipeline

            # Pass project_name or project to VersionedPipeline
            vp_kwargs = kwargs.copy()
            if project_name:
                vp_kwargs["project_name"] = project_name
            elif project:
                vp_kwargs["project"] = project
            return VersionedPipeline(name=name, version=version, **vp_kwargs)
        return super().__new__(cls)

    def __init__(
        self,
        name: str,
        context: Context | None = None,
        executor: Executor | None = None,
        enable_cache: bool = True,
        cache_dir: str | None = None,
        stack: Any | None = None,  # Stack instance
        project: str | None = None,  # Project name to attach to (deprecated, use project_name)
        project_name: str | None = None,  # Project name to attach to (creates if doesn't exist)
        version: str | None = None,  # If provided, VersionedPipeline is created via __new__
    ):
        """Initialize pipeline.

        Args:
            name: Name of the pipeline
            context: Optional context for parameter injection
            executor: Optional executor (defaults to LocalExecutor)
            enable_cache: Whether to enable caching
            cache_dir: Optional directory for cache
            stack: Optional stack instance to run on
            project: Optional project name to attach this pipeline to (deprecated, use project_name)
            project_name: Optional project name to attach this pipeline to.
                If the project doesn't exist, it will be created automatically.
            version: Optional version string. If provided, a VersionedPipeline
                instance is automatically created instead of a regular Pipeline.
        """
        self.name = name
        self.context = context or Context()
        self.enable_cache = enable_cache
        self.stack = None  # Will be assigned via _apply_stack
        self._stack_locked = stack is not None
        self._provided_executor = executor

        self.steps: list[Step] = []
        self.dag = DAG()

        # Storage
        if cache_dir is None:
            from flowyml.utils.config import get_config

            cache_dir = str(get_config().cache_dir)

        self.cache_store = CacheStore(cache_dir) if enable_cache else None

        from flowyml.utils.config import get_config

        self.runs_dir = get_config().runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components from stack or defaults
        self.executor = executor or LocalExecutor()
        # Metadata store for UI integration
        from flowyml.storage.metadata import SQLiteMetadataStore

        self.metadata_store = SQLiteMetadataStore()

        if stack:
            self._apply_stack(stack, locked=True)

        # Handle Project Attachment
        # Support both project_name (preferred) and project (for backward compatibility)
        project_to_use = project_name or project
        if project_to_use:
            from flowyml.core.project import ProjectManager

            manager = ProjectManager()
            # Get or create project
            proj = manager.get_project(project_to_use)
            if not proj:
                proj = manager.create_project(project_to_use)

            # Configure pipeline with project settings
            self.runs_dir = proj.runs_dir
            self.metadata_store = proj.metadata_store

            # Register pipeline with project
            if name not in proj.metadata["pipelines"]:
                proj.metadata["pipelines"].append(name)
                proj._save_metadata()

        # State
        self._built = False
        self.step_groups: list[Any] = []  # Will hold StepGroup objects

    def _apply_stack(self, stack: Any | None, locked: bool) -> None:
        """Attach a stack and update executors/metadata."""
        if not stack:
            return
        self.stack = stack
        self._stack_locked = locked
        if self._provided_executor:
            self.executor = self._provided_executor
        else:
            self.executor = stack.executor
        self.metadata_store = stack.metadata_store

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

        # Analyze step groups
        from flowyml.core.step_grouping import StepGroupAnalyzer

        analyzer = StepGroupAnalyzer()
        self.step_groups = analyzer.analyze_groups(self.dag, self.steps)

        self._built = True

    def run(
        self,
        inputs: dict[str, Any] | None = None,
        debug: bool = False,
        stack: Any | None = None,  # Stack override
        resources: Any | None = None,  # ResourceConfig
        docker_config: Any | None = None,  # DockerConfig
        context: dict[str, Any] | None = None,  # Context vars override
        auto_start_ui: bool = True,  # Auto-start UI server
        **kwargs,
    ) -> PipelineResult:
        """Execute the pipeline.

        Args:
            inputs: Optional input data for the pipeline
            debug: Enable debug mode with detailed logging
            stack: Stack override (uses self.stack if not provided)
            resources: Resource configuration for execution
            docker_config: Docker configuration for containerized execution
            context: Context variables override
            auto_start_ui: Automatically start UI server if not running and display URL
            **kwargs: Additional arguments passed to the orchestrator

        Returns:
            PipelineResult with outputs and execution info
        """
        import uuid
        from flowyml.core.orchestrator import LocalOrchestrator

        run_id = str(uuid.uuid4())

        # Auto-start UI server if requested
        ui_url = None
        run_url = None
        if auto_start_ui:
            try:
                from flowyml.ui.server_manager import UIServerManager

                ui_manager = UIServerManager.get_instance()
                if ui_manager.ensure_running(auto_start=True):
                    ui_url = ui_manager.get_url()
                    run_url = ui_manager.get_run_url(run_id)

                    # Display UI URL
                    if ui_url:
                        print(f"\n🌐 flowyml UI is available at: {ui_url}")
                        if run_url:
                            print(f"📊 View this run in real-time: {run_url}")
                        print()  # Empty line for readability
            except Exception:
                # Silently fail if UI is not available
                pass

        # Determine stack for this run
        if stack is not None:
            self._apply_stack(stack, locked=True)
        elif not self._stack_locked:
            active_stack = None
            try:
                from flowyml.stacks.registry import get_active_stack
            except ImportError:
                get_active_stack = None
            if get_active_stack:
                active_stack = get_active_stack()
            if active_stack:
                self._apply_stack(active_stack, locked=False)

        # Determine orchestrator
        orchestrator = getattr(self.stack, "orchestrator", None) if self.stack else None
        if orchestrator is None:
            orchestrator = LocalOrchestrator()

        # Update context with provided values
        if context:
            self.context.update(context)

        # Build DAG if needed
        if not self._built:
            self.build()

        resource_config = self._coerce_resource_config(resources)
        docker_cfg = self._coerce_docker_config(docker_config)

        # Run the pipeline via orchestrator
        result = orchestrator.run_pipeline(
            self,
            run_id=run_id,
            resources=resource_config,
            docker_config=docker_cfg,
            inputs=inputs,
            context=context,
            **kwargs,
        )

        # If result is just a job ID (remote execution), wrap it in a basic result
        if isinstance(result, str):
            # Create a submitted result wrapper
            wrapper = PipelineResult(run_id, self.name)
            wrapper.attach_configs(resource_config, docker_cfg)
            wrapper.mark_submitted(result)
            self._save_run(wrapper)
            self._save_pipeline_definition()
            return wrapper

        return result

    def to_definition(self) -> dict:
        """Serialize pipeline to definition for storage and reconstruction."""
        if not self._built:
            self.build()

        return {
            "name": self.name,
            "steps": [
                {
                    "name": step.name,
                    "inputs": step.inputs,
                    "outputs": step.outputs,
                    "source_code": step.source_code,
                    "tags": step.tags,
                }
                for step in self.steps
            ],
            "dag": {
                "nodes": [
                    {
                        "name": node.name,
                        "inputs": node.inputs,
                        "outputs": node.outputs,
                    }
                    for node in self.dag.nodes.values()
                ],
                "edges": [
                    {"source": dep, "target": node_name} for node_name, deps in self.dag.edges.items() for dep in deps
                ],
            },
        }

    def _save_pipeline_definition(self) -> None:
        """Save pipeline definition to metadata store for scheduling."""
        try:
            definition = self.to_definition()
            self.metadata_store.save_pipeline_definition(self.name, definition)
        except Exception as e:
            # Don't fail the run if definition saving fails
            print(f"Warning: Failed to save pipeline definition: {e}")

    def _coerce_resource_config(self, resources: Any | None):
        """Convert resources input to ResourceConfig if necessary."""
        if resources is None:
            return None
        try:
            from flowyml.stacks.components import ResourceConfig
        except Exception:
            return resources

        if isinstance(resources, ResourceConfig):
            return resources
        if isinstance(resources, dict):
            return ResourceConfig(**resources)
        return resources

    def _coerce_docker_config(self, docker_config: Any | None):
        """Convert docker input to DockerConfig if necessary."""
        if docker_config is None:
            return None
        try:
            from flowyml.stacks.components import DockerConfig
        except Exception:
            return docker_config

        if isinstance(docker_config, DockerConfig):
            return docker_config
        if isinstance(docker_config, dict):
            return DockerConfig(**docker_config)
        return docker_config

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
                "resources": step.resources.to_dict() if hasattr(step.resources, "to_dict") else step.resources,
            }

        # Save to metadata database for UI
        metadata = {
            "run_id": result.run_id,
            "pipeline_name": result.pipeline_name,
            "status": result.state,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration": result.duration_seconds,
            "success": result.success,
            "context": self.context._params if hasattr(self.context, "_params") else {},
            "steps": steps_metadata,
            "dag": dag_data,
            "resources": result.resource_config.to_dict()
            if hasattr(result.resource_config, "to_dict")
            else result.resource_config,
            "docker": result.docker_config.to_dict()
            if hasattr(result.docker_config, "to_dict")
            else result.docker_config,
            "remote_job_id": result.remote_job_id,
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

                    # Check if it's a flowyml Asset
                    is_asset = hasattr(value, "metadata") and hasattr(value, "data")

                    if is_asset:
                        # Handle flowyml Asset
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

    @classmethod
    def from_definition(cls, definition: dict, context: Context | None = None) -> "Pipeline":
        """Reconstruct pipeline from stored definition.

        This creates a "ghost" pipeline that can be executed but uses
        the stored step structure. Actual step logic must still be
        available in the codebase.

        Args:
            definition: Pipeline definition from to_definition()
            context: Optional context for execution

        Returns:
            Reconstructed Pipeline instance
        """
        from flowyml.core.step import step as step_decorator

        # Create pipeline instance
        pipeline = cls(
            name=definition["name"],
            context=context or Context(),
        )

        # Reconstruct steps
        for step_def in definition["steps"]:
            # Create a generic step function that can be called
            # In a real implementation, we'd need to either:
            # 1. Store serialized functions (using cloudpickle)
            # 2. Import functions by name from codebase
            # 3. Use placeholder functions

            # For now, we'll create a placeholder that logs execution
            def generic_step_func(*args, **kwargs):
                """Generic step function for reconstructed pipeline."""
                print(f"Executing reconstructed step with args={args}, kwargs={kwargs}")
                return

            # Apply step decorator with stored metadata
            decorated = step_decorator(
                name=step_def["name"],
                inputs=step_def["inputs"],
                outputs=step_def["outputs"],
                tags=step_def.get("tags", []),
            )(generic_step_func)

            # Add to pipeline
            pipeline.add_step(decorated)

        return pipeline

    def __repr__(self) -> str:
        return f"Pipeline(name='{self.name}', steps={len(self.steps)})"

    def schedule(
        self,
        schedule_type: str,
        value: str | int,
        **kwargs,
    ) -> Any:
        """Schedule this pipeline to run automatically.

        Args:
            schedule_type: Type of schedule ('cron', 'interval', 'daily', 'hourly')
            value: Schedule value (cron expression, seconds, 'HH:MM', or minute)
            **kwargs: Additional arguments for scheduler

        Returns:
            Schedule object
        """
        from flowyml.core.scheduler import PipelineScheduler

        scheduler = PipelineScheduler()

        if schedule_type == "cron":
            return scheduler.schedule_cron(self.name, self.run, str(value), **kwargs)
        elif schedule_type == "interval":
            return scheduler.schedule_interval(self.name, self.run, seconds=int(value), **kwargs)
        elif schedule_type == "daily":
            if isinstance(value, str) and ":" in value:
                h, m = map(int, value.split(":"))
                return scheduler.schedule_daily(self.name, self.run, hour=h, minute=m, **kwargs)
            else:
                raise ValueError("Daily schedule value must be 'HH:MM'")
        elif schedule_type == "hourly":
            return scheduler.schedule_hourly(self.name, self.run, minute=int(value), **kwargs)
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

    def check_cache(self) -> dict[str, Any] | None:
        """Check if a successful run of this pipeline already exists.

        Returns:
            Metadata of the last successful run, or None if not found.
        """
        # Query metadata store for successful runs of this pipeline
        try:
            runs = self.metadata_store.query(
                pipeline_name=self.name,
                status="completed",
            )

            if runs:
                # Return the most recent one (query returns ordered by created_at DESC)
                return runs[0]
        except Exception as e:
            # Don't fail if metadata store is not available or errors
            print(f"Warning: Failed to check cache: {e}")

        return None

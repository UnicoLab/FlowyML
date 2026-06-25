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
        self.snapshot_hash: str | None = None

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
            "snapshot_hash": self.snapshot_hash,
            "metadata": {
                "resources": self.resource_config.to_dict()
                if hasattr(self.resource_config, "to_dict")
                else self.resource_config,
                "docker": self.docker_config.to_dict()
                if hasattr(self.docker_config, "to_dict")
                else self.docker_config,
                "remote_job_id": self.remote_job_id,
            },
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

        # Option 1: Auto-discover all @step-decorated functions
        >>> pipeline = Pipeline("my_pipeline", context=ctx, auto_discover=True)
        >>> result = pipeline.run()

        # Option 2: Concise explicit selection
        >>> pipeline = Pipeline.from_steps(train, name="my_pipeline", context=ctx)

        # Option 3: Batch add
        >>> pipeline = Pipeline("my_pipeline", context=ctx)
        >>> pipeline.add_steps([train])

        # Option 4: Manual add_step (existing, still works)
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
        **kwargs: Any,
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
        enable_checkpointing: bool | None = None,  # None means use config default
        enable_experiment_tracking: bool | None = None,  # None means use config default (True)
        auto_track: bool | None = None,  # None means use enable_experiment_tracking value
        cache_dir: str | None = None,
        stack: Any | None = None,  # Stack name (str), Stack instance, or StackDefinition
        env: str | None = None,  # Environment name from flowyml.yaml (e.g. 'dev', 'staging', 'prod')
        project: str | None = None,  # Project name to attach to (deprecated, use project_name)
        project_name: str | None = None,  # Project name to attach to (creates if doesn't exist)
        version: str | None = None,  # If provided, VersionedPipeline is created via __new__
        auto_discover: bool = False,  # Auto-discover @step-decorated functions
        **kwargs: Any,
    ):
        """Initialize pipeline.

        Args:
            name: Name of the pipeline
            context: Optional context for parameter injection
            executor: Optional executor (defaults to LocalExecutor)
            enable_cache: Whether to enable caching
            enable_checkpointing: Whether to enable checkpointing (defaults to config setting, True by default)
            enable_experiment_tracking: Whether to enable automatic experiment tracking (defaults to config.auto_log_metrics, True by default)
            auto_track: Whether to automatically track experiments. If None (default), uses the value of enable_experiment_tracking.
            cache_dir: Optional directory for cache
            stack: Stack to run on. Accepts:
                - ``str``: Stack name (e.g. ``"local"``, ``"aml_cpu_small"``),
                  a URI (e.g. ``"github://org/repo@v1#stack_name"``), or ``"local"``.
                - ``Stack``: Existing runtime Stack instance.
                - ``StackDefinition``: Enterprise Pydantic stack definition.
            env: Environment name from ``flowyml.yaml`` (e.g. ``"dev"``, ``"staging"``,
                ``"prod"``). Resolves the stack from the project config's environments
                section. If both ``stack`` and ``env`` are provided, ``stack`` takes priority.
            project: Optional project name to attach this pipeline to (deprecated, use project_name)
            project_name: Optional project name to attach this pipeline to.
                If the project doesn't exist, it will be created automatically.
            version: Optional version string. If provided, a VersionedPipeline
                instance will be created instead of a regular Pipeline.
            auto_discover: If True, automatically discover all ``@step``-decorated
                functions from the global registry at build time. Steps with a
                matching ``pipeline`` tag are preferred. Defaults to False.
            **kwargs: Additional keyword arguments passed to the pipeline.
        """
        from flowyml.utils.config import get_config

        self.name = name
        self.context = context or Context()
        self.enable_cache = enable_cache

        # Set checkpointing (use config default if not specified)
        config = get_config()
        self.enable_checkpointing = (
            enable_checkpointing if enable_checkpointing is not None else config.enable_checkpointing
        )

        # Set experiment tracking (use config default if not specified, default: True)
        # Can be set via enable_experiment_tracking parameter or defaults to config.auto_log_metrics
        self.enable_experiment_tracking = (
            enable_experiment_tracking if enable_experiment_tracking is not None else config.auto_log_metrics
        )
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
        # Metadata store for UI integration - use same store as UI
        from flowyml.storage.metadata import SQLiteMetadataStore
        from flowyml.utils.config import get_config
        import os

        config = get_config()
        # Use simple environment variable check to allow connecting to shared DB
        db_url = os.environ.get("FLOWYML_DATABASE_URL")

        if db_url:
            self.metadata_store = SQLiteMetadataStore(db_url=db_url)
        else:
            # Use the same metadata database path as the UI to ensure visibility
            self.metadata_store = SQLiteMetadataStore(db_path=str(config.metadata_db))

        # --- Unified Stack Resolution ---
        # Priority: explicit stack arg → env arg → env var → project config → default
        self._env = env
        self._stack_definition = None  # Enterprise StackDefinition (if resolved)

        resolved_stack = self._resolve_stack_arg(stack, env)
        if resolved_stack:
            self._apply_stack(resolved_stack, locked=stack is not None)
        else:
            # Fallback: auto-resolve active stack from flowyml.yaml / FLOWYML_STACK env var
            try:
                from flowyml.plugins.stack_config import get_active_stack as _get_yaml_stack

                yaml_stack = _get_yaml_stack()
                if yaml_stack is not None:
                    live_stack = yaml_stack.to_stack()
                    self._apply_stack(live_stack, locked=False)
            except Exception:
                pass  # No config file or parse error — continue with defaults

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

            # Store project name for later use (e.g., in _save_run)
            self.project_name = project_to_use
        else:
            self.project_name = None

        # Auto-tracking
        # auto_track defaults to the same value as enable_experiment_tracking
        self.auto_track = auto_track if auto_track is not None else self.enable_experiment_tracking
        self._auto_tracker = None
        if self.auto_track:
            try:
                from flowyml.tracking.auto_tracking import AutoTracker

                self._auto_tracker = AutoTracker(enabled=True)
            except Exception:
                pass  # Don't fail pipeline creation if auto-tracking import fails

        # State
        self._built = False
        self._auto_discover = auto_discover
        self.step_groups: list[Any] = []  # Will hold StepGroup objects
        self.control_flows: list[Any] = []  # Store conditional control flows (If, Switch, etc.)

    def _resolve_stack_arg(self, stack: Any | None, env: str | None = None) -> Any | None:
        """Resolve a stack argument into a runtime Stack instance.

        Handles string names, URIs, StackDefinition objects, and Stack instances.
        Uses the enterprise StackResolver when available.

        Args:
            stack: Stack name (str), URI (str), Stack instance, or StackDefinition.
            env: Environment name from project config.

        Returns:
            A runtime ``Stack`` instance, or None if unresolvable.
        """
        if stack is None and env is None:
            return None

        # Case 1: Already a Stack instance — use directly
        from flowyml.stacks.base import Stack as BaseStack

        if isinstance(stack, BaseStack):
            return stack

        # Case 2: StackDefinition instance — convert to Stack
        try:
            from flowyml.stacks.enterprise.models import StackDefinition

            if isinstance(stack, StackDefinition):
                self._stack_definition = stack
                return stack.to_stack()
        except ImportError:
            pass

        # Case 3: String (name or URI) or env — use StackResolver
        try:
            from flowyml.stacks.enterprise.resolver import StackResolver

            resolver = StackResolver()
            stack_name = stack if isinstance(stack, str) else None
            definition = resolver.resolve(stack=stack_name, env=env)
            if definition:
                self._stack_definition = definition
                return definition.to_stack()
        except ImportError:
            pass
        except Exception:
            # Resolver failed — try legacy resolution for string names
            pass

        # Case 4: String name — try legacy StackRegistry
        if isinstance(stack, str):
            try:
                from flowyml.stacks.registry import get_registry

                registry = get_registry()
                legacy_stack = registry.get_stack(stack)
                if legacy_stack:
                    return legacy_stack
            except (ImportError, Exception):
                pass

            # Also try plugin StackConfig
            try:
                from flowyml.plugins.stack_config import get_stack_manager

                manager = get_stack_manager()
                stack_config = manager.get_stack(stack)
                if stack_config:
                    return stack_config.to_stack()
            except (ImportError, Exception):
                pass

        return None

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

    def add_steps(self, steps: list[Step]) -> "Pipeline":
        """Add multiple steps to the pipeline at once.

        Args:
            steps: List of Step instances to add

        Returns:
            Self for chaining

        Example:
            >>> pipeline.add_steps([load_data, train_model, evaluate])
        """
        for s in steps:
            self.steps.append(s)
        self._built = False
        return self

    @classmethod
    def from_steps(
        cls,
        *steps: Step,
        name: str,
        **kwargs: Any,
    ) -> "Pipeline":
        """Create a pipeline from an explicit list of steps.

        Convenience constructor that avoids repetitive ``add_step()`` calls
        while still giving you full control over which steps are included.

        Args:
            *steps: Step instances to include
            name: Pipeline name (keyword-only)
            **kwargs: Additional arguments passed to Pipeline()

        Returns:
            Configured Pipeline instance

        Example:
            >>> pipeline = Pipeline.from_steps(
            ...     load_data,
            ...     train_model,
            ...     evaluate,
            ...     name="training",
            ...     enable_cache=False,
            ... )
        """
        pipeline = cls(name=name, **kwargs)
        pipeline.add_steps(list(steps))
        return pipeline

    def add_control_flow(self, control_flow: Any) -> "Pipeline":
        """Add conditional control flow to the pipeline.

        Args:
            control_flow: Control flow object (If, Switch, etc.)

        Returns:
            Self for chaining

        Example:
            ```python
            from flowyml import If

            pipeline.add_control_flow(
                If(
                    condition=lambda ctx: ctx.steps["evaluate_model"].outputs["accuracy"] > 0.9,
                    then_step=deploy_model,
                    else_step=retrain_model,
                )
            )
            ```
        """
        self.control_flows.append(control_flow)
        self._built = False
        return self

    def add_sub_pipeline(
        self,
        pipeline: Any,
        name: str | None = None,
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        input_mapping: dict[str, str] | None = None,
        output_mapping: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> "Pipeline":
        """Add a sub-pipeline as a step in this pipeline.

        The sub-pipeline's steps will execute as a single unit within
        this pipeline's execution flow.

        Args:
            pipeline: Pipeline to nest as a step
            name: Optional step name (defaults to sub_pipeline.name)
            inputs: Input asset names from this pipeline
            outputs: Output asset names exposed to this pipeline
            input_mapping: Maps this pipeline's output names to child input names
            output_mapping: Maps child output names to this pipeline's input names
            **kwargs: Additional SubPipelineStep configuration

        Returns:
            Self for chaining

        Example:
            >>> preprocess = Pipeline("preprocessing")
            >>> preprocess.add_step(clean).add_step(normalize)
            >>>
            >>> parent = Pipeline("training")
            >>> parent.add_sub_pipeline(preprocess, inputs=["raw"], outputs=["clean"])
            >>> parent.add_step(train_model)
        """
        from flowyml.core.subpipeline import SubPipelineStep

        sub_step = SubPipelineStep(
            sub_pipeline=pipeline,
            name=name,
            inputs=inputs,
            outputs=outputs,
            input_mapping=input_mapping,
            output_mapping=output_mapping,
            **kwargs,
        )
        return self.add_step(sub_step)

    def build(self) -> None:
        """Build the execution DAG with type validation."""
        if self._built:
            return

        # Auto-discover steps from global registry if enabled
        if self._auto_discover and not self.steps:
            from flowyml.core.step import get_registered_steps

            discovered = get_registered_steps(pipeline=self.name)
            if not discovered:
                discovered = get_registered_steps()
            self.steps = list(discovered)

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

        # Validate DAG structure (now returns errors + warnings)
        validation_result = self.dag.validate()

        # Handle both old (list) and new (tuple) return formats
        if isinstance(validation_result, tuple):
            errors, warnings = validation_result
        else:
            errors = validation_result
            warnings = []

        # Log warnings (don't fail the build)
        if warnings:
            import logging

            logger = logging.getLogger(__name__)
            for w in warnings:
                logger.warning(f"Pipeline '{self.name}': {w}")

        if errors:
            raise ValueError("Pipeline validation failed:\n" + "\n".join(errors))

        # Type validation across connections
        try:
            from flowyml.core.type_validator import validate_pipeline

            type_errors, type_warnings = validate_pipeline(self.dag, self.steps)

            if type_warnings:
                import logging

                logger = logging.getLogger(__name__)
                for tw in type_warnings:
                    logger.warning(f"Pipeline '{self.name}': {tw}")

            if type_errors:
                error_messages = [str(e) for e in type_errors]
                raise ValueError(
                    "Pipeline type validation failed:\n" + "\n".join(error_messages),
                )
        except ImportError:
            pass  # type_validator not available, skip

        # Analyze step groups
        from flowyml.core.step_grouping import StepGroupAnalyzer

        analyzer = StepGroupAnalyzer()
        self.step_groups = analyzer.analyze_groups(self.dag, self.steps)

        self._built = True

    def dry_run(
        self,
        inputs: dict[str, Any] | None = None,
        stack: Any | None = None,
        env: str | None = None,
        **kwargs: Any,
    ) -> PipelineResult:
        """Validate the pipeline without executing it.

        Resolves the stack, validates policies, and displays the execution
        plan without running any steps.

        Args:
            inputs: Optional input data for the pipeline.
            stack: Stack override (name, URI, instance, or StackDefinition).
            env: Environment name from project config.
            **kwargs: Additional arguments.

        Returns:
            PipelineResult with validation info but no execution.
        """
        return self.run(
            inputs=inputs,
            stack=stack,
            env=env,
            dry_run=True,
            auto_start_ui=False,
            **kwargs,
        )

    def run(
        self,
        inputs: dict[str, Any] | None = None,
        debug: bool = False,
        stack: Any | None = None,  # Stack name (str), URI, Stack instance, or StackDefinition
        env: str | None = None,  # Environment from flowyml.yaml (e.g. 'dev', 'staging', 'prod')
        dry_run: bool = False,  # Validate without executing
        orchestrator: Any | None = None,  # Orchestrator override (takes precedence over stack orchestrator)
        resources: Any | None = None,  # ResourceConfig
        docker_config: Any | None = None,  # DockerConfig
        context: dict[str, Any] | None = None,  # Context vars override
        auto_start_ui: bool = True,  # Auto-start UI server
        **kwargs: Any,
    ) -> PipelineResult:
        """Execute the pipeline.

        Args:
            inputs: Optional input data for the pipeline
            debug: Enable debug mode with detailed logging
            stack: Stack to use for this run. Accepts:
                - ``str``: Stack name or URI (e.g. ``"local"``, ``"github://org/repo@v1#name"``)
                - ``Stack``: Runtime Stack instance
                - ``StackDefinition``: Enterprise Pydantic stack definition
            env: Environment name from ``flowyml.yaml`` (e.g. ``"dev"``, ``"staging"``,
                ``"prod"``). Resolves the stack from the project config's environments section.
            dry_run: If True, resolve the stack, validate policies, and display
                the execution plan without actually running any steps.
            orchestrator: Orchestrator override (takes precedence over stack orchestrator)
            resources: Resource configuration for execution
            docker_config: Docker configuration for containerized execution
            context: Context variables override
            auto_start_ui: Automatically start UI server if not running and display URL
            **kwargs: Additional arguments passed to the orchestrator

        Note:
            The orchestrator is determined in this priority order:
            1. Explicit `orchestrator` parameter (if provided)
            2. Stack's orchestrator (if stack is set/active)
            3. Default LocalOrchestrator

            When using a stack (e.g., GCPStack), the stack's orchestrator is automatically
            used unless explicitly overridden. This is the recommended approach for
            production deployments.

        Returns:
            PipelineResult with outputs and execution info
        """
        import uuid
        from flowyml.core.orchestrator import LocalOrchestrator
        from flowyml.core.checkpoint import PipelineCheckpoint
        from flowyml.utils.config import get_config
        from flowyml.plugins.integration import get_integration

        # Generate or use provided run_id
        run_id = kwargs.pop("run_id", None) or str(uuid.uuid4())

        # --- Transparent Experiment Tracking (dual-write) ---
        # Initialize plugin integration for external tracker forwarding.
        # The integration auto-resolves the tracker from stack/plugin config.
        # Internal FlowyML tracking is handled by _save_run() / _log_experiment_metrics().
        integration = None
        if self.enable_experiment_tracking:
            try:
                integration = get_integration()
                # Collect context params for tracker
                context_params = self.context.to_dict() if self.context else {}
                if context:
                    context_params.update(context)

                # --- Auto-tracking: collect ALL parameters ---
                if self._auto_tracker:
                    try:
                        auto_params = self._auto_tracker.collect_parameters(self)
                        # Merge auto-tracked params into context_params for external tracker
                        context_params.update(auto_params)
                        # Fire params-collected hooks
                        from flowyml.core.hooks import get_global_hooks as _get_hooks

                        _get_hooks().run_params_collected_hooks(auto_params)
                    except Exception:
                        pass  # Don't fail pipeline if auto-tracking fails

                # Build run tags
                run_tags = {}
                if self.project_name:
                    run_tags["flowyml.project"] = self.project_name
                if self.stack:
                    run_tags["flowyml.stack"] = getattr(self.stack, "name", str(type(self.stack).__name__))
                integration.on_pipeline_start(
                    pipeline_name=self.name,
                    run_id=run_id,
                    context=context_params,
                    tags=run_tags,
                )
            except Exception as e:
                import logging as _logging

                _logging.getLogger(__name__).debug(
                    "External tracker integration start skipped: %s",
                    e,
                )

        # Initialize checkpointing if enabled
        if self.enable_checkpointing:
            config = get_config()
            checkpoint = PipelineCheckpoint(
                run_id=run_id,
                checkpoint_dir=str(config.checkpoint_dir),
            )

            # Check if we should resume from checkpoint
            if checkpoint.exists():
                checkpoint_data = checkpoint.load()
                completed_steps = checkpoint_data.get("completed_steps", [])
                if completed_steps:
                    # Auto-resume: use checkpoint state
                    if hasattr(self, "_display") and self._display:
                        self._display.console.print(
                            f"[yellow]📦 Resuming from checkpoint: {len(completed_steps)} steps already completed[/yellow]",
                        )
                    # Store checkpoint info for orchestrator
                    self._checkpoint = checkpoint
                    self._resume_from_checkpoint = True
                    self._completed_steps_from_checkpoint = set(completed_steps)
                else:
                    self._checkpoint = checkpoint
                    self._resume_from_checkpoint = False
                    self._completed_steps_from_checkpoint = set()
            else:
                self._checkpoint = checkpoint
                self._resume_from_checkpoint = False
                self._completed_steps_from_checkpoint = set()
        else:
            self._checkpoint = None
            self._resume_from_checkpoint = False
            self._completed_steps_from_checkpoint = set()

        # Auto-start UI server if requested
        ui_url = None
        run_url = None
        ui_start_failed = False
        if auto_start_ui:
            ui_url, run_url, ui_start_failed = self._ensure_ui_server(run_id)

        # --- Unified Stack Resolution for this run ---
        if stack is not None or env is not None:
            resolved = self._resolve_stack_arg(stack, env)
            if resolved:
                self._apply_stack(resolved, locked=True)
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

        # --- Enterprise Policy Validation ---
        if self._stack_definition:
            try:
                from flowyml.stacks.enterprise.policy import PolicyEngine, PolicyContext

                engine = PolicyEngine()
                policy_ctx = PolicyContext(
                    stack=self._stack_definition,
                    project_name=getattr(self, "project_name", None),
                    environment=env or self._env,
                )
                engine.check(policy_ctx)  # Raises PolicyViolationError on failure
            except ImportError:
                pass  # Enterprise module not loaded

        # --- Dry Run: display plan and return early ---
        if dry_run:
            if not self._built:
                self.build()

            stack_info = "local (default)"
            if self._stack_definition:
                sd = self._stack_definition
                stack_info = f"{sd.name} v{sd.version} (backend: {sd.backend})"
            elif self.stack:
                stack_info = getattr(self.stack, "name", str(type(self.stack).__name__))

            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"🔍 Dry run: Pipeline '{self.name}'")
            logger.info(f"   Stack: {stack_info}")
            logger.info(f"   Steps: {[s.name for s in self.steps]}")
            logger.info("   DAG validated: ✓")
            logger.info("   Policy check: ✓")

            result = PipelineResult(run_id, self.name)
            result.status = "dry_run"
            return result

        # Determine orchestrator
        # Priority: 1) Explicit orchestrator parameter, 2) Stack orchestrator, 3) Default LocalOrchestrator
        if orchestrator is None:
            # Use orchestrator from stack if available
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

        # Prepare Docker Image if running on a stack
        if self.stack and docker_cfg:
            try:
                # This handles building/pushing or validating the URI
                project_name = getattr(self, "project_name", None)
                docker_cfg.image = self.stack.prepare_docker_image(
                    docker_cfg,
                    pipeline_name=self.name,
                    project_name=project_name,
                )
            except Exception as e:
                # If preparation fails (e.g. build error), we should probably fail the run
                # or at least warn. For now, we'll fail to prevent running with bad config
                raise RuntimeError(f"Failed to prepare docker image: {e}") from e

        # Initialize display system for beautiful CLI output
        display = None
        try:
            from flowyml.core.display import PipelineDisplay

            display = PipelineDisplay(
                pipeline_name=self.name,
                steps=self.steps,
                dag=self.dag,
                verbose=True,
                ui_url=ui_url,  # Pass UI URL for prominent display at start
                run_url=run_url,  # Pass run-specific URL for clickable link
            )
            display.show_header()
            display.show_execution_start()
        except Exception:
            # Silently fail if display system not available
            pass

        # Store display on pipeline for orchestrator to use
        self._display = display

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

        # Show summary (only if result is a PipelineResult, not a string or SubmissionResult)
        from flowyml.core.submission_result import SubmissionResult

        if isinstance(result, SubmissionResult):
            # Remote orchestrator returned a SubmissionResult — wrap it
            wrapper = PipelineResult(run_id, self.name)
            wrapper.attach_configs(resource_config, docker_cfg)
            wrapper.mark_submitted(result.job_id)
            wrapper.submission_result = result
            if display:
                meta = result.metadata or {}
                mode = meta.get("mode", "single_job")

                if mode == "group_orchestration":
                    groups = meta.get("groups", [])
                    total = meta.get("total_groups", len(groups))
                    failed = meta.get("failed_group") or meta.get("failed_step")

                    display.console.print(
                        "\n  [bold green]☁️  Group orchestration complete[/bold green]"
                        if not failed
                        else "\n  [bold red]☁️  Group orchestration failed[/bold red]",
                    )
                    display.console.print(
                        f"  Platform: [cyan]{meta.get('platform', 'vertex_ai')}[/cyan]"
                        f"  Project: [cyan]{meta.get('project', '')}[/cyan]"
                        f"  Region: [cyan]{meta.get('region', '')}[/cyan]",
                    )
                    display.console.print(f"  Execution units: [bold]{total}[/bold]\n")

                    for g in groups:
                        status = g.get("status", "UNKNOWN")
                        icon = "✅" if status == "SUCCEEDED" else "❌"
                        steps_str = ", ".join(g.get("steps", []))
                        machine = g.get("machine_type", "auto")
                        display.console.print(
                            f"  {icon} [bold]{g['group_name']}[/bold]  ({machine})  → {steps_str}",
                        )
                    if failed:
                        display.console.print(
                            f"\n  [red]Failed at: {failed}[/red]",
                        )
                        if meta.get("error"):
                            display.console.print(f"  [red]{meta['error']}[/red]")
                else:
                    display.console.print(
                        "\n  [bold green]☁️  Job submitted to remote orchestrator[/bold green]",
                    )
                    display.console.print(f"  Job ID: {result.job_id}")
                    if meta:
                        for k, v in meta.items():
                            if k != "groups":
                                display.console.print(f"  {k}: {v}")
            self._save_run(wrapper)
            self._save_pipeline_definition()
            return wrapper

        if display and not isinstance(result, str):
            display.show_summary(result, ui_url=ui_url, run_url=run_url)

        # If result is just a job ID (remote execution), wrap it in a basic result
        if isinstance(result, str):
            # Create a submitted result wrapper
            wrapper = PipelineResult(run_id, self.name)
            wrapper.attach_configs(resource_config, docker_cfg)
            wrapper.mark_submitted(result)
            self._save_run(wrapper)
            self._save_pipeline_definition()
            return wrapper

        # Auto-freeze pipeline snapshot for reproducibility
        try:
            from flowyml.core.versioning import freeze_pipeline

            snapshot = freeze_pipeline(self)
            if hasattr(result, "snapshot_hash"):
                result.snapshot_hash = snapshot.snapshot_hash
        except Exception:
            pass  # Don't fail run if snapshot fails

        # Ensure result has configs attached (in case orchestrator didn't do it)
        if hasattr(result, "attach_configs") and not hasattr(result, "resource_config"):
            result.attach_configs(resource_config, docker_cfg)

        # --- End External Tracker Run (dual-write) ---
        if integration is not None:
            try:
                is_success = getattr(result, "success", False)
                integration.on_pipeline_end(
                    success=is_success,
                    result=result,
                )
            except Exception as e:
                import logging as _logging

                _logging.getLogger(__name__).debug(
                    "External tracker integration end skipped: %s",
                    e,
                )

        return result

    def rerun(
        self,
        run_id: str,
        from_step: str | None = None,
        **kwargs: Any,
    ) -> "PipelineResult":
        """Re-run a pipeline from a checkpoint, resuming from where it left off.

        Args:
            run_id: The run ID of the previous execution to resume from.
            from_step: Optional step name to start re-execution from.
                       If provided, all steps before this one are skipped.
                       If not provided, resumes from the first non-completed step.
            **kwargs: Additional arguments passed to Pipeline.run().

        Returns:
            PipelineResult with outputs from the resumed run.

        Examples:
            >>> # Resume from last checkpoint
            >>> result = pipeline.rerun(run_id="previous-run-id")
            >>> # Resume from a specific step
            >>> result = pipeline.rerun(run_id="previous-run-id", from_step="train_model")
        """
        from flowyml.core.checkpoint import PipelineCheckpoint
        from flowyml.utils.config import get_config

        config = get_config()
        checkpoint = PipelineCheckpoint(
            run_id=run_id,
            checkpoint_dir=str(config.checkpoint_dir),
        )

        if not checkpoint.exists():
            raise ValueError(
                f"No checkpoint found for run_id='{run_id}'. "
                "Cannot resume — run the pipeline fresh with pipeline.run() instead.",
            )

        # Determine which steps to skip
        completed = checkpoint.get_completed_steps()

        if from_step:
            # Skip only steps that come before from_step
            steps_to_skip = set()
            for step_name in completed:
                if step_name == from_step:
                    break
                steps_to_skip.add(step_name)
        else:
            # Skip all completed steps (resume from first non-completed)
            steps_to_skip = set(completed) - {"pipeline_complete"}

        # Set checkpoint state on pipeline for orchestrator to use
        self._checkpoint = checkpoint
        self._resume_from_checkpoint = True
        self._completed_steps_from_checkpoint = steps_to_skip

        import logging

        logger = logging.getLogger("flowyml.checkpoint")
        logger.info(
            f"Re-running pipeline '{self.name}' from run '{run_id}'. "
            f"Skipping {len(steps_to_skip)} completed step(s)."
            + (f" Starting from step '{from_step}'." if from_step else ""),
        )

        # Run with the checkpoint state already configured
        return self.run(run_id=run_id, **kwargs)

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
                    "execution_group": step.execution_group,
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

    def _ensure_ui_server(self, run_id: str) -> tuple[str | None, str | None, bool]:
        """Ensure UI server is running, start it if needed, or show guidance.

        Args:
            run_id: The run ID for generating the run URL

        Returns:
            Tuple of (ui_url, run_url, start_failed)
            - ui_url: Base URL of the UI server if running
            - run_url: URL to view this specific run if server is running
            - start_failed: True if we tried to start and failed (show guidance)
        """
        import subprocess
        import sys
        import time
        from pathlib import Path

        try:
            from flowyml.ui.utils import is_ui_running, get_ui_host_port
        except ImportError:
            return None, None, False

        host, port = get_ui_host_port()
        url = f"http://{host}:{port}"

        # Check if already running
        if is_ui_running(host, port):
            return url, f"{url}/runs/{run_id}", False

        # Try to start the UI server as a background subprocess
        try:
            # Check if uvicorn is available
            try:
                import uvicorn  # noqa: F401
            except ImportError:
                # uvicorn not installed, show guidance but don't fail
                self._show_ui_guidance(host, port, reason="missing_deps")
                return None, None, True

            # Start uvicorn as a background process
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "flowyml.ui.backend.main:app",
                "--host",
                host,
                "--port",
                str(port),
                "--log-level",
                "warning",
            ]

            # Start as detached background process
            if sys.platform == "win32":
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

            # Wait for server to start (up to 8 seconds)
            started = False
            for _ in range(80):
                time.sleep(0.1)
                if is_ui_running(host, port):
                    started = True
                    break

            if started:
                # Save PID for later stop command
                pid_file = Path.home() / ".flowyml" / "ui_server.pid"
                pid_file.parent.mkdir(parents=True, exist_ok=True)
                pid_file.write_text(f"{process.pid}\n{host}\n{port}")

                return url, f"{url}/runs/{run_id}", False
            else:
                # Server didn't start, kill the process and show guidance
                process.terminate()
                self._show_ui_guidance(host, port, reason="start_failed")
                return None, None, True

        except Exception:
            # Show guidance on failure
            self._show_ui_guidance(host, port, reason="error")
            return None, None, True

    def _show_ui_guidance(self, host: str, port: int, reason: str = "not_running") -> None:
        """Show a helpful message guiding the user to start the UI server.

        Args:
            host: Host the server should run on
            port: Port the server should run on
            reason: Why we're showing guidance (not_running, missing_deps, start_failed, error)
        """
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.text import Text
            from rich import box

            console = Console()

            content = Text()
            content.append("💡 ", style="yellow")
            content.append("Want to see your pipeline run in a live dashboard?\n\n", style="bold")

            if reason == "missing_deps":
                content.append("UI dependencies not installed. ", style="dim")
                content.append("Install with:\n", style="")
                content.append("  pip install uvicorn fastapi\n\n", style="bold cyan")

            content.append("Start the dashboard with:\n", style="")
            content.append("  flowyml go", style="bold green")

            if port != 8080:
                content.append(f" --port {port}", style="bold green")

            content.append("\n\n", style="")
            content.append("Then run your pipeline again to see it in the UI!", style="dim")

            console.print()
            console.print(
                Panel(
                    content,
                    title="[bold cyan]🌐 Dashboard Available[/bold cyan]",
                    border_style="yellow",
                    box=box.ROUNDED,
                ),
            )
            console.print()

        except ImportError:
            # Fallback to simple print
            print()
            print("=" * 60)
            print("💡 Want to see your pipeline run in a live dashboard?")
            print()
            if reason == "missing_deps":
                print("   UI dependencies not installed. Install with:")
                print("     pip install uvicorn fastapi")
                print()
            print("   Start the dashboard with:")
            print("     flowyml go" + (f" --port {port}" if port != 8080 else ""))
            print()
            print("   Then run your pipeline again to see it in the UI!")
            print("=" * 60)
            print()

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

    def _log_experiment_metrics(self, result: PipelineResult) -> None:
        """Automatically log Metrics to experiment tracking (dual-write).

        This method handles the **internal** side of dual-write:
        - Always writes to FlowyML's Experiment/Run tracking system (SQLite)
        - The **external** side (MLflow/WandB) is handled by PipelinePluginIntegration
          hooks in Pipeline.run()

        When auto_track is enabled (default), delegates to AutoTracker which
        collects metrics from all step outputs (plain dicts, Metrics assets,
        scalars) and parameters from context, stack, and environment.

        When auto_track is disabled, falls back to the legacy extraction that
        only handles Metrics assets.

        This is called automatically after each pipeline run if experiment tracking is enabled.
        """
        from flowyml.utils.config import get_config

        config = get_config()

        # Check if experiment tracking is enabled (default: True)
        enable_tracking = getattr(self, "enable_experiment_tracking", None)
        if enable_tracking is None:
            enable_tracking = getattr(config, "auto_log_metrics", True)

        if not enable_tracking:
            return

        # --- AUTO-TRACKER PATH (new, preferred) ---
        if self._auto_tracker:
            try:
                # Extract step-level metrics from any outputs not yet processed
                # (e.g., steps whose results arrived after the hooks fired)
                for step_name, step_result in result.step_results.items():
                    if step_name not in self._auto_tracker._step_metrics:
                        self._auto_tracker.extract_step_metrics(step_name, step_result)

                # Finalize — logs to internal tracker (Experiment + Run)
                self._auto_tracker.finalize_run(self, result)
                return
            except Exception as e:
                import warnings

                warnings.warn(
                    f"AutoTracker finalization failed, falling back to legacy: {e}",
                    stacklevel=2,
                )
                # Fall through to legacy path

        # --- LEGACY PATH (fallback when auto_track=False or AutoTracker fails) ---
        from flowyml.assets.metrics import Metrics

        # Extract all Metrics from pipeline outputs
        all_metrics = {}
        for output_name, output_value in result.outputs.items():
            if isinstance(output_value, Metrics):
                metrics_dict = output_value.get_all_metrics() or output_value.data or {}
                for key, value in metrics_dict.items():
                    if output_name == "metrics" or output_name.endswith("/metrics"):
                        all_metrics[key] = value
                    else:
                        all_metrics[f"{output_name}.{key}"] = value
            elif isinstance(output_value, dict):
                for key, val in output_value.items():
                    if isinstance(val, Metrics):
                        metrics_dict = val.get_all_metrics() or val.data or {}
                        for mkey, mval in metrics_dict.items():
                            all_metrics[f"{key}.{mkey}"] = mval

        # Extract context parameters
        context_params = {}
        if self.context:
            context_params = self.context.to_dict()

        # --- Internal FlowyML tracking (always) ---
        if all_metrics or context_params:
            try:
                from flowyml.tracking.experiment import Experiment
                from flowyml.tracking.runs import Run

                experiment_name = self.name
                experiment = Experiment(
                    name=experiment_name,
                    description=f"Auto-tracked experiment for pipeline: {self.name}",
                )

                experiment.log_run(
                    run_id=result.run_id,
                    metrics=all_metrics,
                    parameters=context_params,
                )

                run = Run(
                    run_id=result.run_id,
                    pipeline_name=self.name,
                    parameters=context_params,
                )
                if all_metrics:
                    run.log_metrics(all_metrics)
                run.complete(status="success" if result.success else "failed")

            except Exception as e:
                import warnings

                warnings.warn(f"Failed to log experiment metrics: {e}", stacklevel=2)

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
                "execution_group": step.execution_group,
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
            "project": getattr(self, "project_name", None),  # Include project for stats tracking
        }
        self.metadata_store.save_run(result.run_id, metadata)

        # Automatic experiment tracking: Extract Metrics and log to experiments
        self._log_experiment_metrics(result)

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
                elif isinstance(step_result.output, (list, tuple)) and len(output_names) == len(
                    step_result.output,
                ):
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
                        # Get properties
                        props = (
                            self._sanitize_for_json(value.metadata.properties)
                            if hasattr(value.metadata, "properties")
                            else {}
                        )

                        # For Dataset assets, include the full data for visualization
                        # This enables histograms and statistics in the UI
                        data_value = None
                        if asset_type == "Dataset" and value.data is not None:
                            try:
                                # Store full data as JSON-serializable dict
                                data_value = self._sanitize_for_json(value.data)
                                props["_full_data"] = data_value
                            except Exception:
                                data_value = str(value.data)[:1000]
                        else:
                            data_value = str(value.data)[:1000] if value.data is not None else None

                        artifact_metadata = {
                            "artifact_id": artifact_id,
                            "name": value.name,
                            "type": asset_type,
                            "run_id": result.run_id,
                            "step": step_name,
                            "path": None,
                            "value": data_value if isinstance(data_value, str) else None,
                            "created_at": datetime.now().isoformat(),
                            "properties": props,
                        }

                        # For Dataset, also include the data directly in the artifact
                        if asset_type == "Dataset" and isinstance(data_value, dict):
                            artifact_metadata["data"] = data_value

                        # Include training_history if present (for Model assets with Keras training)
                        # This enables interactive training charts in the UI
                        if hasattr(value, "training_history") and value.training_history:
                            artifact_metadata["training_history"] = value.training_history

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

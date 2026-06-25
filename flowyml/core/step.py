"""Step Decorator - Define pipeline steps with automatic context injection."""

import contextlib
import hashlib
import inspect
import json
from typing import Any, Union
from collections.abc import Callable
from dataclasses import dataclass, field

# Import resource types
try:
    from flowyml.core.resources import ResourceRequirements, GPUConfig
except ImportError:
    ResourceRequirements = None  # Type: ignore
    GPUConfig = None  # Type: ignore


class StepRegistry:
    """Global registry for auto-discovered pipeline steps.

    Every ``@step``-decorated function is automatically registered here,
    enabling pipelines to auto-discover their steps from artifact
    dependencies instead of requiring manual ``add_step()`` calls.

    The registry supports **pipeline-scoped filtering** via the
    ``pipeline`` tag on ``@step(pipeline="training")``, so steps from
    different modules don't leak into unrelated pipelines.

    Example:
        >>> from flowyml.core.step import get_registered_steps, clear_step_registry
        >>> steps = get_registered_steps()  # all steps
        >>> steps = get_registered_steps("training")  # only steps tagged for "training"
        >>> clear_step_registry()  # reset (useful in tests)
    """

    def __init__(self) -> None:
        self._steps: dict[str, Step] = {}

    def register(self, step: "Step") -> None:
        """Register a step in the global registry.

        Args:
            step: Step instance to register.

        Raises:
            ValueError: If a step with the same name is already registered.
        """
        if step.name in self._steps:
            existing = self._steps[step.name]
            # Allow re-registration of the exact same object (e.g. module reload)
            if existing is not step:
                raise ValueError(
                    f"Step '{step.name}' is already registered. "
                    "Use a unique name or set register=False on one of them.",
                )
        self._steps[step.name] = step

    def get_all(self, pipeline: str | None = None) -> list["Step"]:
        """Return all registered steps, optionally filtered by pipeline tag.

        Args:
            pipeline: If provided, only return steps whose ``pipeline``
                      tag matches this value. Steps without a pipeline
                      tag are included in all queries.

        Returns:
            List of matching Step instances.
        """
        if pipeline is None:
            return list(self._steps.values())

        return [s for s in self._steps.values() if s.tags.get("pipeline") in (pipeline, None)]

    def get_by_name(self, name: str) -> "Step | None":
        """Look up a registered step by name."""
        return self._steps.get(name)

    def clear(self) -> None:
        """Remove all registered steps. Essential for test isolation."""
        self._steps.clear()

    def __len__(self) -> int:
        return len(self._steps)

    def __contains__(self, name: str) -> bool:
        return name in self._steps

    def __repr__(self) -> str:
        return f"StepRegistry({len(self._steps)} steps)"


# Module-level singleton
_global_registry = StepRegistry()


def get_registered_steps(pipeline: str | None = None) -> list["Step"]:
    """Get all globally registered steps, optionally filtered by pipeline.

    Args:
        pipeline: Optional pipeline name to filter by.

    Returns:
        List of registered Step instances.
    """
    return _global_registry.get_all(pipeline)


def clear_step_registry() -> None:
    """Clear the global step registry. Use in test tearDown."""
    _global_registry.clear()


@dataclass
class StepConfig:
    """Configuration for a pipeline step."""

    name: str
    func: Callable
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    cache: bool | str | Callable = "code_hash"
    retry: int = 0
    timeout: int | None = None
    resources: Union[dict[str, Any], "ResourceRequirements", None] = None
    tags: dict[str, str] = field(default_factory=dict)
    condition: Callable | None = None
    execution_group: str | None = None
    source_file: str | None = None
    source_line: int | None = None

    def __hash__(self):
        """Make StepConfig hashable."""
        return hash(self.name)


class Step:
    """A pipeline step that can be executed with automatic context injection."""

    def __init__(
        self,
        func: Callable,
        name: str | None = None,
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        cache: bool | str | Callable = "code_hash",
        retry: int = 0,
        timeout: int | None = None,
        resources: Union[dict[str, Any], "ResourceRequirements", None] = None,
        tags: dict[str, str] | None = None,
        condition: Callable | None = None,
        execution_group: str | None = None,
    ):
        self.func = func
        self.name = name or func.__name__
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.cache = cache
        self.retry = retry
        self.timeout = timeout

        # Store resources (accept both dict for backward compatibility and ResourceRequirements)
        self.resources = resources
        if self.resources and ResourceRequirements and not isinstance(self.resources, ResourceRequirements):
            if isinstance(self.resources, dict):
                resource_kwargs = dict(self.resources)
                gpu_value = resource_kwargs.get("gpu")
                if GPUConfig and gpu_value is not None:
                    if isinstance(gpu_value, dict):
                        resource_kwargs["gpu"] = GPUConfig(
                            gpu_type=gpu_value.get("gpu_type") or gpu_value.get("type") or "generic",
                            count=int(gpu_value.get("count", 1)),
                            memory=gpu_value.get("memory"),
                        )
                    elif isinstance(gpu_value, (int, float)):
                        resource_kwargs["gpu"] = GPUConfig(gpu_type="generic", count=int(gpu_value))
                with contextlib.suppress(TypeError):
                    self.resources = ResourceRequirements(**resource_kwargs)

        self.tags = tags or {}
        self.condition = condition
        self.execution_group = execution_group

        # Capture source code and location for UI display
        try:
            self.source_code = inspect.getsource(func)
            self.source_file = inspect.getsourcefile(func)
            _, self.source_line = inspect.getsourcelines(func)
        except (OSError, TypeError):
            self.source_code = "# Source code not available"
            self.source_file = None
            self.source_line = None

        self.config = StepConfig(
            name=self.name,
            func=func,
            inputs=self.inputs,
            outputs=self.outputs,
            cache=self.cache,
            retry=self.retry,
            timeout=self.timeout,
            resources=self.resources,
            tags=self.tags,
            condition=self.condition,
            execution_group=self.execution_group,
            source_file=self.source_file,
            source_line=self.source_line,
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the step function."""
        # Check condition if present
        if self.condition:
            # We might need to inject context into condition too,
            # but for now assume it takes no args or same args as step?
            # This is tricky without context injection logic here.
            # The executor handles execution, so maybe we just store it here.
            pass

        return self.func(*args, **kwargs)

    def get_code_hash(self) -> str:
        """Compute hash of the step's source code."""
        try:
            source = inspect.getsource(self.func)
            return hashlib.md5(source.encode()).hexdigest()
        except (OSError, TypeError):
            # Fallback for dynamically defined functions or when source is unavailable
            return hashlib.md5(self.name.encode()).hexdigest()[:16]

    def get_input_hash(self, inputs: dict[str, Any]) -> str:
        """Generate hash of inputs for caching."""
        input_str = json.dumps(inputs, sort_keys=True, default=str)
        return hashlib.sha256(input_str.encode()).hexdigest()[:16]

    def get_cache_key(
        self,
        inputs: dict[str, Any] | None = None,
        context_params: dict[str, Any] | None = None,
    ) -> str:
        """Generate cache key based on caching strategy.

        Args:
            inputs: Input data for the step
            context_params: Context parameters injected into the step.
                Included in the cache key to prevent stale cache hits
                when the same step runs with different context values.

        Returns:
            Cache key string
        """
        # Compute context suffix so that different context values produce
        # different cache keys for the same step name + code.
        ctx_suffix = ""
        if context_params:
            ctx_str = json.dumps(context_params, sort_keys=True, default=str)
            ctx_suffix = ":" + hashlib.sha256(ctx_str.encode()).hexdigest()[:12]

        if self.cache == "code_hash":
            return f"{self.name}:{self.get_code_hash()}{ctx_suffix}"
        elif self.cache == "input_hash" and inputs:
            return f"{self.name}:{self.get_input_hash(inputs)}{ctx_suffix}"
        elif callable(self.cache) and inputs:
            return self.cache(inputs, {})
        else:
            return f"{self.name}:no-cache"

    def __repr__(self) -> str:
        return f"Step(name='{self.name}', inputs={self.inputs}, outputs={self.outputs})"


def step(
    _func: Callable | None = None,
    *,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    cache: bool | str | Callable = "code_hash",
    retry: int = 0,
    timeout: int | None = None,
    resources: Union[dict[str, Any], "ResourceRequirements", None] = None,
    tags: dict[str, str] | None = None,
    name: str | None = None,
    condition: Callable | None = None,
    execution_group: str | None = None,
    pipeline: str | None = None,
    register: bool = True,
):
    """Decorator to define a pipeline step with automatic context injection.

    Can be used as @step or @step(inputs=...)

    Every decorated function is automatically registered in a global
    ``StepRegistry``, enabling ``Pipeline(auto_discover=True)`` to build
    the DAG without any manual ``add_step()`` calls.

    Args:
        _func: Function being decorated (when used as @step)
        inputs: List of input asset names
        outputs: List of output asset names
        cache: Caching strategy ("code_hash", "input_hash", callable, or False)
        retry: Number of retry attempts on failure
        timeout: Maximum execution time in seconds
        resources: Resource requirements (ResourceRequirements object or dict for backward compat)
        tags: Metadata tags for the step
        name: Optional custom name for the step
        condition: Optional callable that returns True if step should run
        execution_group: Optional group name for executing multiple steps together
        pipeline: Optional pipeline name for scoped auto-discovery.
            When set, the step is only auto-discovered by pipelines
            that match this name (or by ``get_registered_steps(pipeline="...")``).
        register: If False, the step is NOT added to the global registry.
            Defaults to True. Set to False for helper/utility steps that
            should only be used via explicit ``add_step()``.

    Example:
        >>> @step
        ... def simple_step():
        ...     ...
        >>> @step(inputs=["data/train"], outputs=["model/trained"])
        ... def train_model(train_data):
        ...     ...
        >>> # Scoped to a specific pipeline
        >>> @step(pipeline="training", outputs=["model"])
        ... def train(data):
        ...     ...
        >>> # With resource requirements
        >>> from flowyml.core.resources import ResourceRequirements, GPUConfig
        >>> @step(resources=ResourceRequirements(cpu="4", memory="16Gi", gpu=GPUConfig(gpu_type="nvidia-v100", count=2)))
        ... def gpu_train(data):
        ...     ...
    """

    def decorator(func: Callable) -> Step:
        # Merge pipeline tag into tags dict
        merged_tags = dict(tags) if tags else {}
        if pipeline is not None:
            merged_tags["pipeline"] = pipeline

        step_instance = Step(
            func=func,
            name=name,
            inputs=inputs,
            outputs=outputs,
            cache=cache,
            retry=retry,
            timeout=timeout,
            resources=resources,
            tags=merged_tags if merged_tags else None,
            condition=condition,
            execution_group=execution_group,
        )

        # Auto-register in global registry
        if register:
            _global_registry.register(step_instance)

        return step_instance

    if _func is None:
        return decorator
    else:
        return decorator(_func)

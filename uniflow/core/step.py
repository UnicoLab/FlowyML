"""Step Decorator - Define pipeline steps with automatic context injection."""

import hashlib
import inspect
import json
from typing import Any
from collections.abc import Callable
from dataclasses import dataclass, field


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
    resources: dict[str, Any] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    condition: Callable | None = None

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
        resources: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
        condition: Callable | None = None,
    ):
        self.func = func
        self.name = name or func.__name__
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.cache = cache
        self.retry = retry
        self.timeout = timeout
        self.resources = resources or {}
        self.tags = tags or {}
        self.condition = condition

        # Capture source code for UI display
        try:
            self.source_code = inspect.getsource(func)
        except (OSError, TypeError):
            self.source_code = "# Source code not available"

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
        )

    def __call__(self, *args, **kwargs):
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

    def get_cache_key(self, inputs: dict[str, Any] | None = None) -> str:
        """Generate cache key based on caching strategy.

        Args:
            inputs: Input data for the step

        Returns:
            Cache key string
        """
        if self.cache == "code_hash":
            return f"{self.name}:{self.get_code_hash()}"
        elif self.cache == "input_hash" and inputs:
            return f"{self.name}:{self.get_input_hash(inputs)}"
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
    resources: dict[str, Any] | None = None,
    tags: dict[str, str] | None = None,
    name: str | None = None,
    condition: Callable | None = None,
):
    """Decorator to define a pipeline step with automatic context injection.

    Can be used as @step or @step(inputs=...)

    Args:
        _func: Function being decorated (when used as @step)
        inputs: List of input asset names
        outputs: List of output asset names
        cache: Caching strategy ("code_hash", "input_hash", callable, or False)
        retry: Number of retry attempts on failure
        timeout: Maximum execution time in seconds
        resources: Resource requirements (e.g., {"gpu": 1, "memory": "16GB"})
        tags: Metadata tags for the step
        name: Optional custom name for the step
        condition: Optional callable that returns True if step should run

    Example:
        >>> @step
        ... def simple_step():
        ...     ...
        >>> @step(inputs=["data/train"], outputs=["model/trained"])
        ... def train_model(train_data):
        ...     ...
    """

    def decorator(func: Callable) -> Step:
        return Step(
            func=func,
            name=name,
            inputs=inputs,
            outputs=outputs,
            cache=cache,
            retry=retry,
            timeout=timeout,
            resources=resources,
            tags=tags,
            condition=condition,
        )

    if _func is None:
        return decorator
    else:
        return decorator(_func)

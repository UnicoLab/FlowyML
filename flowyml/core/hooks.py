"""Lifecycle hooks for pipelines and steps."""

from typing import Any, TYPE_CHECKING
from collections.abc import Callable
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from flowyml.core.pipeline import Pipeline, PipelineResult
    from flowyml.core.step import Step
    from flowyml.core.executor import ExecutionResult


@dataclass
class HookRegistry:
    """Registry for pipeline and step lifecycle hooks."""

    # Pipeline-level hooks
    on_pipeline_start: list[Callable[["Pipeline"], None]] = field(default_factory=list)
    on_pipeline_end: list[Callable[["Pipeline", "PipelineResult"], None]] = field(default_factory=list)

    # Step-level hooks
    on_step_start: list[Callable[["Step", dict[str, Any]], None]] = field(default_factory=list)
    on_step_end: list[Callable[["Step", "ExecutionResult"], None]] = field(default_factory=list)

    def register_pipeline_start_hook(self, hook: Callable[["Pipeline"], None]) -> None:
        """Register a hook to run at pipeline start."""
        self.on_pipeline_start.append(hook)

    def register_pipeline_end_hook(self, hook: Callable[["Pipeline", "PipelineResult"], None]) -> None:
        """Register a hook to run at pipeline end."""
        self.on_pipeline_end.append(hook)

    def register_step_start_hook(self, hook: Callable[["Step", dict[str, Any]], None]) -> None:
        """Register a hook to run before step execution."""
        self.on_step_start.append(hook)

    def register_step_end_hook(self, hook: Callable[["Step", "ExecutionResult"], None]) -> None:
        """Register a hook to run after step execution."""
        self.on_step_end.append(hook)

    def run_pipeline_start_hooks(self, pipeline: "Pipeline") -> None:
        """Execute all pipeline start hooks."""
        for hook in self.on_pipeline_start:
            try:
                hook(pipeline)
            except Exception as e:
                print(f"Warning: Pipeline start hook failed: {e}")

    def run_pipeline_end_hooks(self, pipeline: "Pipeline", result: "PipelineResult") -> None:
        """Execute all pipeline end hooks."""
        for hook in self.on_pipeline_end:
            try:
                hook(pipeline, result)
            except Exception as e:
                print(f"Warning: Pipeline end hook failed: {e}")

    def run_step_start_hooks(self, step: "Step", inputs: dict[str, Any]) -> None:
        """Execute all step start hooks."""
        for hook in self.on_step_start:
            try:
                hook(step, inputs)
            except Exception as e:
                print(f"Warning: Step start hook failed: {e}")

    def run_step_end_hooks(self, step: "Step", result: "ExecutionResult") -> None:
        """Execute all step end hooks."""
        for hook in self.on_step_end:
            try:
                hook(step, result)
            except Exception as e:
                print(f"Warning: Step end hook failed: {e}")


# Global hook registry
_global_hooks = HookRegistry()


def get_global_hooks() -> HookRegistry:
    """Get the global hook registry."""
    return _global_hooks


def on_pipeline_start(func: Callable[["Pipeline"], None]) -> Callable[["Pipeline"], None]:
    """Decorator to register a pipeline start hook."""
    _global_hooks.register_pipeline_start_hook(func)
    return func


def on_pipeline_end(
    func: Callable[["Pipeline", "PipelineResult"], None],
) -> Callable[["Pipeline", "PipelineResult"], None]:
    """Decorator to register a pipeline end hook."""
    _global_hooks.register_pipeline_end_hook(func)
    return func


def on_step_start(func: Callable[["Step", dict[str, Any]], None]) -> Callable[["Step", dict[str, Any]], None]:
    """Decorator to register a step start hook."""
    _global_hooks.register_step_start_hook(func)
    return func


def on_step_end(func: Callable[["Step", "ExecutionResult"], None]) -> Callable[["Step", "ExecutionResult"], None]:
    """Decorator to register a step end hook."""
    _global_hooks.register_step_end_hook(func)
    return func

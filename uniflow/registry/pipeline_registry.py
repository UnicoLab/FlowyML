"""Pipeline registry for managing available pipelines."""

from collections.abc import Callable
from uniflow.core.pipeline import Pipeline


class PipelineRegistry:
    """Registry for pipelines to enable lookup by name.

    Crucial for scheduling and remote execution where we need to
    find a pipeline definition by its string name.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.pipelines = {}
        return cls._instance

    def register(self, name: str, pipeline_factory: Callable[..., Pipeline]) -> None:
        """Register a pipeline factory function.

        Args:
            name: Unique name for the pipeline
            pipeline_factory: Function that returns a Pipeline instance
        """
        self.pipelines[name] = pipeline_factory

    def get(self, name: str) -> Callable[..., Pipeline] | None:
        """Get a pipeline factory by name."""
        return self.pipelines.get(name)

    def list_pipelines(self) -> dict[str, str]:
        """List all registered pipelines."""
        return {name: str(func) for name, func in self.pipelines.items()}

    def clear(self) -> None:
        """Clear all registrations."""
        self.pipelines = {}


# Global instance
pipeline_registry = PipelineRegistry()


def register_pipeline(name: str):
    """Decorator to register a pipeline factory."""

    def decorator(func):
        pipeline_registry.register(name, func)
        return func

    return decorator

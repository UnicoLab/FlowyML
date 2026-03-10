"""Dynamic Workflows — Runtime DAG Generation.

Inspired by Flyte's dynamic node handler, this module provides a `@dynamic`
decorator that allows steps to generate sub-pipelines at runtime based on
intermediate results. The generated DAG is expanded into the parent pipeline's
execution plan.

Usage:
    from flowyml.core.dynamic import dynamic

    @dynamic
    def hyperparameter_search(config: dict) -> Pipeline:
        from flowyml import Pipeline, step

        sub = Pipeline("hp_search")
        for lr in config["learning_rates"]:
            @step(outputs=[f"model_lr_{lr}"])
            def train(learning_rate=lr):
                return train_model(learning_rate)
            sub.add_step(train)
        return sub
"""

import logging
from typing import Any
from collections.abc import Callable

logger = logging.getLogger(__name__)


class DynamicWorkflowResult:
    """Result wrapper from a dynamic workflow expansion.

    Attributes:
        sub_pipeline: The dynamically generated sub-pipeline
        results: Aggregated results from the sub-pipeline execution
        expanded: Whether the DAG was expanded successfully
    """

    def __init__(self, sub_pipeline: Any = None, results: Any = None):
        self.sub_pipeline = sub_pipeline
        self.results = results
        self.expanded = sub_pipeline is not None


class DynamicStep:
    """A step that dynamically generates a sub-pipeline at runtime.

    When executed, the decorated function returns a Pipeline object whose
    steps are then expanded into the parent execution context.
    """

    def __init__(
        self,
        func: Callable,
        name: str | None = None,
        **step_kwargs,
    ):
        from flowyml.core.step import Step

        self._dynamic_func = func
        self._step_kwargs = step_kwargs

        # Create the wrapper step
        self.step = Step(
            func=self._execute_dynamic,
            name=name or func.__name__,
            **step_kwargs,
        )

        # Mark as dynamic for orchestrator detection
        self.step._is_dynamic = True
        self.step._dynamic_func = func

        self.name = self.step.name
        self.func = self._execute_dynamic
        self.inputs = self.step.inputs
        self.outputs = self.step.outputs

    def _execute_dynamic(self, *args, **kwargs) -> DynamicWorkflowResult:
        """Execute the dynamic function and run the resulting sub-pipeline.

        Args:
            *args: Arguments passed to the dynamic function
            **kwargs: Keyword arguments passed to the dynamic function

        Returns:
            DynamicWorkflowResult with the sub-pipeline and its results
        """
        from flowyml.core.pipeline import Pipeline

        # Call the dynamic function to get the sub-pipeline
        sub_pipeline = self._dynamic_func(*args, **kwargs)

        if sub_pipeline is None:
            logger.warning(
                f"Dynamic step '{self.name}' returned None — " f"no sub-pipeline to execute",
            )
            return DynamicWorkflowResult()

        if not isinstance(sub_pipeline, Pipeline):
            # If the function returned something other than a Pipeline,
            # wrap it as a direct result
            logger.debug(
                f"Dynamic step '{self.name}' returned a non-Pipeline value — " f"treating as direct result",
            )
            return DynamicWorkflowResult(results=sub_pipeline)

        # Execute the sub-pipeline
        logger.info(
            f"Dynamic step '{self.name}' expanding sub-pipeline "
            f"'{sub_pipeline.name}' with {len(sub_pipeline.steps)} steps",
        )

        result = sub_pipeline.run(auto_start_ui=False)

        return DynamicWorkflowResult(
            sub_pipeline=sub_pipeline,
            results=result,
        )

    def __call__(self, *args, **kwargs):
        """Call the dynamic step."""
        return self._execute_dynamic(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate attribute access to the underlying step."""
        return getattr(self.step, name)


def dynamic(
    _func: Callable | None = None,
    *,
    name: str | None = None,
    **step_kwargs,
):
    """Decorator to create a dynamic workflow step.

    The decorated function should return a Pipeline object. At runtime,
    the returned pipeline is built and executed as part of the parent
    pipeline's execution.

    Args:
        _func: Function being decorated (when used as @dynamic)
        name: Optional custom step name
        **step_kwargs: Additional Step kwargs (inputs, outputs, etc.)

    Example:
        >>> @dynamic(outputs=["best_model"])
        ... def hyperparameter_search(config: dict):
        ...     from flowyml import Pipeline, step
        ...
        ...     sub = Pipeline("hp_search")
        ...     for lr in config["learning_rates"]:
        ...
        ...         @step(outputs=[f"model_{lr}"])
        ...         def train(learning_rate=lr):
        ...             return train_model(learning_rate)
        ...
        ...         sub.add_step(train)
        ...     return sub
        >>>
        >>> pipeline.add_step(hyperparameter_search)
    """

    def decorator(func: Callable) -> DynamicStep:
        return DynamicStep(
            func=func,
            name=name,
            **step_kwargs,
        )

    if _func is None:
        return decorator
    else:
        return decorator(_func)

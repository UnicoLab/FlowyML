"""Sub-Pipeline Composition — Nest pipelines as steps in other pipelines.

Inspired by Flyte's subworkflow handler, this module provides a
`SubPipelineStep` class that wraps a Pipeline as a Step, enabling
hierarchical pipeline composition.

Usage:
    from flowyml import Pipeline, step
    from flowyml.core.subpipeline import SubPipelineStep

    # Define child pipeline
    preprocess_pipeline = Pipeline("preprocessing")
    preprocess_pipeline.add_step(clean_data).add_step(normalize)

    # Use in parent pipeline
    parent = Pipeline("training")
    parent.add_sub_pipeline(preprocess_pipeline, inputs=["raw_data"], outputs=["clean_data"])
    parent.add_step(train_model)
"""

import logging
from typing import Any

from flowyml.core.step import Step

logger = logging.getLogger(__name__)


class SubPipelineStep(Step):
    """A step that wraps and executes an entire sub-pipeline.

    Maps parent pipeline outputs to child pipeline inputs and flattens
    child results back into the parent context.

    Attributes:
        sub_pipeline: The child Pipeline object to execute
        input_mapping: Optional mapping of parent → child input names
        output_mapping: Optional mapping of child → parent output names
    """

    def __init__(
        self,
        sub_pipeline: Any,  # Pipeline
        name: str | None = None,
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        input_mapping: dict[str, str] | None = None,
        output_mapping: dict[str, str] | None = None,
        **step_kwargs,
    ):
        """Initialize sub-pipeline step.

        Args:
            sub_pipeline: The Pipeline to wrap as a step
            name: Step name (defaults to sub_pipeline.name)
            inputs: Input asset names from parent pipeline
            outputs: Output asset names exposed to parent pipeline
            input_mapping: Maps parent input names to child input names
                          e.g., {"parent_data": "raw_data"}
            output_mapping: Maps child output names to parent output names
                          e.g., {"processed": "clean_data"}
            **step_kwargs: Additional Step configuration
        """
        self.sub_pipeline = sub_pipeline
        self.input_mapping = input_mapping or {}
        self.output_mapping = output_mapping or {}

        # Use sub-pipeline name as step name if not provided
        step_name = name or f"sub:{sub_pipeline.name}"

        super().__init__(
            func=self._execute_sub_pipeline,
            name=step_name,
            inputs=inputs or [],
            outputs=outputs or [],
            **step_kwargs,
        )

        # Mark as sub-pipeline for orchestrator detection
        self._is_sub_pipeline = True

    def _execute_sub_pipeline(self, *args, **kwargs) -> Any:
        """Execute the sub-pipeline with mapped inputs.

        Args:
            *args: Positional arguments (parent pipeline outputs)
            **kwargs: Keyword arguments (parent pipeline outputs)

        Returns:
            Results from the sub-pipeline
        """
        # Map parent inputs to child inputs
        child_inputs = {}

        for parent_name, child_name in self.input_mapping.items():
            if parent_name in kwargs:
                child_inputs[child_name] = kwargs[parent_name]

        # Pass through any unmapped kwargs
        for key, value in kwargs.items():
            if key not in self.input_mapping:
                child_inputs[key] = value

        logger.info(
            f"Executing sub-pipeline '{self.sub_pipeline.name}' " f"({len(self.sub_pipeline.steps)} steps)",
        )

        # Run the sub-pipeline
        result = self.sub_pipeline.run(
            inputs=child_inputs,
            auto_start_ui=False,
        )

        # Map child outputs to parent outputs
        if self.output_mapping and hasattr(result, "outputs"):
            mapped_outputs = {}
            for child_name, parent_name in self.output_mapping.items():
                if child_name in result.outputs:
                    mapped_outputs[parent_name] = result.outputs[child_name]
            return mapped_outputs

        # Return the full result if no mapping
        return result

    def __call__(self, *args, **kwargs):
        """Execute the sub-pipeline step."""
        return self._execute_sub_pipeline(*args, **kwargs)


def sub_pipeline(
    pipeline: Any,
    name: str | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    input_mapping: dict[str, str] | None = None,
    output_mapping: dict[str, str] | None = None,
    **kwargs,
) -> SubPipelineStep:
    """Create a sub-pipeline step from a Pipeline object.

    Convenience function for wrapping a pipeline as a step.

    Args:
        pipeline: The Pipeline to wrap
        name: Optional step name
        inputs: Input asset names
        outputs: Output asset names
        input_mapping: Parent→child input name mapping
        output_mapping: Child→parent output name mapping
        **kwargs: Additional Step configuration

    Returns:
        SubPipelineStep instance

    Example:
        >>> from flowyml.core.subpipeline import sub_pipeline
        >>>
        >>> preprocess = Pipeline("preprocessing")
        >>> preprocess.add_step(clean).add_step(normalize)
        >>>
        >>> parent = Pipeline("training")
        >>> parent.add_step(
        ...     sub_pipeline(
        ...         preprocess,
        ...         inputs=["raw_data"],
        ...         outputs=["clean_data"],
        ...         output_mapping={"normalize": "clean_data"},
        ...     )
        ... )
    """
    return SubPipelineStep(
        sub_pipeline=pipeline,
        name=name,
        inputs=inputs,
        outputs=outputs,
        input_mapping=input_mapping,
        output_mapping=output_mapping,
        **kwargs,
    )

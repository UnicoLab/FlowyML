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
        **step_kwargs: Any,
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

        # Auto-derive outputs from output_mapping if not explicitly provided.
        # This is the key fix: the parent orchestrator's _process_step_output
        # relies on step.outputs to know which keys to propagate into the
        # parent namespace. Without this, sub-pipeline results are silently
        # stored under the step name instead of individual output keys.
        resolved_outputs = outputs
        if not resolved_outputs and self.output_mapping:
            # output_mapping maps child_name → parent_name
            resolved_outputs = list(self.output_mapping.values())
        elif not resolved_outputs:
            # No mapping specified: auto-derive from the sub-pipeline's
            # terminal steps (steps with no downstream consumers)
            resolved_outputs = self._derive_outputs_from_sub_pipeline(sub_pipeline)

        super().__init__(
            func=self._execute_sub_pipeline,
            name=step_name,
            inputs=inputs or [],
            outputs=resolved_outputs or [],
            **step_kwargs,
        )

        # Mark as sub-pipeline for orchestrator detection
        self._is_sub_pipeline = True

    @staticmethod
    def _derive_outputs_from_sub_pipeline(sub_pipeline: Any) -> list[str]:
        """Derive output names from the sub-pipeline's terminal steps.

        Terminal steps are those whose outputs are not consumed by any other
        step within the sub-pipeline. Their output names become available to
        the parent pipeline.

        Args:
            sub_pipeline: The child pipeline to inspect.

        Returns:
            List of output names from terminal steps.
        """
        try:
            steps = getattr(sub_pipeline, "steps", [])
            if not steps:
                return []

            # Collect all consumed input names
            all_inputs = set()
            for s in steps:
                all_inputs.update(getattr(s, "inputs", []))

            # Terminal outputs = step outputs not consumed by other steps
            terminal_outputs = []
            for s in steps:
                for out in getattr(s, "outputs", []):
                    if out not in all_inputs:
                        terminal_outputs.append(out)

            return terminal_outputs
        except Exception:
            return []

    def _execute_sub_pipeline(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the sub-pipeline with mapped inputs.

        The return value is always a dict keyed by the declared ``self.outputs``
        names so that the parent orchestrator's ``_process_step_output`` can
        correctly propagate each output into the shared ``step_outputs`` namespace.

        Args:
            *args: Positional arguments (parent pipeline outputs)
            **kwargs: Keyword arguments (parent pipeline outputs)

        Returns:
            Dictionary of {parent_output_name: value} for downstream steps.
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
            f"Executing sub-pipeline '{self.sub_pipeline.name}' ({len(self.sub_pipeline.steps)} steps)",
        )

        # Run the sub-pipeline
        result = self.sub_pipeline.run(
            inputs=child_inputs,
            auto_start_ui=False,
        )

        # Collect ALL child outputs from result.outputs + step_results
        all_child_outputs = dict(result.outputs) if hasattr(result, "outputs") else {}

        # Also scan individual step results for their outputs
        if hasattr(result, "step_results"):
            for step_name, step_res in result.step_results.items():
                if step_res.success and step_res.output is not None:
                    if isinstance(step_res.output, dict):
                        all_child_outputs.update(step_res.output)
                    else:
                        # Use step name as key for non-dict outputs
                        all_child_outputs[step_name] = step_res.output

        # --- Output mapping: child_name → parent_name ---
        if self.output_mapping:
            mapped_outputs = {}
            for child_name, parent_name in self.output_mapping.items():
                if child_name in all_child_outputs:
                    mapped_outputs[parent_name] = all_child_outputs[child_name]
                else:
                    logger.warning(
                        f"Sub-pipeline '{self.sub_pipeline.name}': output_mapping "
                        f"key '{child_name}' not found in child outputs. "
                        f"Available: {list(all_child_outputs.keys())}",
                    )
            return mapped_outputs

        # --- No explicit mapping: expose all child outputs directly ---
        # This lets downstream steps access sub-pipeline outputs by their
        # original names without needing an explicit mapping.
        if all_child_outputs:
            return all_child_outputs

        # Fallback: return the PipelineResult itself
        return result

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the sub-pipeline step."""
        return self._execute_sub_pipeline(*args, **kwargs)


def sub_pipeline(
    pipeline: Any,
    name: str | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    input_mapping: dict[str, str] | None = None,
    output_mapping: dict[str, str] | None = None,
    **kwargs: Any,
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

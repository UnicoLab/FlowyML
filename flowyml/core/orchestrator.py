"""Orchestrator Module - Manages the execution of pipelines."""

from typing import Any, TYPE_CHECKING

from flowyml.stacks.components import Orchestrator, ComponentType, ResourceConfig, DockerConfig

# Import existing materializer system
from flowyml.storage.materializers.base import get_materializer  # noqa

# Import lifecycle hooks
from flowyml.core.hooks import get_global_hooks

# Import observability
from flowyml.core.observability import get_metrics_collector

# Import retry policy
from flowyml.core.retry_policy import with_retry

if TYPE_CHECKING:
    from flowyml.core.pipeline import Pipeline


class LocalOrchestrator(Orchestrator):
    """Orchestrator that runs pipelines locally."""

    def __init__(self, name: str = "local"):
        super().__init__(name)

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.ORCHESTRATOR

    def validate(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "local",
        }

    def get_run_status(self, run_id: str) -> str:
        # Local runs are synchronous, so if we are asking for status, it's likely finished
        # But we don't track status persistence here (MetadataStore does that).
        # We can return "UNKNOWN" or query metadata store if we had access.
        return "COMPLETED"

    @with_retry
    def run_pipeline(
        self,
        pipeline: "Pipeline",
        run_id: str,
        resources: ResourceConfig | None = None,
        docker_config: DockerConfig | None = None,
        inputs: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs,
    ) -> Any:
        """Run the pipeline locally in the current process."""
        from flowyml.core.pipeline import PipelineResult
        from flowyml.core.step_grouping import get_execution_units, StepGroup
        from flowyml.core.executor import ExecutionResult
        import inspect

        # Initialize result
        result = PipelineResult(run_id, pipeline.name)
        result.attach_configs(resources, docker_config)

        # Run pipeline start hooks
        hooks = get_global_hooks()
        hooks.run_pipeline_start_hooks(pipeline)

        # Record metrics if collector configured
        metrics_collector = get_metrics_collector()
        if metrics_collector:
            metrics_collector.record_pipeline_start(pipeline, run_id)

        # Check executor
        if pipeline.executor is None:
            raise RuntimeError(
                "Pipeline has no executor configured. LocalOrchestrator requires a stack with an executor.",
            )

        step_outputs = inputs or {}

        # Map step names to step objects for easier lookup
        pipeline.steps_dict = {step.name: step for step in pipeline.steps}

        # Get execution units (individual steps or groups)
        execution_units = get_execution_units(pipeline.dag, pipeline.steps)

        # Execute steps/groups in order
        for unit in execution_units:
            # Check if unit is a group or individual step
            if isinstance(unit, StepGroup):
                # Execute entire group

                # Get context parameters (use first step's function as representative)
                first_step = unit.steps[0]
                context_params = pipeline.context.inject_params(first_step.func)

                # Execute the group
                group_results = pipeline.executor.execute_step_group(
                    step_group=unit,
                    inputs=step_outputs,
                    context_params=context_params,
                    cache_store=pipeline.cache_store,
                    artifact_store=pipeline.stack.artifact_store if pipeline.stack else None,
                    run_id=run_id,
                    project_name=pipeline.name,
                )

                # Process each step result
                for step_result in group_results:
                    result.add_step_result(step_result)

                    # Handle failure
                    if not step_result.success and not step_result.skipped:
                        result.finalize(success=False)
                        pipeline._save_run(result)
                        return result

                    # Store outputs for next steps/groups
                    if step_result.output is not None:
                        self._process_step_output(pipeline, step_result, step_outputs, result)

            else:
                # Execute single ungrouped step
                step = unit

                # Prepare step inputs
                step_inputs = {}

                # Get function signature to map inputs to parameters
                sig = inspect.signature(step.func)
                params = list(sig.parameters.values())

                # Filter out self/cls
                params = [p for p in params if p.name not in ("self", "cls")]

                # Track which parameters have been assigned
                assigned_params = set()

                if step.inputs:
                    for i, input_name in enumerate(step.inputs):
                        if input_name not in step_outputs:
                            continue

                        val = step_outputs[input_name]

                        # Check if input name matches a parameter
                        param_match = next((p for p in params if p.name == input_name), None)

                        if param_match:
                            step_inputs[param_match.name] = val
                            assigned_params.add(param_match.name)
                        elif i < len(params):
                            # Positional fallback
                            target_param = params[i]
                            if target_param.name not in assigned_params:
                                step_inputs[target_param.name] = val
                                assigned_params.add(target_param.name)

                # Auto-map parameters from available outputs
                for param in params:
                    if param.name in step_outputs and param.name not in step_inputs:
                        step_inputs[param.name] = step_outputs[param.name]
                        assigned_params.add(param.name)

                # Validate context parameters
                exclude_params = list(step.inputs) + list(step_inputs.keys())
                missing_params = pipeline.context.validate_for_step(step.func, exclude=exclude_params)
                if missing_params:
                    error_msg = f"Missing required parameters: {missing_params}"
                    step_result = ExecutionResult(
                        step_name=step.name,
                        success=False,
                        error=error_msg,
                    )
                    result.add_step_result(step_result)
                    result.finalize(success=False)
                    pipeline._save_run(result)
                    pipeline._save_pipeline_definition()
                    return result

                # Get context parameters for this step
                context_params = pipeline.context.inject_params(step.func)

                # Execute step
                step_result = pipeline.executor.execute_step(
                    step,
                    step_inputs,
                    context_params,
                    pipeline.cache_store,
                    artifact_store=pipeline.stack.artifact_store if pipeline.stack else None,
                    run_id=run_id,
                    project_name=pipeline.name,
                )

                result.add_step_result(step_result)

                # Handle failure
                if not step_result.success:
                    result.finalize(success=False)
                    pipeline._save_run(result)
                    pipeline._save_pipeline_definition()
                    return result

                # Store outputs for next steps/groups
                if step_result.output is not None:
                    self._process_step_output(pipeline, step_result, step_outputs, result)

        # Success! Finalize and return
        result.finalize(success=True)

        # Run pipeline end hooks
        hooks.run_pipeline_end_hooks(pipeline, result)

        # Record metrics
        if metrics_collector:
            metrics_collector.record_pipeline_end(pipeline, result)

        pipeline._save_run(result)
        pipeline._save_pipeline_definition()
        return result

    def _process_step_output(self, pipeline, step_result, step_outputs, result):
        """Helper to process step outputs and update state."""
        from pathlib import Path

        step_def = next((s for s in pipeline.steps if s.name == step_result.step_name), None)
        if not step_def:
            return

        outputs_to_process = {}

        # Normalize outputs
        if len(step_def.outputs) == 1:
            outputs_to_process[step_def.outputs[0]] = step_result.output
        elif isinstance(step_result.output, (list, tuple)) and len(step_result.output) == len(step_def.outputs):
            for name, val in zip(step_def.outputs, step_result.output, strict=False):
                outputs_to_process[name] = val
        elif isinstance(step_result.output, dict):
            for name in step_def.outputs:
                if name in step_result.output:
                    outputs_to_process[name] = step_result.output[name]
        else:
            if step_def.outputs:
                outputs_to_process[step_def.outputs[0]] = step_result.output

        # Save and update state
        for name, value in outputs_to_process.items():
            # Update in-memory outputs for immediate next steps (optimization)
            step_outputs[name] = value
            result.outputs[name] = value

            # Materialize to artifact store using existing materializer system
            if pipeline.stack and pipeline.stack.artifact_store:
                try:
                    materializer = get_materializer(value)
                    if materializer:
                        # Use artifact store's base path
                        artifact_path = (
                            Path(pipeline.stack.artifact_store.base_path) / result.run_id / step_result.step_name / name
                        )
                        materializer.save(value, artifact_path)
                except Exception as e:
                    print(f"Warning: Failed to materialize output '{name}': {e}")

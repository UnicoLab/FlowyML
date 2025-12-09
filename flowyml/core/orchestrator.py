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
    from flowyml.core.pipeline import Pipeline, PipelineResult
    from flowyml.core.executor import ExecutionResult
    from flowyml.core.step import Step


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

        # Check if we're resuming from checkpoint
        resume_from_checkpoint = getattr(pipeline, "_resume_from_checkpoint", False)
        completed_steps_from_checkpoint = getattr(pipeline, "_completed_steps_from_checkpoint", set())
        checkpoint = getattr(pipeline, "_checkpoint", None)

        # Execute steps/groups in order
        for unit in execution_units:
            # Check if unit is a group or individual step
            if isinstance(unit, StepGroup):
                # Execute entire group
                # Show group execution start
                if hasattr(pipeline, "_display") and pipeline._display:
                    for step in unit.steps:
                        pipeline._display.update_step_status(step_name=step.name, status="running")

                # Pass pipeline context so each step can get its own injected params
                group_results = pipeline.executor.execute_step_group(
                    step_group=unit,
                    inputs=step_outputs,
                    context=pipeline.context,  # Pass full context object
                    cache_store=pipeline.cache_store,
                    artifact_store=pipeline.stack.artifact_store if pipeline.stack else None,
                    run_id=run_id,
                    project_name=pipeline.name,
                )

                # Process each step result
                for step_result in group_results:
                    # Update display
                    if hasattr(pipeline, "_display") and pipeline._display:
                        pipeline._display.update_step_status(
                            step_name=step_result.step_name,
                            status="success" if step_result.success else "failed",
                            duration=step_result.duration_seconds,
                            cached=step_result.cached,
                            error=step_result.error,
                        )

                    result.add_step_result(step_result)

                    # Handle failure
                    if not step_result.success and not step_result.skipped:
                        result.finalize(success=False)
                        pipeline._save_run(result)
                        return result

                    # Store outputs for next steps/groups
                    if step_result.output is not None:
                        self._process_step_output(pipeline, step_result, step_outputs, result)

                        # Save checkpoint after successful step
                        checkpoint = getattr(pipeline, "_checkpoint", None)
                        if checkpoint and step_result.success:
                            try:
                                # Save step outputs to checkpoint
                                checkpoint.save_step_state(
                                    step_name=step_result.step_name,
                                    outputs=step_outputs,
                                    metadata={
                                        "duration": step_result.duration_seconds,
                                        "cached": step_result.cached,
                                    },
                                )
                            except Exception as e:
                                # Don't fail pipeline if checkpoint save fails
                                import warnings

                                warnings.warn(
                                    f"Failed to save checkpoint for step {step_result.step_name}: {e}",
                                    stacklevel=2,
                                )

                    # Check for control flows that need to be evaluated after this step
                    self._evaluate_control_flows(pipeline, step_result, step_outputs, result, run_id)

            else:
                # Execute single ungrouped step
                step = unit

                # Skip step if already completed in checkpoint
                if resume_from_checkpoint and step.name in completed_steps_from_checkpoint:
                    if hasattr(pipeline, "_display") and pipeline._display:
                        pipeline._display.update_step_status(
                            step_name=step.name,
                            status="success",
                            cached=True,
                        )

                    # Load step outputs from checkpoint
                    try:
                        if checkpoint:
                            step_outputs_from_checkpoint = checkpoint.load_step_state(step.name)

                            # Process checkpoint outputs
                            if isinstance(step_outputs_from_checkpoint, dict):
                                for output_name, output_value in step_outputs_from_checkpoint.items():
                                    step_outputs[output_name] = output_value
                                    result.outputs[output_name] = output_value

                            # Create a mock ExecutionResult for checkpointed step
                            step_result = ExecutionResult(
                                step_name=step.name,
                                success=True,
                                output=step_outputs_from_checkpoint,
                                duration_seconds=0.0,
                                cached=True,
                            )
                            result.add_step_result(step_result)

                            # Continue to next step
                            continue
                    except Exception as e:
                        # If checkpoint load fails, execute the step normally
                        import warnings

                        warnings.warn(
                            f"Failed to load checkpoint for step {step.name}: {e}. Executing step normally.",
                            stacklevel=2,
                        )

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

                # Update display - step starting
                if hasattr(pipeline, "_display") and pipeline._display:
                    pipeline._display.update_step_status(step_name=step.name, status="running")

                # Run step start hooks
                hooks.run_step_start_hooks(step, step_inputs)

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

                # Run step end hooks
                hooks.run_step_end_hooks(step, step_result)

                # Update display - step completed
                if hasattr(pipeline, "_display") and pipeline._display:
                    pipeline._display.update_step_status(
                        step_name=step.name,
                        status="success" if step_result.success else "failed",
                        duration=step_result.duration_seconds,
                        cached=step_result.cached,
                        error=step_result.error,
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

                    # Save checkpoint after successful step
                    checkpoint = getattr(pipeline, "_checkpoint", None)
                    if checkpoint and step_result.success:
                        try:
                            # Save step outputs to checkpoint
                            checkpoint.save_step_state(
                                step_name=step.name,
                                outputs=step_outputs,
                                metadata={
                                    "duration": step_result.duration_seconds,
                                    "cached": step_result.cached,
                                },
                            )
                        except Exception as e:
                            # Don't fail pipeline if checkpoint save fails
                            import warnings

                            warnings.warn(f"Failed to save checkpoint for step {step.name}: {e}", stacklevel=2)

                # Check for control flows that need to be evaluated after this step
                self._evaluate_control_flows(pipeline, step_result, step_outputs, result, run_id)

        # Success! Finalize and return
        result.finalize(success=True)

        # Save final checkpoint if checkpointing is enabled
        checkpoint = getattr(pipeline, "_checkpoint", None)
        if checkpoint and result.success:
            try:
                checkpoint.save_step_state(
                    "pipeline_complete",
                    result.outputs,
                    metadata={
                        "duration": result.duration_seconds,
                        "success": True,
                    },
                )
            except Exception as e:
                import warnings

                warnings.warn(f"Failed to save final checkpoint: {e}", stacklevel=2)

        # Run pipeline end hooks
        hooks.run_pipeline_end_hooks(pipeline, result)

        # Record metrics
        if metrics_collector:
            metrics_collector.record_pipeline_end(pipeline, result)

        pipeline._save_run(result)
        pipeline._save_pipeline_definition()
        return result

    def _evaluate_control_flows(
        self,
        pipeline: "Pipeline",
        step_result: "ExecutionResult",
        step_outputs: dict[str, Any],
        result: "PipelineResult",
        run_id: str,
    ) -> None:
        """Evaluate control flows after a step completes.

        Args:
            pipeline: Pipeline instance
            step_result: Result of the step that just completed
            step_outputs: Current step outputs dictionary
            result: Pipeline result object
            run_id: Run identifier
        """
        from flowyml.core.conditional import If

        # Create a context object for condition evaluation
        class ExecutionContext:
            """Context object for conditional evaluation.

            Provides access to step outputs via ctx.steps['step_name'].outputs['output_name']
            """

            def __init__(self, result: "PipelineResult", pipeline: "Pipeline"):
                self.result = result
                self.pipeline = pipeline
                self._steps_cache = None

            @property
            def steps(self):
                """Lazy-load steps dictionary with outputs."""
                if self._steps_cache is None:
                    self._steps_cache = {}
                    # Build steps dictionary with outputs
                    for step_name, step_res in self.result.step_results.items():
                        if step_res.success and step_res.output is not None:
                            step_def = next((s for s in self.pipeline.steps if s.name == step_name), None)
                            if step_def:
                                # Create step outputs dictionary
                                step_outputs = {}
                                if len(step_def.outputs) == 1:
                                    step_outputs[step_def.outputs[0]] = step_res.output
                                elif isinstance(step_res.output, dict):
                                    step_outputs = step_res.output
                                elif step_def.outputs:
                                    # Try to map tuple/list outputs
                                    if isinstance(step_res.output, (list, tuple)) and len(step_res.output) == len(
                                        step_def.outputs,
                                    ):
                                        for name, val in zip(step_def.outputs, step_res.output, strict=False):
                                            step_outputs[name] = val
                                    else:
                                        step_outputs[step_def.outputs[0]] = step_res.output

                                # Create step object with outputs attribute that supports Asset objects
                                class StepContext:
                                    def __init__(self, outputs):
                                        # Wrap outputs to support Asset object access
                                        self._raw_outputs = outputs
                                        self.outputs = self._wrap_outputs(outputs)

                                    def _wrap_outputs(self, outputs):
                                        """Wrap outputs to support Asset object property access."""
                                        wrapped = {}
                                        for key, value in outputs.items():
                                            wrapped[key] = self._wrap_asset(value)
                                        return wrapped

                                    def _wrap_asset(self, value):
                                        """Wrap Asset objects to expose their properties."""
                                        # Check if it's an Asset object
                                        from flowyml.assets.base import Asset
                                        from flowyml.assets.metrics import Metrics
                                        from flowyml.assets.featureset import FeatureSet

                                        if isinstance(value, Asset):
                                            # Create a wrapper that exposes Asset properties
                                            class AssetWrapper:
                                                def __init__(self, asset):
                                                    self._asset = asset
                                                    # Expose the asset itself
                                                    self._self = asset

                                                def __getattr__(self, name):  # noqa: B023
                                                    # Try to get from asset first (handles all Asset properties)
                                                    try:
                                                        if hasattr(self._asset, name):  # noqa: B023
                                                            attr = getattr(self._asset, name)  # noqa: B023
                                                            # If it's a property/method, return it
                                                            # If it's callable but we want the value, call it
                                                            if callable(attr) and not isinstance(attr, type):
                                                                # It's a method, not a property - return as-is
                                                                return attr
                                                            return attr
                                                    except Exception as e:
                                                        # If accessing the attribute fails, log and continue to fallback logic
                                                        # This can happen if a property raises an exception
                                                        import warnings

                                                        warnings.warn(
                                                            f"Failed to access attribute '{name}' on {type(self._asset).__name__}: {e}",  # noqa: B023
                                                            stacklevel=3,
                                                        )
                                                        pass

                                                    # For Metrics, map .metrics to .data or .get_all_metrics()
                                                    if isinstance(self._asset, Metrics):
                                                        if name == "metrics":  # noqa: B023
                                                            return (
                                                                self._asset.get_all_metrics() or self._asset.data or {}  # noqa: B023
                                                            )

                                                    # For all Assets, expose .data
                                                    if name == "data":  # noqa: B023
                                                        return self._asset.data

                                                    # Expose properties dict
                                                    if name == "properties":  # noqa: B023
                                                        return self._asset.properties

                                                    # Expose tags
                                                    if name == "tags":  # noqa: B023
                                                        return self._asset.tags

                                                    # Expose metadata (as alias for properties + tags)
                                                    if name == "metadata":  # noqa: B023
                                                        # Create a dict that merges properties and tags
                                                        # Tags take precedence if there's a conflict
                                                        # Start with properties, then update with tags (tags override)
                                                        # Use dict() constructor to ensure it's a proper dict with .get() method
                                                        metadata_dict = (
                                                            dict(self._asset.properties)
                                                            if self._asset.properties
                                                            else {}
                                                        )
                                                        if self._asset.tags:
                                                            metadata_dict.update(self._asset.tags)
                                                        return metadata_dict

                                                    raise AttributeError(  # noqa: B023
                                                        f"'{type(self).__name__}' object has no attribute '{name}'",  # noqa: B023
                                                    )

                                                def __getitem__(self, key):
                                                    """Allow dict-like access for Metrics.data and Asset.data."""
                                                    # For Metrics, access via get_all_metrics()
                                                    if isinstance(self._asset, Metrics):
                                                        metrics = (
                                                            self._asset.get_all_metrics() or self._asset.data or {}
                                                        )
                                                        if isinstance(metrics, dict):
                                                            return metrics[key]  # noqa: B023

                                                    # For all Assets, allow dict access to .data if it's a dict
                                                    if isinstance(self._asset.data, dict):
                                                        return self._asset.data[key]

                                                    # For FeatureSet, allow access to statistics
                                                    if isinstance(self._asset, FeatureSet):
                                                        if key in self._asset.statistics:
                                                            return self._asset.statistics[key]

                                                    raise KeyError(f"'{key}' not found in {type(self._asset).__name__}")

                                                def __contains__(self, key):
                                                    """Support 'in' operator."""
                                                    # For Metrics, check in metrics dict
                                                    if isinstance(self._asset, Metrics):
                                                        metrics = (
                                                            self._asset.get_all_metrics() or self._asset.data or {}
                                                        )
                                                        if isinstance(metrics, dict):
                                                            return key in metrics

                                                    # For all Assets, check in .data if it's a dict
                                                    if isinstance(self._asset.data, dict):
                                                        return key in self._asset.data

                                                    # For FeatureSet, check in statistics
                                                    if isinstance(self._asset, FeatureSet):
                                                        return key in self._asset.statistics

                                                    return False

                                                def __repr__(self):
                                                    return f"<AssetWrapper({type(self._asset).__name__})>"

                                            return AssetWrapper(value)
                                        # For dict values, return as-is but allow attribute access
                                        elif isinstance(value, dict):

                                            class DictWrapper(dict):
                                                """Dict wrapper that allows attribute access."""

                                                def __getattr__(self, name):  # noqa: B023
                                                    if name in self:  # noqa: B023
                                                        return self[name]  # noqa: B023
                                                    raise AttributeError(  # noqa: B023
                                                        f"'{type(self).__name__}' object has no attribute '{name}'",  # noqa: B023
                                                    )

                                            return DictWrapper(value)
                                        # For other types, return as-is
                                        return value

                                self._steps_cache[step_name] = StepContext(step_outputs)
                return self._steps_cache

        context = ExecutionContext(result, pipeline)

        # Evaluate each control flow
        for control_flow in pipeline.control_flows:
            if isinstance(control_flow, If):
                try:
                    selected_step = control_flow.evaluate(context)
                except Exception as e:
                    # If condition evaluation fails, log the error with full traceback for debugging
                    import warnings
                    import traceback

                    warnings.warn(
                        f"Failed to evaluate control flow condition: {e}\n{traceback.format_exc()}",
                        stacklevel=2,
                    )
                    # If condition evaluation fails, try to execute else_step as fallback
                    # This ensures we don't silently skip execution
                    selected_step = control_flow.else_step

                # Execute selected_step if it exists (could be then_step, else_step, or None)
                if selected_step:
                    from flowyml.core.step import Step

                    # Check if selected_step is already a Step object or a function
                    if isinstance(selected_step, Step):
                        # Already a Step object, use it directly
                        step_obj = selected_step
                    else:
                        # It's a function, try to find existing Step or create one
                        step_obj = next((s for s in pipeline.steps if s.func == selected_step), None)

                        # If step not found in pipeline.steps, it's a conditional step - create Step object on the fly
                        if step_obj is None:
                            # Get function name safely
                            func_name = getattr(selected_step, "__name__", "conditional_step")
                            # Create a Step object for the conditional step function
                            step_obj = Step(
                                func=selected_step,
                                name=func_name,
                                inputs=[],  # Conditional steps may not have explicit inputs
                                outputs=[],  # Conditional steps may not have explicit outputs
                            )

                    if step_obj.name not in result.step_results:
                        # Execute the selected step
                        # The check above prevents re-execution of the same step
                        self._execute_conditional_step(
                            pipeline,
                            step_obj,
                            step_outputs,
                            result,
                            run_id,
                        )
                        # Note: Control flows will be re-evaluated after conditional step completes

    def _execute_conditional_step(
        self,
        pipeline: "Pipeline",
        step: "Step",
        step_outputs: dict[str, Any],
        result: "PipelineResult",
        run_id: str,
    ) -> None:
        """Execute a step that was selected by conditional logic.

        Args:
            pipeline: Pipeline instance
            step: Step to execute
            step_outputs: Current step outputs
            result: Pipeline result object
            run_id: Run identifier
        """
        # Prepare step inputs (similar to regular step execution)
        import inspect

        step_inputs = {}
        sig = inspect.signature(step.func)
        params = [p for p in sig.parameters.values() if p.name not in ("self", "cls")]

        for param in params:
            if param.name in step_outputs:
                step_inputs[param.name] = step_outputs[param.name]

        # Get context parameters
        context_params = pipeline.context.inject_params(step.func)

        # Update display
        if hasattr(pipeline, "_display") and pipeline._display:
            pipeline._display.update_step_status(step_name=step.name, status="running")

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

        # Update display
        if hasattr(pipeline, "_display") and pipeline._display:
            pipeline._display.update_step_status(
                step_name=step.name,
                status="success" if step_result.success else "failed",
                duration=step_result.duration_seconds,
                cached=step_result.cached,
                error=step_result.error,
            )

        result.add_step_result(step_result)

        # Handle failure
        if not step_result.success:
            result.finalize(success=False)
            return

        # Process outputs
        if step_result.output is not None:
            self._process_step_output(pipeline, step_result, step_outputs, result)

            # Save checkpoint after successful conditional step
            checkpoint = getattr(pipeline, "_checkpoint", None)
            if checkpoint and step_result.success:
                try:
                    checkpoint.save_step_state(
                        step_name=step.name,
                        outputs=step_outputs,
                        metadata={
                            "duration": step_result.duration_seconds,
                            "cached": step_result.cached,
                        },
                    )
                except Exception as e:
                    import warnings

                    warnings.warn(f"Failed to save checkpoint for conditional step {step.name}: {e}", stacklevel=2)

        # Check for control flows that need to be evaluated after conditional step
        self._evaluate_control_flows(pipeline, step_result, step_outputs, result, run_id)

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

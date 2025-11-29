"""Executor Module - Execute pipeline steps with retry and error handling."""

import time
import traceback
import contextlib
from typing import Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExecutionResult:
    """Result of step execution."""

    step_name: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_seconds: float = 0.0
    cached: bool = False
    skipped: bool = False
    artifact_uri: str | None = None
    retries: int = 0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class Executor:
    """Base executor for running pipeline steps."""

    def execute_step(
        self,
        step,
        inputs: dict[str, Any],
        context_params: dict[str, Any],
        cache_store: Any | None = None,
    ) -> ExecutionResult:
        """Execute a single step.

        Args:
            step: Step to execute
            inputs: Input data for the step
            context_params: Parameters from context
            cache_store: Cache store for caching

        Returns:
            ExecutionResult with output or error
        """
        raise NotImplementedError

    def execute_step_group(
        self,
        step_group,  # StepGroup
        inputs: dict[str, Any],
        context_params: dict[str, Any],
        cache_store: Any | None = None,
        artifact_store: Any | None = None,
        run_id: str | None = None,
        project_name: str = "default",
    ) -> list[ExecutionResult]:
        """Execute a group of steps together.

        Args:
            step_group: StepGroup to execute
            inputs: Input data available to the group
            context_params: Parameters from context
            cache_store: Cache store for caching
            artifact_store: Artifact store for materialization
            run_id: Run identifier
            project_name: Project name

        Returns:
            List of ExecutionResult (one per step)
        """
        raise NotImplementedError


class LocalExecutor(Executor):
    """Local executor - runs steps in the current process."""

    def execute_step(
        self,
        step,
        inputs: dict[str, Any],
        context_params: dict[str, Any],
        cache_store: Any | None = None,
        artifact_store: Any | None = None,
        run_id: str | None = None,
        project_name: str = "default",
    ) -> ExecutionResult:
        """Execute step locally with retry, caching, and materialization."""
        start_time = time.time()
        retries = 0

        # Check condition
        if step.condition:
            try:
                # We pass inputs and context params to condition if it accepts them
                # For simplicity, let's try to inspect the condition function
                # or just pass what we can.
                # A simple approach: pass nothing if it takes no args, or kwargs if it does.
                # But inspect is safer.
                import inspect

                sig = inspect.signature(step.condition)
                kwargs = {**inputs, **context_params}

                # Filter kwargs to only what condition accepts
                cond_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

                should_run = step.condition(**cond_kwargs)

                if not should_run:
                    duration = time.time() - start_time
                    return ExecutionResult(
                        step_name=step.name,
                        success=True,
                        output=None,  # Skipped steps produce None
                        duration_seconds=duration,
                        skipped=True,
                    )
            except Exception as e:
                # If condition check fails, treat as step failure
                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=False,
                    error=f"Condition check failed: {str(e)}",
                    duration_seconds=duration,
                )

        # Check cache
        if cache_store and step.cache:
            cache_key = step.get_cache_key(inputs)
            cached_result = cache_store.get(cache_key)

            if cached_result is not None:
                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=True,
                    output=cached_result,
                    duration_seconds=duration,
                    cached=True,
                )

        # Execute with retry
        max_retries = step.retry
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Prepare arguments
                kwargs = {**inputs, **context_params}

                # Execute step
                result = step.func(**kwargs)

                # Materialize output if artifact store is available
                artifact_uri = None
                if artifact_store and result is not None and run_id:
                    with contextlib.suppress(Exception):
                        artifact_uri = artifact_store.materialize(
                            obj=result,
                            name="output",  # Default name for single output
                            run_id=run_id,
                            step_name=step.name,
                            project_name=project_name,
                        )

                # Cache result
                if cache_store and step.cache:
                    cache_key = step.get_cache_key(inputs)
                    cache_store.set_value(
                        cache_key,
                        result,
                        step.name,
                        step.get_code_hash(),
                    )

                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=True,
                    output=result,
                    duration_seconds=duration,
                    retries=retries,
                    artifact_uri=artifact_uri,
                )

            except Exception as e:
                last_error = str(e)
                retries += 1

                if attempt < max_retries:
                    # Wait before retry (exponential backoff)
                    wait_time = 2**attempt
                    time.sleep(wait_time)
                    continue

                # All retries exhausted
                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=False,
                    error=f"{last_error}\n{traceback.format_exc()}",
                    duration_seconds=duration,
                    retries=retries,
                )

        # Should never reach here
        duration = time.time() - start_time
        return ExecutionResult(
            step_name=step.name,
            success=False,
            error=last_error,
            duration_seconds=duration,
            retries=retries,
        )

    def execute_step_group(
        self,
        step_group,  # StepGroup from step_grouping module
        inputs: dict[str, Any],
        context_params: dict[str, Any],
        cache_store: Any | None = None,
        artifact_store: Any | None = None,
        run_id: str | None = None,
        project_name: str = "default",
    ) -> list[ExecutionResult]:
        """Execute a group of steps together in the same environment.

        For local execution, steps execute sequentially but share the same process.

        Args:
            step_group: StepGroup containing steps to execute
            inputs: Input data available to the group
            context_params: Parameters from context
            cache_store: Cache store for caching
            artifact_store: Artifact store for materialization
            run_id: Run identifier
            project_name: Project name

        Returns:
            List of ExecutionResult (one per step in execution order)
        """
        results: list[ExecutionResult] = []
        step_outputs = dict(inputs)  # Copy initial inputs

        # Execute steps in their defined order
        for step_name in step_group.execution_order:
            # Find the step object
            step = next(s for s in step_group.steps if s.name == step_name)

            # Prepare inputs for this step
            step_inputs = {}
            for input_name in step.inputs:
                if input_name in step_outputs:
                    step_inputs[input_name] = step_outputs[input_name]

            # Execute this step
            result = self.execute_step(
                step=step,
                inputs=step_inputs,
                context_params=context_params,
                cache_store=cache_store,
                artifact_store=artifact_store,
                run_id=run_id,
                project_name=project_name,
            )

            results.append(result)

            # If step failed, stop group execution
            if not result.success:
                # Mark remaining steps as skipped
                current_index = step_group.execution_order.index(step_name)
                remaining_steps = step_group.execution_order[current_index + 1 :]

                for remaining_name in remaining_steps:
                    skip_result = ExecutionResult(
                        step_name=remaining_name,
                        success=True,  # Set to True since skipped steps technically don't fail
                        error="Skipped due to earlier failure in group",
                        skipped=True,
                    )
                    results.append(skip_result)
                break

            # Store outputs for next steps in group
            if result.output is not None:
                if len(step.outputs) == 1:
                    step_outputs[step.outputs[0]] = result.output
                elif isinstance(result.output, (list, tuple)) and len(result.output) == len(step.outputs):
                    for name, val in zip(step.outputs, result.output, strict=False):
                        step_outputs[name] = val
                elif isinstance(result.output, dict):
                    for name in step.outputs:
                        if name in result.output:
                            step_outputs[name] = result.output[name]
                else:
                    if step.outputs:
                        step_outputs[step.outputs[0]] = result.output

        return results


class DistributedExecutor(Executor):
    """Distributed executor - runs steps on remote workers.
    (Placeholder for future implementation).
    """

    def __init__(self, worker_pool_size: int = 4):
        self.worker_pool_size = worker_pool_size

    def execute_step(
        self,
        step,
        inputs: dict[str, Any],
        context_params: dict[str, Any],
        cache_store: Any | None = None,
    ) -> ExecutionResult:
        """Execute step in distributed manner."""
        # Placeholder - would use Ray, Dask, or similar
        # For now, fall back to local execution
        local_executor = LocalExecutor()
        return local_executor.execute_step(step, inputs, context_params, cache_store)

    def execute_step_group(
        self,
        step_group,  # StepGroup
        inputs: dict[str, Any],
        context_params: dict[str, Any],
        cache_store: Any | None = None,
        artifact_store: Any | None = None,
        run_id: str | None = None,
        project_name: str = "default",
    ) -> list[ExecutionResult]:
        """Execute step group in distributed manner."""
        # Placeholder - in real implementation, would send entire group to remote worker
        # For now, fall back to local execution
        local_executor = LocalExecutor()
        return local_executor.execute_step_group(
            step_group,
            inputs,
            context_params,
            cache_store,
            artifact_store,
            run_id,
            project_name,
        )

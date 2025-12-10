"""Executor Module - Execute pipeline steps with retry and error handling."""

import time
import traceback
import contextlib
from typing import Any
from dataclasses import dataclass
from datetime import datetime

import threading
import ctypes
import requests
import os
import inspect


class StopExecutionError(Exception):
    """Exception raised when execution is stopped externally."""

    pass


# Alias for backwards compatibility
StopExecution = StopExecutionError


def _async_raise(tid, exctype):
    """Raises an exception in the threads with id tid"""
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    if res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class LogCapture:
    """Context manager to capture stdout/stderr for streaming to the server."""

    def __init__(self):
        self._buffer = []
        self._lock = threading.Lock()

    def write(self, text):
        if text.strip():
            with self._lock:
                self._buffer.append(text)

    def flush(self):
        pass

    def get_and_clear(self) -> list[str]:
        with self._lock:
            lines = self._buffer[:]
            self._buffer.clear()
            return lines


class MonitorThread(threading.Thread):
    """Background thread that sends heartbeats and flushes logs to the server."""

    def __init__(
        self,
        run_id: str,
        step_name: str,
        target_tid: int,
        log_capture: LogCapture | None = None,
        interval: int = 5,
    ):
        super().__init__()
        self.run_id = run_id
        self.step_name = step_name
        self.target_tid = target_tid
        self.log_capture = log_capture
        self.interval = interval
        self._stop_event = threading.Event()
        # Get UI server URL from configuration (supports env vars, config, centralized deployments)
        try:
            from flowyml.ui.utils import get_ui_server_url

            self.api_url = get_ui_server_url()
        except Exception:
            # Fallback to environment variable or default
            self.api_url = os.getenv("FLOWYML_SERVER_URL", "http://localhost:8080")

    def stop(self, error: str | None = None):
        """Stop the monitor thread.

        Args:
            error: Optional error message to send as final log entry
        """
        self._final_error = error
        self._stop_event.set()

    def _flush_logs(self, level: str = "INFO"):
        """Send captured logs to the server."""
        if not self.log_capture:
            return

        lines = self.log_capture.get_and_clear()
        if not lines:
            return

        content = "".join(lines)
        with contextlib.suppress(Exception):
            requests.post(
                f"{self.api_url}/api/runs/{self.run_id}/steps/{self.step_name}/logs",
                json={
                    "content": content,
                    "level": level,
                    "timestamp": datetime.now().isoformat(),
                },
                timeout=2,
            )

    def _send_error(self, error: str):
        """Send error message to the server."""
        with contextlib.suppress(Exception):
            requests.post(
                f"{self.api_url}/api/runs/{self.run_id}/steps/{self.step_name}/logs",
                json={
                    "content": f"ERROR: {error}",
                    "level": "ERROR",
                    "timestamp": datetime.now().isoformat(),
                },
                timeout=2,
            )

    def run(self):
        while not self._stop_event.is_set():
            try:
                # Send heartbeat
                response = requests.post(
                    f"{self.api_url}/api/runs/{self.run_id}/steps/{self.step_name}/heartbeat",
                    json={"step_name": self.step_name, "status": "running"},
                    timeout=2,
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("action") == "stop":
                        print(f"Received stop signal for step {self.step_name}")
                        _async_raise(self.target_tid, StopExecution)
                        break
            except Exception:
                pass  # Ignore heartbeat failures

            # Flush logs
            self._flush_logs()

            self._stop_event.wait(self.interval)

        # Final log flush
        self._flush_logs()

        # Send error if there was one
        if hasattr(self, "_final_error") and self._final_error:
            self._send_error(self._final_error)


# Keep HeartbeatThread as an alias for backwards compatibility
HeartbeatThread = MonitorThread


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
        context: Any | None = None,  # Context object for per-step injection
        context_params: dict[str, Any] | None = None,  # Deprecated: use context instead
        cache_store: Any | None = None,
        artifact_store: Any | None = None,
        run_id: str | None = None,
        project_name: str = "default",
    ) -> list[ExecutionResult]:
        """Execute a group of steps together.

        Args:
            step_group: StepGroup to execute
            inputs: Input data available to the group
            context: Context object for per-step parameter injection (preferred)
            context_params: Parameters from context (deprecated, use context instead)
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
                monitor_thread = None
                log_capture = None
                original_stdout = None
                original_stderr = None
                try:
                    # Start monitoring thread with log capture if run_id is present
                    if run_id:
                        import sys

                        log_capture = LogCapture()
                        original_stdout = sys.stdout
                        original_stderr = sys.stderr
                        sys.stdout = log_capture
                        sys.stderr = log_capture

                        monitor_thread = MonitorThread(
                            run_id=run_id,
                            step_name=step.name,
                            target_tid=threading.get_ident(),
                            log_capture=log_capture,
                        )
                        monitor_thread.start()

                    result = step.func(**kwargs)
                except StopExecution:
                    duration = time.time() - start_time
                    return ExecutionResult(
                        step_name=step.name,
                        success=False,
                        error="Execution stopped by user",
                        duration_seconds=duration,
                        retries=retries,
                    )
                finally:
                    # Restore stdout/stderr
                    if original_stdout:
                        import sys

                        sys.stdout = original_stdout
                    if original_stderr:
                        import sys

                        sys.stderr = original_stderr

                    # Stop monitor thread (only if not already stopped in exception handler)
                    if monitor_thread and not monitor_thread._stop_event.is_set():
                        monitor_thread.stop()
                        monitor_thread.join()

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
                error_traceback = traceback.format_exc()
                retries += 1

                if attempt < max_retries:
                    # Wait before retry (exponential backoff)
                    wait_time = 2**attempt
                    time.sleep(wait_time)
                    continue

                # All retries exhausted - send error to logs
                if monitor_thread:
                    monitor_thread.stop(error=f"{last_error}\n{error_traceback}")
                    monitor_thread.join()
                    monitor_thread = None  # Prevent double-stop in finally

                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=False,
                    error=f"{last_error}\n{error_traceback}",
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
        context: Any | None = None,  # Context object for per-step injection
        context_params: dict[str, Any] | None = None,  # Deprecated: use context instead
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
            context: Context object for per-step parameter injection (preferred)
            context_params: Parameters from context (deprecated, use context instead)
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

            # Prepare inputs for this step - map input names to function parameters
            step_inputs = {}

            # Get function signature to properly map inputs to parameters
            sig = inspect.signature(step.func)
            params = list(sig.parameters.values())
            # Filter out self/cls
            params = [p for p in params if p.name not in ("self", "cls")]
            assigned_params = set()

            if step.inputs:
                for i, input_name in enumerate(step.inputs):
                    if input_name not in step_outputs:
                        continue

                    val = step_outputs[input_name]

                    # Check if input name matches a parameter directly
                    param_match = next((p for p in params if p.name == input_name), None)

                    if param_match:
                        step_inputs[param_match.name] = val
                        assigned_params.add(param_match.name)
                    elif i < len(params):
                        # Positional fallback - use the parameter at the same position
                        target_param = params[i]
                        if target_param.name not in assigned_params:
                            step_inputs[target_param.name] = val
                            assigned_params.add(target_param.name)

            # Auto-map parameters from available outputs by name
            for param in params:
                if param.name in step_outputs and param.name not in step_inputs:
                    step_inputs[param.name] = step_outputs[param.name]
                    assigned_params.add(param.name)

            # Inject context parameters for this specific step
            if context is not None:
                # Use context object to inject params per step
                step_context_params = context.inject_params(step.func)
            elif context_params is not None:
                # Fallback to provided context_params (backward compatibility)
                step_context_params = context_params
            else:
                step_context_params = {}

            # Execute this step
            result = self.execute_step(
                step=step,
                inputs=step_inputs,
                context_params=step_context_params,
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

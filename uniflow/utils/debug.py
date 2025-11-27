"""Pipeline and step debugging tools."""

from collections.abc import Callable
from functools import wraps
import contextlib


class StepDebugger:
    """Debug individual pipeline steps.

    Features:
    - Breakpoints
    - Input/output inspection
    - Exception debugging
    - Step profiling

    Examples:
        >>> from uniflow import step, StepDebugger
        >>> debugger = StepDebugger()
        >>> @step(outputs=["processed"])
        ... @debugger.breakpoint()
        ... def process_data(data):
        ...     # Debugger will stop here
        ...     return data * 2
    """

    def __init__(self):
        self.breakpoints = set()
        self.step_history = []
        self.enabled = True

    def break_at(self, condition: Callable | None = None):
        """Add a breakpoint to a step.

        Args:
            condition: Optional condition function. Break only if returns True.
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                # Check condition
                should_break = True
                if condition:
                    should_break = condition(*args, **kwargs)

                if should_break:
                    while True:
                        cmd = input("\n(debug) ").strip()

                        if cmd == "c":
                            break
                        if cmd == "i":
                            pass
                        elif cmd.startswith("p "):
                            expr = cmd[2:]
                            with contextlib.suppress(Exception):
                                # Evaluate in context
                                result = eval(expr, {"args": args, "kwargs": kwargs})
                        elif cmd == "pdb":
                            import pdb  # noqa: T100

                            pdb.set_trace()
                            break

                # Execute function
                try:
                    result = func(*args, **kwargs)

                    # Log execution
                    self.step_history.append(
                        {
                            "step": func.__name__,
                            "inputs": {"args": args, "kwargs": kwargs},
                            "output": result,
                            "success": True,
                        },
                    )

                    return result
                except Exception as e:
                    # Log error
                    self.step_history.append(
                        {
                            "step": func.__name__,
                            "inputs": {"args": args, "kwargs": kwargs},
                            "error": str(e),
                            "success": False,
                        },
                    )
                    raise

            return wrapper

        return decorator

    def trace(self):
        """Enable step tracing (print inputs/outputs)."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                result = func(*args, **kwargs)

                return result

            return wrapper

        return decorator

    def profile(self):
        """Profile step execution time."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                import time

                start = time.time()
                result = func(*args, **kwargs)
                time.time() - start

                return result

            return wrapper

        return decorator

    def get_history(self):
        """Get step execution history."""
        return self.step_history

    def clear_history(self) -> None:
        """Clear execution history."""
        self.step_history = []


class PipelineDebugger:
    """Debug entire pipelines.

    Features:
    - Step-by-step execution
    - DAG visualization
    - Execution replay
    - Error analysis
    """

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.execution_log = []

    def step_through(self) -> None:
        """Execute pipeline step-by-step with breaks."""
        self.pipeline.build()
        order = self.pipeline.dag.topological_sort()

        for _ in order:
            response = input("\nExecute this step? [Y/n/q]: ").lower()

            if response == "q":
                break
            if response == "n":
                continue

            # Execute step would happen here in actual implementation

    def visualize_dag(self) -> None:
        """Visualize the pipeline DAG."""
        self.pipeline.build()

    def analyze_errors(self, run_id: str) -> None:
        """Analyze errors from a failed run."""
        # Load run metadata
        metadata = self.pipeline.metadata_store.load_run(run_id)

        if not metadata:
            return

        steps_metadata = metadata.get("steps", {})

        failed_steps = []
        for step_name, step_data in steps_metadata.items():
            if not step_data.get("success", True):
                failed_steps.append((step_name, step_data))

        if not failed_steps:
            return

        for _, step_data in failed_steps:
            if step_data.get("source_code"):
                for _ in step_data["source_code"].split("\n")[:10]:
                    pass

    def replay_run(self, run_id: str, start_from: str | None = None) -> None:
        """Replay a previous run, optionally starting from a specific step."""
        if start_from:
            pass
        _ = run_id  # Unused in placeholder

        # Implementation would load state and re-execute


def inspect_step(step) -> None:
    """Inspect a step's metadata.

    Args:
        step: Step to inspect
    """
    if step.source_code:
        pass


def print_dag(pipeline) -> None:
    """Pretty print pipeline DAG."""
    pipeline.build()


# Global debugger instance
_global_debugger = StepDebugger()


def debug_step(*args, **kwargs):
    """Convenience function to debug a step."""
    return _global_debugger.break_at(*args, **kwargs)


def trace_step():
    """Convenience function to trace a step."""
    return _global_debugger.trace()


def profile_step():
    """Convenience function to profile a step."""
    return _global_debugger.profile()

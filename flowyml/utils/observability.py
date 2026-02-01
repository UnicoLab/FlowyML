from functools import wraps
from typing import Any
from collections.abc import Callable
from opentelemetry import trace

tracer = trace.get_tracer("flowyml")


def trace_execution(operation_name: str | None = None) -> Callable:
    """Decorator to trace function execution with OpenTelemetry."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_name = operation_name or func.__name__
            with tracer.start_as_current_span(span_name) as span:
                # Add basic attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    raise e

        return wrapper

    return decorator

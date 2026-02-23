"""🌐 Generic GenAI Integration — Framework-Agnostic Observability.

Works with ANY GenAI framework (CrewAI, AutoGen, Haystack, DSPy, custom)
without requiring any framework-specific dependencies.

Usage:
    # Decorator — Wrap any function
    from flowyml.integrations.generic import observe

    @observe(name="my_agent", project="demo")
    def run_agent(query: str, flowyml_session=None):
        # Use flowyml_session to log spans manually
        span = flowyml_session.start_span("llm", "my_model_call")
        result = call_my_model(query)
        span.set_tokens(prompt_tokens=50, completion_tokens=100, model="gpt-4o")
        flowyml_session.end_span(span, outputs={"result": result})
        return result

    # Context Manager — Wrap a block of code
    from flowyml.integrations.generic import trace

    with trace("my_pipeline", project="demo") as tracer:
        span = tracer.start_span("llm", "step1")
        result = do_work()
        tracer.end_span(span, outputs={"result": result})

    # Manual logging — Fire-and-forget
    from flowyml.integrations.generic import log_llm_call, log_tool_call

    log_llm_call(
        model="gpt-4o", prompt="Hello", response="Hi!",
        prompt_tokens=5, completion_tokens=2,
    )
"""

from flowyml.integrations.base import (
    BaseTracer,
    GenAISession,
    SessionTracer,
    TraceSession,
    TraceSpan,
    Turn,
    estimate_cost,
    log_embedding_call,
    log_llm_call,
    log_tool_call,
    observe,
    safe_serialize,
    session_trace,
    trace,
)
from flowyml.integrations.eval_bridge import SessionEvaluator
from flowyml.integrations.streaming import SessionEventStream

__all__ = [
    # Core classes
    "BaseTracer",
    "TraceSession",
    "TraceSpan",
    # Session-level (GenAI-first)
    "GenAISession",
    "Turn",
    "SessionTracer",
    "session_trace",
    "SessionEvaluator",
    "SessionEventStream",
    # High-level API
    "trace",
    "observe",
    # Manual logging
    "log_llm_call",
    "log_tool_call",
    "log_embedding_call",
    # Utilities
    "safe_serialize",
    "estimate_cost",
    # Convenience: span() shorthand
    "span",
]


def span(
    name: str,
    event_type: str = "custom",
    *,
    inputs: dict | None = None,
    metadata: dict | None = None,
    tracer: BaseTracer | None = None,
    project: str | None = None,
) -> "_SpanContext":
    """Create a span as a context manager.

    Example::

        with span("my_step", "llm") as s:
            result = do_work()
            s.set_tokens(prompt_tokens=10, completion_tokens=20, model="gpt-4o")
            s.outputs = {"result": result}

    Or within a trace() context::

        with trace("pipeline") as tracer:
            with span("step1", "llm", tracer=tracer) as s:
                result = call_llm()
                s.set_tokens(prompt_tokens=10, completion_tokens=20)
    """
    return _SpanContext(
        name=name,
        event_type=event_type,
        inputs=inputs,
        metadata=metadata,
        tracer=tracer,
        project=project,
    )


class _SpanContext:
    """Context manager for a single span."""

    def __init__(
        self,
        name: str,
        event_type: str,
        inputs: dict | None = None,
        metadata: dict | None = None,
        tracer: BaseTracer | None = None,
        project: str | None = None,
    ):
        self._name = name
        self._event_type = event_type
        self._inputs = inputs
        self._metadata = metadata
        self._ext_tracer = tracer
        self._project = project
        self._tracer: BaseTracer | None = None
        self._span: TraceSpan | None = None
        self._owns_tracer = False

    def __enter__(self) -> TraceSpan:
        if self._ext_tracer:
            self._tracer = self._ext_tracer
        else:
            self._tracer = BaseTracer(
                name=self._name,
                project=self._project,
                framework="generic",
            )
            self._owns_tracer = True

        self._span = self._tracer.start_span(
            self._event_type,
            self._name,
            inputs=self._inputs or {},
            metadata=self._metadata or {},
        )
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._span and self._tracer:
            error = str(exc_val) if exc_val else None
            self._tracer.end_span(self._span, error=error)

        if self._owns_tracer and self._tracer:
            self._tracer.finalize()

        return False  # Don't suppress exceptions

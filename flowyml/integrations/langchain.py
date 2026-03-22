"""🔗 LangChain Integration — FlowyML Observability for LangChain.

Provides observability for LangChain chains, runnables, and agents
that are NOT using LangGraph. Uses the same callback handler as the
LangGraph integration.

Usage:
    # Context Manager
    with trace_chain("my_chain", project="demo") as session:
        result = chain.invoke(input, config=session.config)

    # Decorator
    @observe_chain(name="summarizer", project="demo")
    def summarize(text: str, flowyml_session=None):
        return chain.invoke(text, config=flowyml_session.config)

    # Direct handler
    handler = FlowyMLCallbackHandler(session_name="my_chain")
    result = chain.invoke(input, config={"callbacks": [handler]})
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from flowyml.integrations.langgraph import FlowyMLCallbackHandler

__all__ = [
    "FlowyMLCallbackHandler",
    "trace_chain",
    "observe_chain",
    "instrument_chain",
]


# ─────────────────────────────────────────────────────
# trace_chain() — Context manager for LangChain
# ─────────────────────────────────────────────────────
@contextmanager
def trace_chain(
    name: str = "langchain_chain",
    project: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Context manager for tracing LangChain chains and runnables.

    Yields a session wrapper with a ``.config`` property for injection.

    Example::

        with trace_chain("qa_chain", project="support") as session:
            result = chain.invoke(
                {"question": "What is AI?"},
                config=session.config,
            )
        print(f"Tokens used: {session.total_tokens}")
    """
    handler = FlowyMLCallbackHandler(
        session_name=name,
        project=project,
        framework="langchain",
        tags=tags,
        auto_log=auto_log,
        verbose=verbose,
    )

    class _ChainTraceSession:
        def __init__(self, handler):
            self._handler = handler
            self._session = handler.session

        @property
        def config(self) -> dict[str, Any]:
            return {"callbacks": [self._handler]}

        def __getattr__(self, attr_name):
            return getattr(self._session, attr_name)

    wrapper = _ChainTraceSession(handler)

    try:
        yield wrapper
    except Exception as e:
        handler.session.errors.append(str(e))
        raise
    finally:
        handler._tracer.finalize()
        if print_summary:
            handler.session.print_summary()


# ─────────────────────────────────────────────────────
# observe_chain() — Decorator for LangChain
# ─────────────────────────────────────────────────────
def observe_chain(
    name: str | None = None,
    project: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Decorator for automatic observability on LangChain functions.

    Works with **both sync and async** functions.

    Example::

        @observe_chain(name="qa_bot", project="support")
        def answer(question: str, flowyml_session=None):
            return chain.invoke(
                {"question": question},
                config=flowyml_session.config,
            )


        @observe_chain(name="async_qa", project="support")
        async def async_answer(question: str, flowyml_session=None):
            return await chain.ainvoke(
                {"question": question},
                config=flowyml_session.config,
            )
    """
    import functools
    import inspect

    def decorator(func):
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                session_name = name or func.__name__
                with trace_chain(
                    name=session_name,
                    project=project,
                    tags=tags,
                    auto_log=auto_log,
                    verbose=verbose,
                    print_summary=print_summary,
                ) as session:
                    sig = inspect.signature(func)
                    if "flowyml_session" in sig.parameters:
                        kwargs["flowyml_session"] = session
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                session_name = name or func.__name__
                with trace_chain(
                    name=session_name,
                    project=project,
                    tags=tags,
                    auto_log=auto_log,
                    verbose=verbose,
                    print_summary=print_summary,
                ) as session:
                    sig = inspect.signature(func)
                    if "flowyml_session" in sig.parameters:
                        kwargs["flowyml_session"] = session
                    return func(*args, **kwargs)

            return wrapper

    return decorator


# ─────────────────────────────────────────────────────
# instrument_chain() — Permanently wrap a Runnable
# ─────────────────────────────────────────────────────
def instrument_chain(
    chain: Any,
    name: str | None = None,
    project: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
) -> Any:
    """Instrument a LangChain Runnable for automatic tracing.

    Example::

        traced_chain = instrument_chain(chain, name="qa_chain")
        result = traced_chain.invoke({"question": "What?"})
    """

    class InstrumentedChain:
        def __init__(self, c, n, p, t, al, v, ps):
            self._chain = c
            self._name = n or getattr(c, "name", "langchain_chain")
            self._project = p
            self._tags = t
            self._auto_log = al
            self._verbose = v
            self._print_summary = ps

        def invoke(self, input_data, config=None, **kwargs):
            with trace_chain(
                name=self._name,
                project=self._project,
                tags=self._tags,
                auto_log=self._auto_log,
                verbose=self._verbose,
                print_summary=self._print_summary,
            ) as session:
                merged = dict(config or {})
                existing = merged.get("callbacks", [])
                merged["callbacks"] = existing + [session._handler]
                return self._chain.invoke(input_data, config=merged, **kwargs)

        async def ainvoke(self, input_data, config=None, **kwargs):
            with trace_chain(
                name=self._name,
                project=self._project,
                tags=self._tags,
                auto_log=self._auto_log,
                verbose=self._verbose,
                print_summary=self._print_summary,
            ) as session:
                merged = dict(config or {})
                existing = merged.get("callbacks", [])
                merged["callbacks"] = existing + [session._handler]
                return await self._chain.ainvoke(
                    input_data,
                    config=merged,
                    **kwargs,
                )

        def __getattr__(self, attr_name):
            return getattr(self._chain, attr_name)

        def __repr__(self):
            return f"InstrumentedChain(name={self._name!r}, " f"chain={self._chain!r})"

    return InstrumentedChain(
        chain,
        name,
        project,
        tags,
        auto_log,
        verbose,
        print_summary,
    )


# ─────────────────────────────────────────────────────
# trace_chain_session() — Multi-turn session for LangChain
# ─────────────────────────────────────────────────────
@contextmanager
def trace_chain_session(
    name: str = "langchain_session",
    *,
    project: str | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
    tags: dict[str, str] | None = None,
    evaluator: Any | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Context manager for multi-turn LangChain session tracing.

    Wraps :class:`SessionTracer` to provide session-level aggregation
    across multiple LangChain invocations.

    Example::

        with trace_chain_session("qa_bot", project="support") as session:
            with session.turn("user") as t:
                t.content = "What is AI?"
                result = chain.invoke(
                    {"question": "What is AI?"},
                    config={"callbacks": [session.handler]},
                )
                t.content = result
    """
    from flowyml.integrations.base import SessionTracer

    tracer = SessionTracer(
        name=name,
        project=project,
        framework="langchain",
        thread_id=thread_id,
        user_id=user_id,
        tags=tags,
        evaluator=evaluator,
        auto_log=auto_log,
        verbose=verbose,
    )

    handler = FlowyMLCallbackHandler(
        session_name=name,
        project=project,
        framework="langchain",
        tags=tags,
        auto_log=False,  # SessionTracer handles persistence
        verbose=verbose,
    )

    class _SessionChainWrapper:
        def __init__(self, tracer, handler):
            self._tracer = tracer
            self._handler = handler

        @property
        def handler(self):
            return self._handler

        @property
        def config(self) -> dict[str, Any]:
            return {"callbacks": [self._handler]}

        @property
        def genai_session(self):
            return self._tracer.genai_session

        def turn(self, role="user", content=""):
            return self._tracer.turn(role=role, content=content)

        def start_turn(self, role="user", content=""):
            return self._tracer.start_turn(role=role, content=content)

        def end_turn(self, **kwargs):
            return self._tracer.end_turn(**kwargs)

        def __getattr__(self, attr_name):
            return getattr(self._tracer.genai_session, attr_name)

    wrapper = _SessionChainWrapper(tracer, handler)

    try:
        yield wrapper
    except Exception as e:
        tracer.genai_session.errors.append(str(e))
        raise
    finally:
        tracer.end_session()
        if print_summary:
            tracer.genai_session.print_summary()

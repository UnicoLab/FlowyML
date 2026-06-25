"""🔗 LangGraph & LangChain Integration — Full GenAI Observability for FlowyML.

Provides automatic tracing, logging, and observability for LangGraph agents
and LangChain components with zero-config setup.

Usage:
    # 1. Decorator — Wrap any LangGraph agent function
    @observe(name="my_agent", project="chatbot")
    def run_agent(query: str):
        return graph.invoke({"messages": [HumanMessage(content=query)]})

    # 2. Context Manager — Wrap an entire graph invocation
    with trace_graph("my_agent", project="chatbot") as session:
        result = graph.invoke(
            {"messages": [HumanMessage(content="Hello")]},
            config=session.config,
        )

    # 3. Callback Handler — Use directly with LangChain/LangGraph
    handler = FlowyMLCallbackHandler(session_name="my_agent")
    result = graph.invoke(input, config={"callbacks": [handler]})

    # 4. Instrument a compiled graph permanently
    traced_graph = instrument(graph, name="my_agent", project="chatbot")
    result = traced_graph.invoke(input)  # Auto-traced every time
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any

from flowyml.integrations.base import (
    BaseTracer,
    TraceSession,
    TraceSpan,
    safe_serialize,
)

# Re-export for backward compatibility
__all__ = [
    "FlowyMLCallbackHandler",
    "TraceSession",
    "TraceSpan",
    "trace_graph",
    "observe",
    "instrument",
]


# ─────────────────────────────────────────────────────
# FlowyML Callback Handler (LangChain/LangGraph)
# ─────────────────────────────────────────────────────
class FlowyMLCallbackHandler:
    """LangChain BaseCallbackHandler that logs everything to FlowyML.

    Compatible with all LangChain runnables and LangGraph compiled graphs.
    Captures LLM calls, tool invocations, chains, agent actions, retriever
    queries, and graph node transitions with full token/cost telemetry.

    Usage::

        handler = FlowyMLCallbackHandler(session_name="my_agent")
        result = graph.invoke(input, config={"callbacks": [handler]})
        handler.session.print_summary()
    """

    def __init__(
        self,
        session_name: str = "langgraph_session",
        project: str | None = None,
        framework: str = "langgraph",
        tags: dict[str, str] | None = None,
        session: TraceSession | None = None,
        auto_log: bool = True,
        verbose: bool = False,
    ):
        self._tracer = BaseTracer(
            name=session_name,
            project=project,
            framework=framework,
            tags=tags,
            session=session,
            auto_log=auto_log,
            verbose=verbose,
        )
        self.session = self._tracer.session
        self.trace_id = self._tracer.trace_id
        self.auto_log = auto_log
        self.verbose = verbose

    # ─── LLM Events ─────────────────────────────────
    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: str | None = None,
        parent_run_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM starts."""
        rid = str(run_id or uuid.uuid4())
        name = serialized.get("name", serialized.get("id", ["LLM"])[-1])
        invocation_params = kwargs.get("invocation_params", {})
        model = invocation_params.get("model_name") or invocation_params.get("model")

        span = self._tracer.start_span(
            "llm",
            name,
            run_id=rid,
            inputs={"prompts": [safe_serialize(p) for p in prompts]},
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            metadata={
                **(metadata or {}),
                **({"tags": tags} if tags else {}),
                **({"model": model} if model else {}),
            },
        )
        if model:
            span.model = model
            self.session.add_model(model)
        self.session.total_llm_calls += 1
        # Auto-save prompts as artifacts
        for i, p in enumerate(prompts):
            span.add_artifact(
                f"prompt_{i}",
                "prompt",
                p,
                metadata={"model": model, "index": i},
            )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: str | None = None,
        parent_run_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chat model starts."""
        rid = str(run_id or uuid.uuid4())
        name = serialized.get(
            "name",
            serialized.get("id", ["ChatModel"])[-1],
        )

        model = (
            kwargs.get("invocation_params", {}).get("model_name")
            or kwargs.get("invocation_params", {}).get("model")
            or serialized.get("kwargs", {}).get("model_name")
            or serialized.get("kwargs", {}).get("model")
        )

        msg_data = []
        for msg_list in messages:
            for msg in msg_list:
                if hasattr(msg, "type") and hasattr(msg, "content"):
                    msg_data.append(
                        {
                            "role": msg.type,
                            "content": safe_serialize(msg.content),
                        },
                    )
                else:
                    msg_data.append(safe_serialize(msg))

        span = self._tracer.start_span(
            "chat_model",
            name,
            run_id=rid,
            inputs={"messages": msg_data},
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            metadata={
                **(metadata or {}),
                **({"tags": tags} if tags else {}),
                **({"model": model} if model else {}),
            },
        )
        if model:
            span.model = model
            self.session.add_model(model)
        self.session.total_llm_calls += 1
        # Auto-save chat messages as prompt artifact
        span.add_artifact(
            "chat_messages",
            "prompt",
            msg_data,
            metadata={"model": model, "message_count": len(msg_data)},
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM finishes."""
        rid = str(run_id or "")
        span = self._tracer._run_to_span.get(rid)
        if span is None:
            return

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        model = span.model

        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage") or response.llm_output.get("usage", {})
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0) or 0
                completion_tokens = usage.get("completion_tokens", 0) or 0
                total_tokens = usage.get("total_tokens", 0) or prompt_tokens + completion_tokens
            model = model or response.llm_output.get("model_name") or response.llm_output.get("model")

        if hasattr(response, "generations") and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, "generation_info") and gen.generation_info:
                        usage = gen.generation_info.get("usage", {})
                        if usage:
                            prompt_tokens += usage.get("prompt_tokens", 0) or 0
                            completion_tokens += usage.get("completion_tokens", 0) or 0

        if not total_tokens:
            total_tokens = prompt_tokens + completion_tokens

        span.set_tokens(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
        )
        self.session.record_tokens(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=span.cost,
        )

        output_text = ""
        if hasattr(response, "generations") and response.generations:
            texts = []
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, "text"):
                        texts.append(gen.text)
                    elif hasattr(gen, "message") and hasattr(gen.message, "content"):
                        texts.append(gen.message.content)
            output_text = "\n".join(texts)

        self._tracer.end_span(
            rid,
            outputs={"response": safe_serialize(output_text)},
        )
        # Auto-save response as artifact
        if span and output_text:
            span.add_artifact(
                "llm_response",
                "response",
                output_text,
                metadata={"model": model, "tokens": total_tokens},
            )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM errors."""
        self._tracer.end_span(str(run_id or ""), error=str(error))

    # ─── Chain Events ───────────────────────────────
    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: str | None = None,
        parent_run_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain starts (includes LangGraph nodes)."""
        rid = str(run_id or uuid.uuid4())
        name = serialized.get("name", serialized.get("id", ["Chain"])[-1])

        node_name = None
        if tags:
            for tag in tags:
                if tag.startswith("graph:") or tag.startswith("seq:"):
                    node_name = tag

        event_type = "graph_node" if node_name else "chain"

        span = self._tracer.start_span(
            event_type,
            name,
            run_id=rid,
            inputs={"input": safe_serialize(inputs)},
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            metadata={
                **(metadata or {}),
                **({"tags": tags} if tags else {}),
            },
        )
        span.node_name = node_name
        self.session.total_chain_calls += 1

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._tracer.end_span(
            str(run_id or ""),
            outputs={"output": safe_serialize(outputs)},
        )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._tracer.end_span(str(run_id or ""), error=str(error))

    # ─── Tool Events ────────────────────────────────
    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: str | None = None,
        parent_run_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or uuid.uuid4())
        name = serialized.get("name", serialized.get("id", ["Tool"])[-1])

        span = self._tracer.start_span(
            "tool",
            name,
            run_id=rid,
            inputs={"tool_input": safe_serialize(input_str)},
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            metadata=metadata or {},
        )
        span.tool_name = name
        span.tool_input = safe_serialize(input_str)
        self.session.total_tool_calls += 1
        self.session.add_tool(name)
        # Auto-save tool input as artifact
        span.add_artifact(
            f"tool_input:{name}",
            "intermediate",
            input_str,
            metadata={"tool": name},
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        span = self._tracer._run_to_span.get(rid)
        if span:
            span.tool_output = safe_serialize(output)
        self._tracer.end_span(
            rid,
            outputs={"tool_output": safe_serialize(output)},
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._tracer.end_span(str(run_id or ""), error=str(error))

    # ─── Agent Events ───────────────────────────────
    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: str | None = None,
        parent_run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or uuid.uuid4())
        tool = getattr(action, "tool", "unknown")
        tool_input = getattr(action, "tool_input", "")

        self._tracer.start_span(
            "agent_action",
            f"action:{tool}",
            run_id=f"{rid}_action",
            inputs={
                "tool": tool,
                "tool_input": safe_serialize(tool_input),
                "log": safe_serialize(getattr(action, "log", "")),
            },
            parent_run_id=str(parent_run_id) if parent_run_id else None,
        )

    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or "")
        output = getattr(finish, "return_values", {})
        self._tracer.end_span(
            f"{rid}_action",
            outputs={"return_values": safe_serialize(output)},
        )

    # ─── Retriever Events ───────────────────────────
    def on_retriever_start(
        self,
        serialized: dict[str, Any],
        query: str,
        *,
        run_id: str | None = None,
        parent_run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id or uuid.uuid4())
        name = serialized.get(
            "name",
            serialized.get("id", ["Retriever"])[-1],
        )
        self._tracer.start_span(
            "retriever",
            name,
            run_id=rid,
            inputs={"query": safe_serialize(query)},
            parent_run_id=str(parent_run_id) if parent_run_id else None,
        )

    def on_retriever_end(
        self,
        documents: list[Any],
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        doc_summaries = []
        for doc in documents[:10]:
            if hasattr(doc, "page_content"):
                doc_summaries.append(
                    {
                        "content": safe_serialize(
                            doc.page_content,
                            max_len=500,
                        ),
                        "metadata": safe_serialize(
                            getattr(doc, "metadata", {}),
                            max_len=200,
                        ),
                    },
                )
            else:
                doc_summaries.append(safe_serialize(doc, max_len=500))
        self._tracer.end_span(
            str(run_id or ""),
            outputs={"documents": doc_summaries, "count": len(documents)},
        )
        # Auto-save retrieved documents as artifacts
        rid = str(run_id or "")
        span = self._tracer._run_to_span.get(rid) if rid else None
        if span is None:
            # span already ended, get from session steps
            for step in reversed(self.session.steps):
                if step.get("type") == "retriever":
                    break
        self.session.total_retriever_calls = (
            getattr(
                self.session,
                "total_retriever_calls",
                0,
            )
            + 1
        )
        # Save each document as separate artifact at session level
        for i, doc_info in enumerate(doc_summaries[:5]):
            self.session.artifacts.append(
                {
                    "artifact_id": str(uuid.uuid4()),
                    "span_id": rid,
                    "name": f"retrieved_doc_{i}",
                    "type": "document",
                    "content": safe_serialize(doc_info, max_len=5000),
                    "metadata": {"index": i, "total": len(documents)},
                    "timestamp": time.time(),
                },
            )

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._tracer.end_span(str(run_id or ""), error=str(error))

    # ─── Streaming (no-op to avoid noise) ───────────
    def on_text(self, text: str, **kwargs: Any) -> None:
        pass

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        pass


# ─────────────────────────────────────────────────────
# trace_graph() — Context manager for LangGraph
# ─────────────────────────────────────────────────────
@contextmanager
def trace_graph(
    name: str = "langgraph_agent",
    project: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Context manager for tracing a LangGraph invocation.

    Yields a :class:`_GraphTraceSession` with a ``.config`` property
    that injects the callback handler into ``graph.invoke()``.

    Example::

        with trace_graph("my_agent", project="chatbot") as session:
            result = graph.invoke(
                {"messages": [HumanMessage(content="Hello")]},
                config=session.config,
            )
    """
    handler = FlowyMLCallbackHandler(
        session_name=name,
        project=project,
        tags=tags,
        auto_log=auto_log,
        verbose=verbose,
    )

    class _GraphTraceSession:
        """Thin wrapper that adds .config for LangChain compatibility."""

        def __init__(self, handler):
            self._handler = handler
            self._session = handler.session

        @property
        def config(self) -> dict[str, Any]:
            return {"callbacks": [self._handler]}

        def __getattr__(self, name):
            return getattr(self._session, name)

    wrapper = _GraphTraceSession(handler)

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
# observe() — Decorator for LangGraph
# ─────────────────────────────────────────────────────
def observe(
    name: str | None = None,
    project: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Decorator for automatic observability on LangGraph functions.

    The decorated function receives a ``flowyml_session`` keyword argument
    with the active session. Use ``session.config`` to pass callbacks.

    Example::

        @observe(name="customer_agent", project="support")
        def handle_query(query: str, flowyml_session=None):
            return graph.invoke(
                {"messages": [HumanMessage(content=query)]},
                config=flowyml_session.config if flowyml_session else {},
            )
    """
    import functools
    import inspect as _inspect

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            session_name = name or func.__name__
            with trace_graph(
                name=session_name,
                project=project,
                tags=tags,
                auto_log=auto_log,
                verbose=verbose,
                print_summary=print_summary,
            ) as session:
                sig = _inspect.signature(func)
                if "flowyml_session" in sig.parameters:
                    kwargs["flowyml_session"] = session
                return func(*args, **kwargs)

        return wrapper

    return decorator


# ─────────────────────────────────────────────────────
# instrument() — Permanently wrap a compiled graph
# ─────────────────────────────────────────────────────
def instrument(
    graph: Any,
    name: str | None = None,
    project: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
) -> Any:
    """Instrument a LangGraph compiled graph for automatic tracing.

    Returns a wrapper that behaves identically to the original graph
    but automatically injects FlowyML callbacks on every invocation.

    Example::

        traced_graph = instrument(graph, name="my_agent", project="demo")
        result = traced_graph.invoke({"messages": [...]})
    """

    class InstrumentedGraph:
        def __init__(self, g, n, p, t, al, v, ps):
            self._graph = g
            self._name = n or getattr(g, "name", "langgraph_agent")
            self._project = p
            self._tags = t
            self._auto_log = al
            self._verbose = v
            self._print_summary = ps

        def invoke(
            self,
            input_data: Any,
            config: dict[str, Any] | None = None,
            **kwargs,
        ) -> Any:
            with trace_graph(
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
                return self._graph.invoke(input_data, config=merged, **kwargs)

        async def ainvoke(
            self,
            input_data: Any,
            config: dict[str, Any] | None = None,
            **kwargs,
        ) -> Any:
            with trace_graph(
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
                return await self._graph.ainvoke(
                    input_data,
                    config=merged,
                    **kwargs,
                )

        def stream(
            self,
            input_data: Any,
            config: dict[str, Any] | None = None,
            **kwargs,
        ):
            handler = FlowyMLCallbackHandler(
                session_name=self._name,
                project=self._project,
                tags=self._tags,
                auto_log=self._auto_log,
                verbose=self._verbose,
            )
            merged = dict(config or {})
            existing = merged.get("callbacks", [])
            merged["callbacks"] = existing + [handler]
            try:
                yield from self._graph.stream(
                    input_data,
                    config=merged,
                    **kwargs,
                )
            finally:
                handler._tracer.finalize()
                if self._print_summary:
                    handler.session.print_summary()

        def __getattr__(self, attr_name):
            return getattr(self._graph, attr_name)

        def __repr__(self):
            return f"InstrumentedGraph(name={self._name!r}, graph={self._graph!r})"

    return InstrumentedGraph(
        graph,
        name,
        project,
        tags,
        auto_log,
        verbose,
        print_summary,
    )

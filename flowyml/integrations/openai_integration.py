"""🤖 OpenAI Integration — Direct FlowyML Observability for OpenAI SDK.

No LangChain required! Works directly with the ``openai`` Python package.

Usage:
    # Drop-in replacement
    from flowyml.integrations.openai_integration import TracedOpenAI
    client = TracedOpenAI(project="my_project")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}],
    )

    # Patch existing client
    from flowyml.integrations.openai_integration import patch_openai
    import openai
    client = openai.OpenAI()
    patch_openai(client, project="my_project")
    response = client.chat.completions.create(...)

    # Decorator
    from flowyml.integrations.openai_integration import trace_openai
    @trace_openai(name="summarizer", project="demo")
    def summarize(text: str, flowyml_session=None):
        return client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": text}],
        )
"""

from __future__ import annotations

import functools
import logging
from contextlib import contextmanager
from typing import Any

from flowyml.integrations.base import (
    BaseTracer,
    TraceSession,
    TraceSpan,
    safe_serialize,
)

logger = logging.getLogger(__name__)

__all__ = [
    "TracedOpenAI",
    "TracedOpenAISession",
    "patch_openai",
    "trace_openai",
    "trace_openai_session",
]


# ─────────────────────────────────────────────────────
# Wrapper for chat.completions.create
# ─────────────────────────────────────────────────────
def _wrap_completions_create(
    original_create: Any,
    tracer: BaseTracer,
) -> Any:
    """Wrap chat.completions.create to capture traces."""

    @functools.wraps(original_create)
    def wrapped(*args, **kwargs):
        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])
        stream = kwargs.get("stream", False)

        span = tracer.start_span(
            "chat_model",
            f"openai:{model}",
            inputs={
                "messages": [
                    {
                        "role": m.get("role", "?"),
                        "content": safe_serialize(
                            m.get("content", ""),
                            max_len=2000,
                        ),
                    }
                    for m in (messages or [])[:20]
                ],
                "model": model,
                "temperature": kwargs.get("temperature"),
                "max_tokens": kwargs.get("max_tokens"),
            },
        )
        tracer.session.total_llm_calls += 1
        tracer.session.add_model(model)

        try:
            response = original_create(*args, **kwargs)

            if stream:
                return _wrap_stream(response, span, tracer)

            # Extract usage from response
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", 0) or 0

            span.set_tokens(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=model,
            )
            tracer.session.record_tokens(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=span.cost,
            )

            # Extract response content
            content = ""
            choices = getattr(response, "choices", [])
            if choices:
                msg = getattr(choices[0], "message", None)
                if msg:
                    content = getattr(msg, "content", "") or ""

            tracer.end_span(
                span,
                outputs={
                    "content": safe_serialize(content),
                    "model": getattr(response, "model", model),
                    "finish_reason": (getattr(choices[0], "finish_reason", None) if choices else None),
                },
            )

            return response

        except Exception as e:
            tracer.end_span(span, error=str(e))
            raise

    return wrapped


def _wrap_stream(stream, span: TraceSpan, tracer: BaseTracer):
    """Wrap a streaming response to capture stats at the end."""
    content_parts = []
    completion_tokens = 0
    model = span.model

    def stream_wrapper():
        nonlocal completion_tokens, model
        try:
            for chunk in stream:
                choices = getattr(chunk, "choices", [])
                if choices:
                    delta = getattr(choices[0], "delta", None)
                    if delta:
                        c = getattr(delta, "content", None)
                        if c:
                            content_parts.append(c)
                            completion_tokens += 1

                usage = getattr(chunk, "usage", None)
                if usage:
                    completion_tokens = getattr(usage, "completion_tokens", 0) or 0

                model = getattr(chunk, "model", model)
                yield chunk
        finally:
            span.set_tokens(
                completion_tokens=completion_tokens,
                model=model,
            )
            tracer.session.record_tokens(
                completion_tokens=completion_tokens,
                cost=span.cost,
            )
            tracer.end_span(
                span,
                outputs={
                    "content": "".join(content_parts)[:5000],
                    "streamed": True,
                    "model": model,
                },
            )

    return stream_wrapper()


# ─────────────────────────────────────────────────────
# Wrapper for embeddings.create
# ─────────────────────────────────────────────────────
def _wrap_embeddings_create(
    original_create: Any,
    tracer: BaseTracer,
) -> Any:
    """Wrap embeddings.create to capture traces."""

    @functools.wraps(original_create)
    def wrapped(*args, **kwargs):
        model = kwargs.get("model", "text-embedding-3-small")
        input_text = kwargs.get("input", "")

        texts = input_text if isinstance(input_text, list) else [input_text]
        span = tracer.start_span(
            "embedding",
            f"openai:{model}",
            inputs={
                "texts": [safe_serialize(t, max_len=500) for t in texts[:5]],
                "count": len(texts),
                "model": model,
            },
        )
        tracer.session.total_embedding_calls += 1
        tracer.session.add_model(model)

        try:
            response = original_create(*args, **kwargs)

            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", 0) or 0

            span.set_tokens(
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
                model=model,
            )
            tracer.session.record_tokens(
                prompt_tokens=prompt_tokens,
                total_tokens=total_tokens,
                cost=span.cost,
            )

            data = getattr(response, "data", [])
            dims = len(getattr(data[0], "embedding", [])) if data else None

            tracer.end_span(
                span,
                outputs={
                    "dimensions": dims,
                    "count": len(data),
                    "model": getattr(response, "model", model),
                },
            )

            return response

        except Exception as e:
            tracer.end_span(span, error=str(e))
            raise

    return wrapped


# ─────────────────────────────────────────────────────
# patch_openai() — Monkey-patch an existing client
# ─────────────────────────────────────────────────────
def patch_openai(
    client: Any,
    *,
    project: str | None = None,
    name: str = "openai_session",
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
) -> BaseTracer:
    """Monkey-patch an OpenAI client for automatic tracing.

    Returns the tracer so you can access session metrics.

    Example::

        import openai

        client = openai.OpenAI()
        tracer = patch_openai(client, project="my_project")
        response = client.chat.completions.create(...)
        tracer.session.print_summary()
    """
    tracer = BaseTracer(
        name=name,
        project=project,
        framework="openai",
        tags=tags,
        auto_log=auto_log,
        verbose=verbose,
    )

    if hasattr(client, "chat") and hasattr(client.chat, "completions"):
        original = client.chat.completions.create
        client.chat.completions.create = _wrap_completions_create(
            original,
            tracer,
        )

    if hasattr(client, "embeddings"):
        original_emb = client.embeddings.create
        client.embeddings.create = _wrap_embeddings_create(
            original_emb,
            tracer,
        )

    return tracer


# ─────────────────────────────────────────────────────
# TracedOpenAI — Drop-in replacement
# ─────────────────────────────────────────────────────
class TracedOpenAI:
    """Drop-in replacement for ``openai.OpenAI()`` with auto-tracing.

    All chat completions and embedding calls are automatically traced
    and logged to FlowyML.

    Example::

        client = TracedOpenAI(project="my_project")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello!"}],
        )
        client.tracer.session.print_summary()
    """

    def __init__(
        self,
        *,
        project: str | None = None,
        name: str = "openai_session",
        tags: dict[str, str] | None = None,
        auto_log: bool = True,
        verbose: bool = False,
        print_summary_on_del: bool = False,
        **openai_kwargs,
    ):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "The openai package is required. Install it with: pip install openai",
            )

        self._client = openai.OpenAI(**openai_kwargs)
        self.tracer = patch_openai(
            self._client,
            project=project,
            name=name,
            tags=tags,
            auto_log=auto_log,
            verbose=verbose,
        )
        self._print_on_del = print_summary_on_del

    @property
    def session(self) -> TraceSession:
        return self.tracer.session

    @property
    def chat(self):
        return self._client.chat

    @property
    def embeddings(self):
        return self._client.embeddings

    @property
    def models(self):
        return self._client.models

    def finalize(self) -> None:
        """Finalize the session and print summary."""
        self.tracer.finalize()
        self.session.print_summary()

    def __getattr__(self, name):
        return getattr(self._client, name)

    def __repr__(self):
        return f"TracedOpenAI(project={self.session.project!r})"


# ─────────────────────────────────────────────────────
# TracedOpenAISession — Session-mode drop-in
# ─────────────────────────────────────────────────────
class TracedOpenAISession:
    """Session-mode OpenAI client with multi-turn tracking and auto-evals.

    Each ``chat.completions.create`` call is automatically wrapped as a
    turn within the session.  Evaluators and event streams can be attached
    for real-time quality monitoring.

    Example::

        from flowyml.integrations.openai_integration import TracedOpenAISession
        from flowyml.integrations.eval_bridge import SessionEvaluator
        from flowyml.evals import Relevance

        client = TracedOpenAISession(
            project="support",
            evaluator=SessionEvaluator([Relevance(threshold=0.7)]),
        )
        # Each call is a turn
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello!"}],
        )
        resp2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Hello!"},
                {"role": "assistant", "content": resp.choices[0].message.content},
                {"role": "user", "content": "Tell me more"},
            ],
        )
        client.finalize()  # Prints session summary with eval scores
    """

    def __init__(
        self,
        *,
        project: str | None = None,
        name: str = "openai_session",
        thread_id: str | None = None,
        user_id: str | None = None,
        tags: dict[str, str] | None = None,
        evaluator: Any | None = None,
        auto_log: bool = True,
        verbose: bool = False,
        **openai_kwargs,
    ):
        from flowyml.integrations.base import SessionTracer

        try:
            import openai
        except ImportError:
            raise ImportError(
                "The openai package is required. Install it with: pip install openai",
            )

        self._client = openai.OpenAI(**openai_kwargs)
        self._session_tracer = SessionTracer(
            name=name,
            project=project,
            framework="openai",
            thread_id=thread_id,
            user_id=user_id,
            tags=tags,
            evaluator=evaluator,
            auto_log=auto_log,
            verbose=verbose,
        )

        # Wrap chat completions with session-aware tracing
        if hasattr(self._client, "chat") and hasattr(
            self._client.chat,
            "completions",
        ):
            original = self._client.chat.completions.create
            self._client.chat.completions.create = self._wrap_session_create(original)

    def _wrap_session_create(self, original_create: Any) -> Any:
        """Wrap create to automatically manage turns."""
        tracer = self._session_tracer

        @functools.wraps(original_create)
        def wrapped(*args, **kwargs):
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])

            # Extract user content for turn
            user_content = ""
            for m in reversed(messages or []):
                if m.get("role") == "user":
                    user_content = str(m.get("content", ""))
                    break

            tracer.start_turn(role="user", content=user_content)

            span = tracer.start_span(
                "chat_model",
                f"openai:{model}",
                inputs={
                    "messages": [
                        {
                            "role": m.get("role", "?"),
                            "content": safe_serialize(
                                m.get("content", ""),
                                max_len=2000,
                            ),
                        }
                        for m in (messages or [])[:20]
                    ],
                    "model": model,
                },
            )
            tracer.session.total_llm_calls += 1
            tracer.session.add_model(model)

            try:
                response = original_create(*args, **kwargs)

                usage = getattr(response, "usage", None)
                prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                total_tokens = getattr(usage, "total_tokens", 0) or 0

                span.set_tokens(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    model=model,
                )
                tracer.session.record_tokens(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=span.cost,
                )

                content = ""
                choices = getattr(response, "choices", [])
                if choices:
                    msg = getattr(choices[0], "message", None)
                    if msg:
                        content = getattr(msg, "content", "") or ""

                tracer.end_span(
                    span,
                    outputs={"content": safe_serialize(content)},
                )
                tracer.end_turn(content=content)

                return response

            except Exception as e:
                tracer.end_span(span, error=str(e))
                tracer.end_turn(error=str(e))
                raise

        return wrapped

    @property
    def genai_session(self):
        return self._session_tracer.genai_session

    @property
    def chat(self):
        return self._client.chat

    @property
    def embeddings(self):
        return self._client.embeddings

    def finalize(self) -> None:
        """Finalize session and print summary."""
        self._session_tracer.end_session()
        self.genai_session.print_summary()

    def __getattr__(self, name):
        return getattr(self._client, name)

    def __repr__(self):
        return f"TracedOpenAISession(project={self.genai_session.project!r}, turns={self.genai_session.total_turns})"


# ─────────────────────────────────────────────────────
# trace_openai() — Decorator for OpenAI functions
# ─────────────────────────────────────────────────────
def trace_openai(
    name: str | None = None,
    project: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Decorator for functions that use the OpenAI SDK directly.

    Example::

        @trace_openai(name="summarizer", project="demo")
        def summarize(text: str, flowyml_session=None):
            client = openai.OpenAI()
            return client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": text}],
            )
    """
    from flowyml.integrations.base import observe as _base_observe

    return _base_observe(
        name=name,
        project=project,
        framework="openai",
        tags=tags,
        auto_log=auto_log,
        verbose=verbose,
        print_summary=print_summary,
    )


# ─────────────────────────────────────────────────────
# trace_openai_session() — Context manager
# ─────────────────────────────────────────────────────
@contextmanager
def trace_openai_session(
    name: str = "openai_session",
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
    """Context manager for multi-turn OpenAI session tracing.

    Example::

        with trace_openai_session("chatbot", project="demo") as client:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello!"}],
            )
    """
    client = TracedOpenAISession(
        project=project,
        name=name,
        thread_id=thread_id,
        user_id=user_id,
        tags=tags,
        evaluator=evaluator,
        auto_log=auto_log,
        verbose=verbose,
    )
    try:
        yield client
    except Exception as e:
        client.genai_session.errors.append(str(e))
        raise
    finally:
        client._session_tracer.end_session()
        if print_summary:
            client.genai_session.print_summary()

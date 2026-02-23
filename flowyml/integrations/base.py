"""🔗 GenAI Observability Foundation — Framework-Agnostic Core.

This module provides the shared data model and utilities used by all
FlowyML GenAI integrations (LangGraph, LangChain, OpenAI, generic).

Public API:
    - TraceSpan      — Single span within a trace
    - TraceSession   — Aggregated session for one invocation
    - BaseTracer     — Manages span lifecycle + persistence
    - trace()        — Context manager for tracing any GenAI code
    - observe()      — Decorator for automatic observability
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
import time
import uuid
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────
# Cost Estimation (per 1K tokens)
# ─────────────────────────────────────────────────────
MODEL_COSTS: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"prompt": 0.0025, "completion": 0.01},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
    "o1": {"prompt": 0.015, "completion": 0.06},
    "o1-mini": {"prompt": 0.003, "completion": 0.012},
    "o3-mini": {"prompt": 0.0011, "completion": 0.0044},
    # Anthropic
    "claude-3-5-sonnet": {"prompt": 0.003, "completion": 0.015},
    "claude-3-5-haiku": {"prompt": 0.0008, "completion": 0.004},
    "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
    "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
    "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
    # Google
    "gemini-2.0-flash": {"prompt": 0.0001, "completion": 0.0004},
    "gemini-1.5-pro": {"prompt": 0.00125, "completion": 0.005},
    "gemini-1.5-flash": {"prompt": 0.000075, "completion": 0.0003},
    # Mistral
    "mistral-large": {"prompt": 0.002, "completion": 0.006},
    "mistral-medium": {"prompt": 0.0027, "completion": 0.0081},
    "mistral-small": {"prompt": 0.0002, "completion": 0.0006},
    # Cohere
    "command-r-plus": {"prompt": 0.002, "completion": 0.01},
    "command-r": {"prompt": 0.0005, "completion": 0.0015},
}


def estimate_cost(
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Estimate cost in USD based on model and token counts."""
    if not model:
        return 0.0
    model_key = model.lower().split("/")[-1].split(":")[-1]
    for key, costs in MODEL_COSTS.items():
        if key in model_key:
            return prompt_tokens / 1000 * costs["prompt"] + completion_tokens / 1000 * costs["completion"]
    return 0.0


# ─────────────────────────────────────────────────────
# Safe Serialization
# ─────────────────────────────────────────────────────
def safe_serialize(obj: Any, max_len: int = 5000) -> str:
    """Safely serialize an object to a JSON-friendly string."""
    try:
        if isinstance(obj, str):
            s = obj
        elif isinstance(obj, (dict, list, tuple)):
            s = json.dumps(obj, default=str, ensure_ascii=False)
        else:
            s = str(obj)
    except Exception:
        s = repr(obj)
    return s[:max_len] if len(s) > max_len else s


# ─────────────────────────────────────────────────────
# Trace Span
# ─────────────────────────────────────────────────────
@dataclass
class TraceSpan:
    """A single span within a trace (LLM call, tool call, chain, etc.).

    Each span captures a complete unit of work with full context:
    inputs, outputs, artifacts, tokens, cost, and timing. Spans
    form a tree via parent_id for canvas DAG visualization.
    """

    event_id: str
    trace_id: str
    parent_id: str | None
    event_type: str  # llm, chat_model, tool, chain, agent, retriever, graph_node, embedding, custom
    name: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration: float | None = None
    status: str = "running"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Token usage & cost
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str | None = None

    # Tool-specific
    tool_name: str | None = None
    tool_input: str | None = None
    tool_output: str | None = None

    # Graph-specific
    node_name: str | None = None

    # Artifacts attached to this span (prompts, outputs, docs, etc.)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def end(
        self,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Finalize the span."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        if outputs is not None:
            self.outputs = outputs
        if error:
            self.status = "error"
            self.error = str(error)
        else:
            self.status = "success"

    def set_tokens(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        model: str | None = None,
    ) -> None:
        """Set token usage and auto-calculate cost."""
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens or (prompt_tokens + completion_tokens)
        if model:
            self.model = model
        self.cost = estimate_cost(self.model, prompt_tokens, completion_tokens)

    def add_artifact(
        self,
        name: str,
        artifact_type: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Attach an artifact to this span.

        Artifacts are first-class objects: prompts, responses, documents,
        images, configs, intermediate results — anything worth tracking.

        Args:
            name: Human-readable name (e.g. "system_prompt").
            artifact_type: "prompt", "response", "document", "embedding",
                "image", "config", "intermediate", "code".
            content: The artifact content (auto-serialized).
            metadata: Optional metadata dict.

        Returns:
            The artifact dict that was added.
        """
        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "span_id": self.event_id,
            "name": name,
            "type": artifact_type,
            "content": safe_serialize(content, max_len=50000),
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self.artifacts.append(artifact)
        return artifact

    def to_event_dict(self) -> dict[str, Any]:
        """Convert to FlowyML trace event dict (canvas-ready)."""
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "event_type": self.event_type,
            "name": self.name,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "status": self.status,
            "error": self.error,
            "metadata": {
                **self.metadata,
                **({"tool_name": self.tool_name} if self.tool_name else {}),
                **({"tool_input": self.tool_input} if self.tool_input else {}),
                **({"tool_output": self.tool_output} if self.tool_output else {}),
                **({"node_name": self.node_name} if self.node_name else {}),
            },
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "model": self.model,
            "artifacts": self.artifacts,
        }


# ─────────────────────────────────────────────────────
# Trace Session
# ─────────────────────────────────────────────────────
@dataclass
class TraceSession:
    """Aggregated observability session for a single invocation.

    Collects metrics across all spans produced during one logical
    operation (an agent run, a chain invocation, a batch of API calls, etc.).
    """

    session_id: str
    name: str
    project: str | None = None
    framework: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    # Aggregated metrics
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_chain_calls: int = 0
    total_embedding_calls: int = 0
    total_retriever_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    models_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    # Canvas graph data (edges for DAG visualization)
    _edges: list[tuple[str, str]] = field(default_factory=list, repr=False)

    @property
    def duration(self) -> float | None:
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def add_model(self, model: str) -> None:
        """Register a model name if not already tracked."""
        if model and model not in self.models_used:
            self.models_used.append(model)

    def add_tool(self, tool_name: str) -> None:
        """Register a tool name if not already tracked."""
        if tool_name and tool_name not in self.tools_used:
            self.tools_used.append(tool_name)

    def record_tokens(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Add token counts and cost to session aggregates."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += total_tokens or (prompt_tokens + completion_tokens)
        self.total_cost += cost

    def record_step(self, span: TraceSpan) -> None:
        """Record a completed span as a step in the session."""
        self.steps.append(
            {
                "event_id": span.event_id,
                "parent_id": span.parent_id,
                "name": span.name,
                "type": span.event_type,
                "duration": round(span.duration or 0, 4),
                "status": span.status,
                "model": span.model,
                "tokens": span.total_tokens,
                "cost": round(span.cost, 6),
                "inputs": span.inputs,
                "outputs": span.outputs,
                "artifacts": span.artifacts,
            },
        )
        # Track edge for canvas DAG
        if span.parent_id:
            self._edges.append((span.parent_id, span.event_id))
        # Collect artifacts at session level
        self.artifacts.extend(span.artifacts)
        if span.error:
            self.errors.append(
                f"[{span.event_type}:{span.name}] {span.error[:200]}",
            )

    def to_canvas_graph(self) -> dict[str, Any]:
        """Return canvas-ready DAG data for FlowyML UI visualization.

        Returns a dict with ``nodes`` and ``edges`` suitable for rendering
        the full trace as an interactive DAG in the FlowyML canvas.
        """
        nodes = []
        for step in self.steps:
            nodes.append(
                {
                    "id": step["event_id"],
                    "label": step["name"],
                    "type": step["type"],
                    "status": step["status"],
                    "duration": step["duration"],
                    "model": step.get("model"),
                    "tokens": step.get("tokens", 0),
                    "cost": step.get("cost", 0),
                    "inputs": step.get("inputs"),
                    "outputs": step.get("outputs"),
                    "artifacts": step.get("artifacts", []),
                },
            )
        edges = [{"source": src, "target": tgt} for src, tgt in self._edges]
        return {"nodes": nodes, "edges": edges}

    def summary(self) -> dict[str, Any]:
        """Return a human-readable summary dict."""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "project": self.project,
            "framework": self.framework,
            "duration_seconds": round(self.duration or 0, 3),
            "llm_calls": self.total_llm_calls,
            "tool_calls": self.total_tool_calls,
            "chain_calls": self.total_chain_calls,
            "embedding_calls": self.total_embedding_calls,
            "retriever_calls": self.total_retriever_calls,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "estimated_cost_usd": round(self.total_cost, 6),
            "models_used": list(set(self.models_used)),
            "tools_used": list(set(self.tools_used)),
            "artifacts_count": len(self.artifacts),
            "errors": self.errors,
            "steps_count": len(self.steps),
            "canvas_graph": self.to_canvas_graph(),
        }

    def print_summary(self) -> None:
        """Pretty-print the session summary."""
        s = self.summary()
        fw = f" ({s['framework']})" if s["framework"] else ""
        print("\n" + "═" * 60)
        print(f"  🔗 FlowyML Trace — {s['name']}{fw}")
        print("═" * 60)
        print(f"  📋 Session    : {s['session_id'][:12]}...")
        if s["project"]:
            print(f"  📂 Project    : {s['project']}")
        print(f"  ⏱  Duration   : {s['duration_seconds']:.2f}s")
        print(f"  🤖 LLM Calls  : {s['llm_calls']}")
        print(f"  🔧 Tool Calls : {s['tool_calls']}")
        if s["chain_calls"]:
            print(f"  🔗 Chains     : {s['chain_calls']}")
        if s["embedding_calls"]:
            print(f"  📐 Embeddings : {s['embedding_calls']}")
        print(
            f"  📊 Tokens     : {s['total_tokens']:,} "
            f"(prompt: {s['prompt_tokens']:,} / "
            f"completion: {s['completion_tokens']:,})",
        )
        print(f"  💰 Est. Cost  : ${s['estimated_cost_usd']:.4f}")
        if s["models_used"]:
            print(f"  🏷  Models     : {', '.join(s['models_used'])}")
        if s["tools_used"]:
            print(f"  🛠  Tools      : {', '.join(s['tools_used'])}")
        if s["retriever_calls"]:
            print(f"  📚 Retrievers : {s['retriever_calls']}")
        if s["artifacts_count"]:
            print(f"  📦 Artifacts  : {s['artifacts_count']}")
        if s["errors"]:
            print(f"  ❌ Errors     : {len(s['errors'])}")
            for err in s["errors"][:3]:
                print(f"     → {err[:80]}")
        print(f"  📈 Steps      : {s['steps_count']}")
        print("═" * 60 + "\n")


# ─────────────────────────────────────────────────────
# Base Tracer — Manages span lifecycle and persistence
# ─────────────────────────────────────────────────────
class BaseTracer:
    """Framework-agnostic tracer that manages spans and persists to FlowyML.

    All framework-specific integrations (LangGraph, OpenAI, etc.) either
    use or extend this class.

    Usage::

        tracer = BaseTracer(name="my_task", project="demo")
        span = tracer.start_span("llm", "gpt4_call", inputs={"prompt": "Hi"})
        # ... do work ...
        tracer.end_span(span, outputs={"response": "Hello!"})
        tracer.finalize()
        tracer.session.print_summary()
    """

    def __init__(
        self,
        name: str = "genai_session",
        project: str | None = None,
        framework: str | None = None,
        tags: dict[str, str] | None = None,
        session: TraceSession | None = None,
        auto_log: bool = True,
        verbose: bool = False,
    ):
        self.auto_log = auto_log
        self.verbose = verbose

        trace_id = str(uuid.uuid4())
        self.session = session or TraceSession(
            session_id=trace_id,
            name=name,
            project=project,
            framework=framework,
            tags=tags or {},
        )
        self.trace_id = self.session.session_id

        # Span tracking
        self._span_stack: list[TraceSpan] = []
        self._run_to_span: dict[str, TraceSpan] = {}
        self._metadata_store: Any = None
        self._store_init_attempted = False

    @property
    def _store(self):
        """Lazy-load metadata store (only on first actual persist)."""
        if self._metadata_store is None and not self._store_init_attempted:
            self._store_init_attempted = True
            try:
                from flowyml.storage.sql import SQLMetadataStore

                self._metadata_store = SQLMetadataStore()
            except Exception as e:
                logger.debug(f"Metadata store not available: {e}")
        return self._metadata_store

    def start_span(
        self,
        event_type: str,
        name: str,
        *,
        run_id: str | None = None,
        inputs: dict[str, Any] | None = None,
        parent_run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """Create and register a new span."""
        rid = run_id or str(uuid.uuid4())

        parent_id = None
        if parent_run_id and parent_run_id in self._run_to_span:
            parent_id = self._run_to_span[parent_run_id].event_id
        elif self._span_stack:
            parent_id = self._span_stack[-1].event_id

        span = TraceSpan(
            event_id=str(uuid.uuid4()),
            trace_id=self.trace_id,
            parent_id=parent_id,
            event_type=event_type,
            name=name,
            inputs=inputs or {},
            metadata=metadata or {},
        )
        self._run_to_span[rid] = span
        self._span_stack.append(span)

        if self.verbose:
            logger.info(f"[FlowyML] ▶ {event_type}:{name} started")

        return span

    def end_span(
        self,
        span_or_run_id: TraceSpan | str,
        *,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TraceSpan | None:
        """Finalize and persist a span."""
        # Resolve span from run_id
        if isinstance(span_or_run_id, str):
            span = self._run_to_span.pop(span_or_run_id, None)
        else:
            span = span_or_run_id
            # Remove from run_to_span by value
            for rid, s in list(self._run_to_span.items()):
                if s is span:
                    del self._run_to_span[rid]
                    break

        if span is None:
            return None

        span.end(outputs=outputs, error=error)

        # Remove from stack
        if span in self._span_stack:
            self._span_stack.remove(span)

        # Record in session
        self.session.record_step(span)

        # Persist
        if self.auto_log:
            self._persist_span(span)

        if self.verbose:
            icon = "✅" if span.status == "success" else "❌"
            logger.info(
                f"[FlowyML] {icon} {span.event_type}:{span.name} "
                f"({span.duration:.3f}s, {span.total_tokens} tokens)",
            )

        return span

    def save_artifact(
        self,
        name: str,
        artifact_type: str,
        content: Any,
        *,
        span: TraceSpan | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save an artifact to FlowyML (prompt, response, document, etc.).

        Artifacts are first-class citizens stored alongside trace data.
        They can be attached to a specific span or to the session.

        Args:
            name: Artifact name (e.g. "system_prompt", "rag_documents").
            artifact_type: Category — "prompt", "response", "document",
                "embedding", "image", "config", "intermediate", "code".
            content: The artifact content.
            span: Optional span to attach the artifact to.
            metadata: Optional metadata.

        Returns:
            The artifact dict.
        """
        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "trace_id": self.trace_id,
            "span_id": span.event_id if span else None,
            "name": name,
            "type": artifact_type,
            "content": safe_serialize(content, max_len=50000),
            "metadata": metadata or {},
            "timestamp": time.time(),
            "project": self.session.project,
        }
        self.session.artifacts.append(artifact)
        if span:
            span.artifacts.append(artifact)

        # Persist to storage
        if self.auto_log:
            store = self._store
            if store is not None:
                try:
                    store.save_artifact(
                        run_id=self.trace_id,
                        name=name,
                        artifact_type=artifact_type,
                        data=safe_serialize(content, max_len=50000),
                        metadata={
                            **artifact,
                            "framework": self.session.framework,
                        },
                    )
                except Exception as e:
                    logger.debug(f"Artifact storage: {e}")

        return artifact

    def _persist_span(self, span: TraceSpan) -> None:
        """Save span to FlowyML storage."""
        store = self._store
        if store is None:
            return
        try:
            event_dict = span.to_event_dict()
            if self.session.project:
                event_dict["project"] = self.session.project
            store.save_trace_event(event_dict)
        except Exception as e:
            logger.warning(f"Failed to save trace event: {e}")

    def finalize(self) -> None:
        """Finalize the session and persist session-level data."""
        self.session.end_time = time.time()

        if not self.auto_log:
            return

        store = self._store
        if store is None:
            return

        # Save session-level trace event
        try:
            store.save_trace_event(
                {
                    "event_id": self.session.session_id,
                    "trace_id": self.session.session_id,
                    "parent_id": None,
                    "event_type": "session",
                    "name": self.session.name,
                    "inputs": {"tags": self.session.tags},
                    "outputs": self.session.summary(),
                    "start_time": self.session.start_time,
                    "end_time": self.session.end_time,
                    "duration": self.session.duration,
                    "status": "error" if self.session.errors else "success",
                    "error": ("; ".join(self.session.errors) if self.session.errors else None),
                    "metadata": {
                        "framework": self.session.framework or "generic",
                        "type": "session",
                    },
                    "prompt_tokens": self.session.total_prompt_tokens,
                    "completion_tokens": self.session.total_completion_tokens,
                    "total_tokens": self.session.total_tokens,
                    "cost": self.session.total_cost,
                    "model": (", ".join(self.session.models_used) if self.session.models_used else None),
                    "project": self.session.project,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to save session event: {e}")

        # Save as a FlowyML run for UI visibility
        try:
            fw = self.session.framework or "genai"
            store.save_run(
                run_id=self.session.session_id,
                metadata={
                    "pipeline_name": f"{fw}:{self.session.name}",
                    "status": ("failed" if self.session.errors else "completed"),
                    "duration": self.session.duration,
                    "started_at": datetime.fromtimestamp(
                        self.session.start_time,
                    ).isoformat(),
                    "ended_at": (
                        datetime.fromtimestamp(
                            self.session.end_time,
                        ).isoformat()
                        if self.session.end_time
                        else None
                    ),
                    "tags": {
                        **self.session.tags,
                        "framework": fw,
                    },
                    "genai_metrics": {
                        "llm_calls": self.session.total_llm_calls,
                        "tool_calls": self.session.total_tool_calls,
                        "embedding_calls": self.session.total_embedding_calls,
                        "retriever_calls": self.session.total_retriever_calls,
                        "total_tokens": self.session.total_tokens,
                        "prompt_tokens": self.session.total_prompt_tokens,
                        "completion_tokens": self.session.total_completion_tokens,
                        "estimated_cost_usd": self.session.total_cost,
                        "models_used": self.session.models_used,
                        "tools_used": self.session.tools_used,
                        "artifacts_count": len(self.session.artifacts),
                    },
                    "steps": {
                        step["name"]: {
                            "event_id": step.get("event_id"),
                            "parent_id": step.get("parent_id"),
                            "status": step["status"],
                            "duration_seconds": step["duration"],
                            "tokens": step.get("tokens", 0),
                            "type": step.get("type"),
                            "model": step.get("model"),
                        }
                        for step in self.session.steps
                    },
                    "canvas_graph": self.session.to_canvas_graph(),
                    "artifacts": [
                        {
                            "artifact_id": a["artifact_id"],
                            "name": a["name"],
                            "type": a["type"],
                            "span_id": a.get("span_id"),
                        }
                        for a in self.session.artifacts
                    ],
                    "project": self.session.project,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to save run metadata: {e}")


# ─────────────────────────────────────────────────────
# High-Level API: trace() context manager
# ─────────────────────────────────────────────────────
@contextlib.contextmanager
def trace(
    name: str = "genai_session",
    *,
    project: str | None = None,
    framework: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Context manager for tracing any GenAI code.

    Yields a :class:`BaseTracer` whose ``.session`` contains
    aggregated metrics after the block completes.

    Example::

        with trace("my_task", project="demo") as tracer:
            span = tracer.start_span("llm", "gpt4_call")
            result = call_llm(...)
            span.set_tokens(prompt_tokens=10, completion_tokens=20, model="gpt-4o")
            tracer.end_span(span, outputs={"response": result})
    """
    tracer = BaseTracer(
        name=name,
        project=project,
        framework=framework,
        tags=tags,
        auto_log=auto_log,
        verbose=verbose,
    )

    try:
        yield tracer
    except Exception as e:
        tracer.session.errors.append(str(e))
        raise
    finally:
        tracer.finalize()
        if print_summary:
            tracer.session.print_summary()


# ─────────────────────────────────────────────────────
# High-Level API: observe() decorator
# ─────────────────────────────────────────────────────
def observe(
    name: str | None = None,
    *,
    project: str | None = None,
    framework: str | None = None,
    tags: dict[str, str] | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Decorator for automatic observability on any function.

    Injects a ``flowyml_session`` keyword argument with the active
    :class:`TraceSession` if the function signature accepts it.

    Example::

        @observe(name="summarize", project="demo")
        def summarize(text: str, flowyml_session=None):
            # flowyml_session.session contains the TraceSession
            span = flowyml_session.start_span("llm", "summarize_call")
            result = call_llm(text)
            span.set_tokens(prompt_tokens=50, completion_tokens=100, model="gpt-4o")
            flowyml_session.end_span(span, outputs={"result": result})
            return result
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            session_name = name or func.__name__
            with trace(
                session_name,
                project=project,
                framework=framework,
                tags=tags,
                auto_log=auto_log,
                verbose=verbose,
                print_summary=print_summary,
            ) as tracer:
                sig = inspect.signature(func)
                if "flowyml_session" in sig.parameters:
                    kwargs["flowyml_session"] = tracer
                return func(*args, **kwargs)

        return wrapper

    return decorator


# ─────────────────────────────────────────────────────
# Convenience: Manual logging functions
# ─────────────────────────────────────────────────────
_global_tracer: BaseTracer | None = None


def get_current_tracer() -> BaseTracer | None:
    """Get the current active tracer (if any)."""
    return _global_tracer


def log_llm_call(
    *,
    model: str,
    prompt: str | dict | list,
    response: str | dict,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    name: str = "llm_call",
    project: str | None = None,
    tracer: BaseTracer | None = None,
) -> TraceSpan:
    """Log a single LLM call to FlowyML.

    Can be used standalone or within a trace() context.

    Example::

        log_llm_call(
            model="gpt-4o",
            prompt="Summarize this text",
            response="Here's the summary...",
            prompt_tokens=50,
            completion_tokens=100,
        )
    """
    t = (
        tracer
        or _global_tracer
        or BaseTracer(
            name=name,
            project=project,
            framework="manual",
        )
    )
    span = t.start_span(
        "llm",
        name,
        inputs={"prompt": safe_serialize(prompt)},
    )
    span.set_tokens(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
    )
    t.session.total_llm_calls += 1
    t.session.add_model(model)
    t.session.record_tokens(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=span.cost,
    )
    t.end_span(span, outputs={"response": safe_serialize(response)})

    if tracer is None and _global_tracer is None:
        t.finalize()

    return span


def log_tool_call(
    *,
    name: str,
    tool_input: str | dict,
    tool_output: str | dict,
    duration: float | None = None,
    tracer: BaseTracer | None = None,
    project: str | None = None,
) -> TraceSpan:
    """Log a single tool call to FlowyML.

    Example::

        log_tool_call(
            name="web_search",
            tool_input="latest AI news",
            tool_output="Results: ...",
        )
    """
    t = (
        tracer
        or _global_tracer
        or BaseTracer(
            name=name,
            project=project,
            framework="manual",
        )
    )
    span = t.start_span(
        "tool",
        name,
        inputs={"tool_input": safe_serialize(tool_input)},
    )
    span.tool_name = name
    span.tool_input = safe_serialize(tool_input)
    span.tool_output = safe_serialize(tool_output)
    t.session.total_tool_calls += 1
    t.session.add_tool(name)
    t.end_span(
        span,
        outputs={"tool_output": safe_serialize(tool_output)},
    )

    if tracer is None and _global_tracer is None:
        t.finalize()

    return span


def log_embedding_call(
    *,
    model: str,
    input_text: str | list[str],
    dimensions: int | None = None,
    token_count: int = 0,
    name: str = "embedding",
    tracer: BaseTracer | None = None,
    project: str | None = None,
) -> TraceSpan:
    """Log an embedding call to FlowyML.

    Example::

        log_embedding_call(
            model="text-embedding-3-small",
            input_text="Hello world",
            token_count=2,
        )
    """
    t = (
        tracer
        or _global_tracer
        or BaseTracer(
            name=name,
            project=project,
            framework="manual",
        )
    )
    texts = input_text if isinstance(input_text, list) else [input_text]
    span = t.start_span(
        "embedding",
        name,
        inputs={
            "texts": [safe_serialize(txt, max_len=500) for txt in texts[:5]],
            "count": len(texts),
        },
        metadata={"dimensions": dimensions} if dimensions else {},
    )
    span.set_tokens(prompt_tokens=token_count, model=model)
    t.session.total_embedding_calls += 1
    t.session.add_model(model)
    t.session.record_tokens(prompt_tokens=token_count, cost=span.cost)
    t.end_span(span, outputs={"dimensions": dimensions, "count": len(texts)})

    if tracer is None and _global_tracer is None:
        t.finalize()

    return span


# ─────────────────────────────────────────────────────
# GenAI Session Layer — Multi-Turn / Thread Aggregation
# ─────────────────────────────────────────────────────


@dataclass
class Turn:
    """A single user↔assistant interaction within a GenAI session.

    Instead of logging every prompt/response as separate spans, a Turn
    aggregates all spans from one exchange into a single unit with
    session-level metrics.  Eval results are attached per-turn so
    quality can be tracked across the entire conversation.
    """

    turn_id: str
    session_id: str
    turn_index: int
    role: str = "user"  # user, assistant, system, tool
    content: str = ""  # Aggregated content for the turn
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str | None = None
    latency: float = 0.0  # Wall-clock seconds
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    eval_results: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    spans: list[TraceSpan] = field(default_factory=list)
    error: str | None = None
    status: str = "running"  # running, success, error

    # ── computed ────────────────────────────────────

    def end(
        self,
        *,
        content: str | None = None,
        error: str | None = None,
    ) -> None:
        """Finalize this turn."""
        if content is not None:
            self.content = content
        self.latency = time.time() - self.timestamp
        if error:
            self.status = "error"
            self.error = str(error)
        else:
            self.status = "success"

        # Aggregate from constituent spans
        for span in self.spans:
            self.input_tokens += span.prompt_tokens
            self.output_tokens += span.completion_tokens
            self.total_tokens += span.total_tokens
            self.cost += span.cost
            if span.model and not self.model:
                self.model = span.model
            if span.tool_name:
                self.tool_calls.append(
                    {
                        "name": span.tool_name,
                        "input": span.tool_input,
                        "output": span.tool_output,
                    },
                )
            self.artifacts.extend(span.artifacts)

    def add_eval(
        self,
        scorer_name: str,
        score: float,
        *,
        passed: bool | None = None,
        rationale: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Attach an evaluation result to this turn."""
        result = {
            "scorer": scorer_name,
            "score": score,
            "passed": passed,
            "rationale": rationale,
            "metadata": metadata or {},
            "turn_id": self.turn_id,
            "timestamp": time.time(),
        }
        self.eval_results.append(result)
        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage / API."""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "turn_index": self.turn_index,
            "role": self.role,
            "content": self.content[:5000] if self.content else "",
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost": round(self.cost, 6),
            "model": self.model,
            "latency": round(self.latency, 4),
            "tool_calls": self.tool_calls,
            "eval_results": self.eval_results,
            "artifacts_count": len(self.artifacts),
            "status": self.status,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class GenAISession:
    """Long-lived observability session for GenAI applications.

    Designed for chatbots, multi-turn agents, and interactive AI apps
    where logging each prompt/response individually is wasteful.  Instead,
    turns are aggregated at the session (thread) level with running totals,
    automatic eval hooks, and experiment-ready metrics.
    """

    session_id: str
    name: str
    project: str | None = None
    thread_id: str | None = None  # Chatbot thread / conversation ID
    user_id: str | None = None  # End-user identifier
    framework: str | None = None
    tags: dict[str, str] = field(default_factory=dict)

    # Turn storage
    turns: list[Turn] = field(default_factory=list)

    # ── session-level aggregated metrics (updated per turn) ──
    total_turns: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency: float = 0.0
    models_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    eval_scores: dict[str, list[float]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    # Lifecycle
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: str = "active"  # active, completed, errored

    # ── Event stream (optional real-time callbacks) ──
    _event_callbacks: list[Any] = field(default_factory=list, repr=False)
    # ── Evaluator (optional auto-eval on each turn) ──
    _evaluator: Any | None = field(default=None, repr=False)

    # ── core methods ────────────────────────────────

    @property
    def duration(self) -> float:
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def record_turn(self, turn: Turn) -> None:
        """Record a completed turn and update aggregates."""
        self.turns.append(turn)
        self.total_turns += 1
        self.total_input_tokens += turn.input_tokens
        self.total_output_tokens += turn.output_tokens
        self.total_tokens += turn.total_tokens
        self.total_cost += turn.cost
        self.total_latency += turn.latency

        if turn.model and turn.model not in self.models_used:
            self.models_used.append(turn.model)
        for tc in turn.tool_calls:
            name = tc.get("name", "")
            if name and name not in self.tools_used:
                self.tools_used.append(name)

        if turn.error:
            self.errors.append(
                f"[turn:{turn.turn_index}] {turn.error[:200]}",
            )

        self.artifacts.extend(turn.artifacts)

        # Record eval scores at session level
        for ev in turn.eval_results:
            scorer = ev.get("scorer", "unknown")
            score_val = ev.get("score")
            if score_val is not None:
                self.eval_scores.setdefault(scorer, []).append(float(score_val))

        # Fire event callbacks
        for cb in self._event_callbacks:
            with contextlib.suppress(Exception):
                cb("turn_end", turn.to_dict())

        # Auto-eval if evaluator is attached
        if self._evaluator is not None:
            try:
                self._evaluator.evaluate_turn(turn)
            except Exception as e:
                logger.debug(f"Auto-eval failed: {e}")

    def add_eval(
        self,
        scorer_name: str,
        score: float,
        *,
        turn: Turn | None = None,
        passed: bool | None = None,
        rationale: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an eval result, optionally attached to a specific turn."""
        target = turn or (self.turns[-1] if self.turns else None)
        result = {
            "scorer": scorer_name,
            "score": score,
            "passed": passed,
            "rationale": rationale,
            "metadata": metadata or {},
            "turn_id": target.turn_id if target else None,
            "timestamp": time.time(),
        }
        if target:
            target.eval_results.append(result)
        self.eval_scores.setdefault(scorer_name, []).append(float(score))

        # Fire eval event
        for cb in self._event_callbacks:
            with contextlib.suppress(Exception):
                cb("eval_complete", result)
        return result

    def attach_evaluator(self, evaluator: Any) -> None:
        """Attach an evaluator for automatic per-turn scoring."""
        self._evaluator = evaluator

    def on_event(self, callback) -> None:
        """Register an event callback for real-time streaming."""
        self._event_callbacks.append(callback)

    # ── reporting ───────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Session-level aggregated summary."""
        avg_evals = {}
        for scorer, scores in self.eval_scores.items():
            if scores:
                avg_evals[scorer] = {
                    "mean": round(sum(scores) / len(scores), 4),
                    "min": round(min(scores), 4),
                    "max": round(max(scores), 4),
                    "count": len(scores),
                }
        return {
            "session_id": self.session_id,
            "name": self.name,
            "project": self.project,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "framework": self.framework,
            "status": self.status,
            "duration_seconds": round(self.duration, 3),
            "total_turns": self.total_turns,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.total_cost, 6),
            "avg_latency_seconds": (round(self.total_latency / self.total_turns, 3) if self.total_turns > 0 else 0),
            "models_used": list(set(self.models_used)),
            "tools_used": list(set(self.tools_used)),
            "eval_scores": avg_evals,
            "artifacts_count": len(self.artifacts),
            "errors": self.errors,
        }

    def to_experiment_metrics(self) -> dict[str, float]:
        """Convert to flat metrics dict for experiment tracking."""
        metrics: dict[str, float] = {
            "total_turns": float(self.total_turns),
            "total_tokens": float(self.total_tokens),
            "total_cost_usd": self.total_cost,
            "avg_latency_s": (self.total_latency / self.total_turns if self.total_turns > 0 else 0),
        }
        for scorer, scores in self.eval_scores.items():
            if scores:
                metrics[f"eval_{scorer}_mean"] = sum(scores) / len(scores)
        return metrics

    def print_summary(self) -> None:
        """Pretty-print the session summary."""
        s = self.summary()
        fw = f" ({s['framework']})" if s["framework"] else ""
        print("\n" + "═" * 60)
        print(f"  🧠 FlowyML GenAI Session — {s['name']}{fw}")
        print("═" * 60)
        print(f"  📋 Session    : {s['session_id'][:12]}...")
        if s["project"]:
            print(f"  📂 Project    : {s['project']}")
        if s["thread_id"]:
            print(f"  🧵 Thread     : {s['thread_id'][:12]}...")
        if s["user_id"]:
            print(f"  👤 User       : {s['user_id']}")
        print(f"  ⏱  Duration   : {s['duration_seconds']:.2f}s")
        print(f"  💬 Turns      : {s['total_turns']}")
        print(
            f"  📊 Tokens     : {s['total_tokens']:,} "
            f"(in: {s['total_input_tokens']:,} / "
            f"out: {s['total_output_tokens']:,})",
        )
        print(f"  💰 Est. Cost  : ${s['estimated_cost_usd']:.4f}")
        if s["avg_latency_seconds"]:
            print(f"  ⚡ Avg Latency: {s['avg_latency_seconds']:.2f}s/turn")
        if s["models_used"]:
            print(f"  🏷  Models     : {', '.join(s['models_used'])}")
        if s["tools_used"]:
            print(f"  🛠  Tools      : {', '.join(s['tools_used'])}")
        if s["eval_scores"]:
            print("  📈 Eval Scores:")
            for scorer, stats in s["eval_scores"].items():
                print(
                    f"     {scorer}: mean={stats['mean']:.2f} "
                    f"(min={stats['min']:.2f}, max={stats['max']:.2f}, "
                    f"n={stats['count']})",
                )
        if s["artifacts_count"]:
            print(f"  📦 Artifacts  : {s['artifacts_count']}")
        if s["errors"]:
            print(f"  ❌ Errors     : {len(s['errors'])}")
            for err in s["errors"][:3]:
                print(f"     → {err[:80]}")
        print("═" * 60 + "\n")


class SessionTracer(BaseTracer):
    """Manages a GenAISession across multiple turns.

    Extends :class:`BaseTracer` to support multi-turn sessions
    (chatbots, agents, interactive apps).  Each ``turn()`` context
    manager groups spans into a single :class:`Turn` and records
    it in the parent :class:`GenAISession`.

    Usage::

        tracer = SessionTracer("chatbot", project="support")
        with tracer.turn("user") as turn:
            # spans created via tracer.start_span() go into this turn
            span = tracer.start_span("llm", "gpt4_call")
            result = call_llm(...)
            tracer.end_span(span, outputs={"response": result})
            turn.content = result
        tracer.end_session()
        tracer.genai_session.print_summary()
    """

    def __init__(
        self,
        name: str = "genai_session",
        *,
        project: str | None = None,
        framework: str | None = None,
        thread_id: str | None = None,
        user_id: str | None = None,
        tags: dict[str, str] | None = None,
        evaluator: Any | None = None,
        auto_log: bool = True,
        verbose: bool = False,
    ):
        super().__init__(
            name=name,
            project=project,
            framework=framework,
            tags=tags,
            auto_log=auto_log,
            verbose=verbose,
        )
        self.genai_session = GenAISession(
            session_id=self.trace_id,
            name=name,
            project=project,
            thread_id=thread_id or str(uuid.uuid4()),
            user_id=user_id,
            framework=framework,
            tags=tags or {},
        )
        if evaluator is not None:
            self.genai_session.attach_evaluator(evaluator)

        self._current_turn: Turn | None = None
        self._turn_counter = 0

    # ── Turn lifecycle ──────────────────────────────

    def start_turn(self, role: str = "user", content: str = "") -> Turn:
        """Begin a new turn."""
        self._turn_counter += 1
        turn = Turn(
            turn_id=str(uuid.uuid4()),
            session_id=self.genai_session.session_id,
            turn_index=self._turn_counter,
            role=role,
            content=content,
        )
        self._current_turn = turn

        # Fire event
        for cb in self.genai_session._event_callbacks:
            with contextlib.suppress(Exception):
                cb("turn_start", {"turn_id": turn.turn_id, "role": role})

        return turn

    def end_turn(
        self,
        *,
        content: str | None = None,
        error: str | None = None,
    ) -> Turn | None:
        """Finalize the current turn and record it."""
        turn = self._current_turn
        if turn is None:
            return None

        turn.end(content=content, error=error)
        self.genai_session.record_turn(turn)
        self._current_turn = None
        return turn

    @contextlib.contextmanager
    def turn(self, role: str = "user", content: str = ""):
        """Context manager for a single turn.

        Usage::

            with tracer.turn("user") as t:
                t.content = "Hello!"
                span = tracer.start_span("llm", "reply")
                # ... do work ...
                tracer.end_span(span)
        """
        t = self.start_turn(role=role, content=content)
        try:
            yield t
        except Exception as e:
            self.end_turn(error=str(e))
            raise
        else:
            self.end_turn(content=t.content)

    # ── Override span tracking to capture into current turn ──

    def end_span(
        self,
        span_or_run_id: TraceSpan | str,
        *,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TraceSpan | None:
        """Finalize span and attach to current turn if active."""
        span = super().end_span(
            span_or_run_id,
            outputs=outputs,
            error=error,
        )
        if span is not None and self._current_turn is not None:
            self._current_turn.spans.append(span)
        return span

    # ── Session lifecycle ───────────────────────────

    def end_session(self) -> GenAISession:
        """Finalize the session."""
        self.genai_session.end_time = time.time()
        self.genai_session.status = "errored" if self.genai_session.errors else "completed"

        # Persist session data
        if self.auto_log:
            self._persist_session()

        return self.genai_session

    def _persist_session(self) -> None:
        """Save session, turns, and evals to storage."""
        store = self._store
        if store is None:
            return

        fw = self.genai_session.framework or "genai"
        session_summary = self.genai_session.summary()

        # Save as a FlowyML run for UI visibility
        try:
            store.save_run(
                run_id=self.genai_session.session_id,
                metadata={
                    "pipeline_name": f"{fw}:session:{self.genai_session.name}",
                    "status": self.genai_session.status,
                    "duration": self.genai_session.duration,
                    "started_at": datetime.fromtimestamp(
                        self.genai_session.start_time,
                    ).isoformat(),
                    "ended_at": (
                        datetime.fromtimestamp(
                            self.genai_session.end_time,
                        ).isoformat()
                        if self.genai_session.end_time
                        else None
                    ),
                    "tags": {
                        **self.genai_session.tags,
                        "framework": fw,
                        "type": "genai_session",
                    },
                    "genai_session": session_summary,
                    "turns": [t.to_dict() for t in self.genai_session.turns],
                    "project": self.genai_session.project,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to save session run: {e}")

        # Save session-level trace event
        try:
            store.save_trace_event(
                {
                    "event_id": self.genai_session.session_id,
                    "trace_id": self.genai_session.session_id,
                    "parent_id": None,
                    "event_type": "genai_session",
                    "name": self.genai_session.name,
                    "inputs": {"tags": self.genai_session.tags},
                    "outputs": session_summary,
                    "start_time": self.genai_session.start_time,
                    "end_time": self.genai_session.end_time,
                    "duration": self.genai_session.duration,
                    "status": self.genai_session.status,
                    "error": ("; ".join(self.genai_session.errors) if self.genai_session.errors else None),
                    "metadata": {
                        "framework": fw,
                        "type": "genai_session",
                        "thread_id": self.genai_session.thread_id,
                        "user_id": self.genai_session.user_id,
                    },
                    "prompt_tokens": self.genai_session.total_input_tokens,
                    "completion_tokens": self.genai_session.total_output_tokens,
                    "total_tokens": self.genai_session.total_tokens,
                    "cost": self.genai_session.total_cost,
                    "model": (", ".join(self.genai_session.models_used) if self.genai_session.models_used else None),
                    "project": self.genai_session.project,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to save session event: {e}")

    def finalize(self) -> None:
        """Override finalize to also end the GenAI session."""
        super().finalize()
        if self.genai_session.status == "active":
            self.end_session()


# ─────────────────────────────────────────────────────
# High-Level API: session_trace() context manager
# ─────────────────────────────────────────────────────
@contextlib.contextmanager
def session_trace(
    name: str = "genai_session",
    *,
    project: str | None = None,
    framework: str | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
    tags: dict[str, str] | None = None,
    evaluator: Any | None = None,
    auto_log: bool = True,
    verbose: bool = False,
    print_summary: bool = True,
):
    """Context manager for multi-turn GenAI session tracing.

    Yields a :class:`SessionTracer` whose ``.genai_session`` contains
    aggregated metrics across all turns.

    Example::

        with session_trace("chatbot", project="support") as tracer:
            with tracer.turn("user") as t:
                t.content = "What is AI?"
                span = tracer.start_span("llm", "reply")
                response = call_llm("What is AI?")
                span.set_tokens(prompt_tokens=10, completion_tokens=50, model="gpt-4o-mini")
                tracer.end_span(span, outputs={"response": response})
                t.content = response

            with tracer.turn("user") as t:
                t.content = "Tell me more"
                # ... more LLM calls ...
    """
    tracer = SessionTracer(
        name=name,
        project=project,
        framework=framework,
        thread_id=thread_id,
        user_id=user_id,
        tags=tags,
        evaluator=evaluator,
        auto_log=auto_log,
        verbose=verbose,
    )
    try:
        yield tracer
    except Exception as e:
        tracer.genai_session.errors.append(str(e))
        raise
    finally:
        tracer.end_session()
        if print_summary:
            tracer.genai_session.print_summary()

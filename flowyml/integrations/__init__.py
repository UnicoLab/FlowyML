"""flowyml Integrations — GenAI Observability for any framework.

Available integrations:
    - base:               Framework-agnostic core (trace, observe, log_*)
    - langgraph:          LangGraph agents
    - langchain:          LangChain chains/runnables
    - openai_integration: Native OpenAI SDK
    - generic:            Any framework (CrewAI, AutoGen, custom)
    - keras:              Keras training callback

Session-level (GenAI-first):
    - session_trace:      Multi-turn session tracing
    - GenAISession:       Long-lived session container
    - Turn:               Single interaction within a session
    - SessionTracer:      Session lifecycle manager
    - SessionEvaluator:   Auto-eval on each turn
    - SessionEventStream: Real-time event streaming
"""

# ─── Framework-agnostic core (always available) ─────

# ─── Eval bridge (always available) ────────────────

# ─── Streaming (always available) ──────────────────

import contextlib

# ─── Framework-agnostic core (always available) ─────

# ─── Eval bridge (always available) ────────────────

# ─── Streaming (always available) ──────────────────

# ─── LangGraph / LangChain (optional) ──────────────
with contextlib.suppress(ImportError):
    from flowyml.integrations.langgraph import (
        FlowyMLCallbackHandler,
        instrument,
        observe as observe_graph,
        trace_graph,
    )

with contextlib.suppress(ImportError):
    from flowyml.integrations.langchain import (
        instrument_chain,
        observe_chain,
        trace_chain,
    )

# ─── OpenAI (optional) ─────────────────────────────
with contextlib.suppress(ImportError):
    from flowyml.integrations.openai_integration import (
        TracedOpenAI,
        patch_openai,
        trace_openai,
    )

# ─── Generic (always available) ────────────────────

# ─── Keras (optional) ──────────────────────────────
with contextlib.suppress(ImportError):
    from flowyml.integrations.keras import FlowymlKerasCallback

__all__ = [
    "FlowyMLCallbackHandler",
    "instrument",
    "observe_graph",
    "trace_graph",
    "instrument_chain",
    "observe_chain",
    "trace_chain",
    "TracedOpenAI",
    "patch_openai",
    "trace_openai",
    "FlowymlKerasCallback",
]

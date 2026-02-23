# 🔗 FlowyML GenAI Observability — Implementation Plan

## Vision

Provide a **universal, framework-agnostic GenAI observability layer** that lets users
add full tracing, logging, token tracking, cost estimation, and FlowyML integration
to *any* GenAI application with minimal code changes. The mantra:
**"Import, decorate, done."**

---

## Architecture Overview

```
flowyml/integrations/
├── __init__.py           # Central exports + convenience imports
├── base.py               # 🆕 Framework-agnostic core (TraceSpan, TraceSession, GenAITracer)
├── langgraph.py          # ✅ EXISTS — Refactor to inherit from base
├── langchain.py          # 🆕 Pure LangChain integration (non-graph)
├── openai_integration.py # 🆕 Native OpenAI/Azure OpenAI wrapper
├── generic.py            # 🆕 Generic wrapper for ANY framework (CrewAI, AutoGen, etc.)
└── keras.py              # ✅ EXISTS — Untouched
```

### Dependency Hierarchy
```
base.py ← Core (no external deps, pure Python + flowyml.storage)
  ├── langgraph.py ← requires: langchain-core (optional)
  ├── langchain.py ← requires: langchain-core (optional)
  ├── openai_integration.py ← requires: openai (optional)
  └── generic.py ← no external deps (wraps any callable)
```

---

## Task Breakdown

### Task 1: Extract Shared Foundation → `base.py` ✂️
**What**: Move `TraceSpan`, `TraceSession`, `_safe_serialize`, `_MODEL_COSTS`,
`_estimate_cost`, and the metadata store integration out of `langgraph.py`
into a new `base.py` module so ALL integrations share the same data model.

**Key Classes/Functions to extract**:
- `TraceSpan` — The span dataclass
- `TraceSession` — Session aggregator (remove `config` property — that's LangChain-specific)
- `_safe_serialize()` — Safe JSON serialization helper
- `_MODEL_COSTS` + `_estimate_cost()` — Cost estimation engine
- `BaseTracer` — New class that handles span lifecycle + metadata store persistence
- `trace()` — Generic context manager (framework-agnostic version of `trace_graph`)
- `observe()` — Generic decorator (injects `flowyml_session` kwarg)

**Outcome**: `langgraph.py` becomes thin — it only contains `FlowyMLCallbackHandler`
(LangChain callback protocol) and the `instrument()` function. Everything else
is imported from `base.py`.

---

### Task 2: LangChain Integration → `langchain.py` 🔗
**What**: Dedicated LangChain integration for non-graph usage (chains, runnables,
retrievers, agents without LangGraph).

**Key APIs**:
- `FlowyMLCallbackHandler` — Re-exported from `langgraph.py` (same handler works)
- `trace_chain(name, project)` — Context manager optimized for chain tracing
- `@observe_chain()` — Decorator for LangChain chain functions
- `instrument_chain(chain)` — Wrap a LangChain Runnable permanently

**Note**: The `FlowyMLCallbackHandler` already covers LangChain callbacks. This
module mainly provides convenience wrappers and explicit LangChain-branded imports
so users searching for "flowyml langchain" find the right thing.

---

### Task 3: OpenAI Native Integration → `openai_integration.py` 🤖
**What**: Direct wrapper for the `openai` Python SDK without requiring LangChain.
Many users use OpenAI directly — they should get full FlowyML observability too.

**Key APIs**:
- `@trace_openai()` — Decorator that wraps OpenAI client methods
- `patch_openai(client)` — Monkey-patch an existing OpenAI client for auto-tracing
- `TracedOpenAI(...)` — Drop-in replacement for `openai.OpenAI()` with auto-tracing

**What Gets Tracked**:
- `client.chat.completions.create()` — Full request/response
- `client.embeddings.create()` — Embedding calls
- Token usage from the response's `usage` field
- Cost estimation using `_MODEL_COSTS`
- Streaming support (aggregates tokens at stream end)

---

### Task 4: Generic Framework Integration → `generic.py` 🌐
**What**: A framework-agnostic wrapper that works with ANY GenAI code — no LangChain
or OpenAI needed. This is the "universal adapter".

**Key APIs**:
- `@observe(name, project)` — Decorator (re-exported from base, works standalone)
- `trace(name, project)` — Context manager (re-exported from base)
- `span(name, type)` — Manual span creation for custom instrumentation
- `log_llm_call(model, prompt, response, tokens)` — Manual LLM call logging
- `log_tool_call(name, input, output)` — Manual tool call logging

**Example (CrewAI)**:
```python
from flowyml.integrations.generic import observe, span, log_llm_call

@observe(name="research_crew", project="my_project")
def run_crew(topic: str, flowyml_session=None):
    crew = Crew(agents=[...], tasks=[...])
    result = crew.kickoff(inputs={"topic": topic})
    # Optionally log manually
    log_llm_call(model="gpt-4o", prompt=topic, response=str(result), tokens={"total": 500})
    return result
```

---

### Task 5: Update `langgraph.py` to use `base.py` 🔄
**What**: Refactor the existing `langgraph.py` to import everything from `base.py`
instead of defining its own copies.

**Changes**:
- Import `TraceSpan`, `TraceSession`, `_safe_serialize`, `_estimate_cost` from `base`
- Keep `FlowyMLCallbackHandler` (adds LangChain callback methods)
- Keep `instrument()` (LangGraph-specific graph wrapping)
- `trace_graph()` → Thin wrapper around `base.trace()` that sets `framework="langgraph"`
- `observe()` → Re-export from `base.observe()` with langgraph preset

---

### Task 6: Optional Dependencies in `pyproject.toml` 📦
**What**: Add proper optional extras for the integration dependencies.

**New extras**:
```toml
langchain = ["langchain-core>=0.2.0"]
langgraph = ["langgraph>=0.2.0", "langchain-core>=0.2.0"]
openai = ["openai>=1.0.0"]
genai = ["langchain-core>=0.2.0", "langgraph>=0.2.0", "openai>=1.0.0"]
```

**Update `all` extra** to include `genai` deps.

---

### Task 7: Update Package Exports (`__init__.py`) 📤
**What**: Wire up all new integrations into the main package with lazy loading.

**New top-level exports**:
```python
from flowyml import (
    # Already exported
    FlowyMLCallbackHandler, TraceSession, trace_graph, observe, instrument_graph,
    # New generic
    trace, span, log_llm_call, log_tool_call,
    # New OpenAI
    TracedOpenAI, patch_openai, trace_openai,
)
```

All wrapped in `try/except ImportError` for optional deps.

---

### Task 8: Comprehensive Tests → `tests/test_genai_integrations.py` 🧪
**What**: Full test suite covering all integrations without requiring API keys.

**Test Categories**:
1. **Base Layer Tests** (no external deps):
   - TraceSpan creation, end, to_event_dict
   - TraceSession aggregation and summary
   - Cost estimation for known models
   - `trace()` context manager lifecycle
   - `observe()` decorator injection
   - `_safe_serialize` edge cases

2. **LangGraph/LangChain Handler Tests** (mocked):
   - `on_chat_model_start` / `on_llm_end` flow
   - Token extraction from various response formats
   - Tool call tracking
   - Error propagation
   - Parent/child span relationships
   - Session metrics aggregation

3. **OpenAI Integration Tests** (mocked):
   - `@trace_openai` decorator
   - `patch_openai()` monkey-patching
   - Token/cost extraction from OpenAI responses

4. **Generic Integration Tests**:
   - Manual `span()` creation
   - `log_llm_call()` / `log_tool_call()`
   - Cross-framework session sharing

5. **Storage Integration Tests**:
   - Trace events saved to SQLMetadataStore
   - Runs saved for UI visibility
   - Trace retrieval via `get_trace()`

---

### Task 9: Documentation → `docs/integrations/genai-observability.md` 📚
**What**: Comprehensive tutorial-style documentation.

**Sections**:
1. Overview & Quick Start (30 seconds to first trace)
2. LangGraph Integration (detailed guide)
3. LangChain Integration (detailed guide)
4. OpenAI Integration (detailed guide)
5. Generic / Framework-Agnostic (CrewAI, AutoGen, custom)
6. What Gets Tracked (full telemetry spec)
7. Viewing Traces in FlowyML UI
8. Cost Estimation & Token Tracking
9. Advanced: Custom Spans & Manual Instrumentation
10. Configuration Reference

---

### Task 10: Examples 📝
**What**: Multiple runnable example files.

**Files**:
- `examples/langgraph_observability.py` ✅ EXISTS — Update to use base imports
- `examples/langchain_observability.py` 🆕 — LangChain chains/runnables
- `examples/openai_observability.py` 🆕 — Direct OpenAI SDK usage
- `examples/generic_observability.py` 🆕 — Framework-agnostic example
- `examples/evaluations/genai_eval_with_tracing.py` 🆕 — Evals + tracing together

---

## Execution Order

| Priority | Task | Depends On | Est. Size |
|----------|------|------------|-----------|
| 1 | Task 1: `base.py` | — | ~400 lines |
| 2 | Task 5: Refactor `langgraph.py` | Task 1 | ~200 line delta |
| 3 | Task 2: `langchain.py` | Task 1 | ~100 lines |
| 4 | Task 3: `openai_integration.py` | Task 1 | ~250 lines |
| 5 | Task 4: `generic.py` | Task 1 | ~150 lines |
| 6 | Task 6: `pyproject.toml` | — | ~15 lines |
| 7 | Task 7: `__init__.py` updates | Tasks 1-5 | ~30 lines |
| 8 | Task 8: Tests | Tasks 1-5 | ~500 lines |
| 9 | Task 9: Documentation | Tasks 1-5 | ~400 lines |
| 10 | Task 10: Examples | Tasks 1-5 | ~300 lines |

---

## Key Design Decisions

1. **No hard dependencies** — All framework integrations are optional extras.
   Core `base.py` uses only stdlib + `flowyml.storage`.

2. **Shared data model** — `TraceSpan` and `TraceSession` are defined once in
   `base.py`. All integrations produce the same data, viewable in the same UI.

3. **Lazy metadata store** — The store is only initialized when the first trace
   event needs to be persisted, avoiding import-time DB creation.

4. **`auto_log=True` by default** — Traces are persisted automatically. Can be
   disabled for testing or when only the in-memory session summary is needed.

5. **Cost estimation is best-effort** — Unknown models get `$0.00`. The cost table
   is maintained in `base.py` and easy to extend.

6. **Print summary by default** — When using `trace()` or `observe()`, a summary
   is printed at the end. Can be silenced with `print_summary=False`.

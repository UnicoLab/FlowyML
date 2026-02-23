# 🔗 GenAI Observability — Full-Stack Tracing for Any AI Framework

FlowyML provides **zero-config GenAI observability** — just import, decorate, and get
full tracing, token tracking, cost estimation, and UI visualization automatically.

> [!TIP]
> **New to GenAI observability?** Start with the [30-Second Quick Start](#30-second-quick-start)
> below. You'll have full tracing in 3 lines of code.

---

## 30-Second Quick Start

```python
# For LangGraph agents
from flowyml import observe, trace_graph

@observe(name="my_agent", project="chatbot")
def handle_query(query, flowyml_session=None):
    return graph.invoke(
        {"messages": [HumanMessage(content=query)]},
        config=flowyml_session.config,  # Auto-injected!
    )

result = handle_query("What is AI?")
# ═══════════════════════════════════════════════════
#   🔗 FlowyML Trace — my_agent (langgraph)
# ═══════════════════════════════════════════════════
#   🤖 LLM Calls  : 2
#   🔧 Tool Calls : 1
#   📊 Tokens     : 1,234 (prompt: 800 / completion: 434)
#   💰 Est. Cost  : $0.0042
#   🏷  Models     : gpt-4o-mini
#   🛠  Tools      : web_search
# ═══════════════════════════════════════════════════
```

---

## Installation

```bash
# Core (always available — no external deps)
pip install flowyml

# With LangGraph/LangChain support
pip install "flowyml[langgraph]"

# With OpenAI support
pip install "flowyml[openai]"

# Everything
pip install "flowyml[genai]"
```

---

## Supported Frameworks

| Framework | Integration | Code Change |
|-----------|------------|-------------|
| **LangGraph** | `@observe()` / `trace_graph()` / `instrument()` | 1-2 lines |
| **LangChain** | `@observe_chain()` / `trace_chain()` / `instrument_chain()` | 1-2 lines |
| **OpenAI SDK** | `TracedOpenAI()` / `patch_openai()` | 1 line |
| **Any Framework** | `@observe()` / `trace()` / `span()` / `log_llm_call()` | 1-3 lines |

---

## 1. LangGraph Integration

### Method A: `@observe()` Decorator (Recommended)

The simplest way — decorate your function and everything is traced automatically:

```python
from flowyml import observe

@observe(name="customer_agent", project="support")
def handle_ticket(ticket_id: str, flowyml_session=None):
    # flowyml_session.config has the callbacks pre-configured
    result = graph.invoke(
        {"messages": [HumanMessage(content=f"Handle ticket {ticket_id}")]},
        config=flowyml_session.config,
    )
    return result

# Just call normally — tracing happens automatically
handle_ticket("TICKET-1234")
```

### Method B: `trace_graph()` Context Manager

For more control over the tracing scope:

```python
from flowyml import trace_graph

with trace_graph("research_agent", project="analytics") as session:
    # Multi-turn conversation — all traced as one session
    result1 = graph.invoke(
        {"messages": [HumanMessage(content="Research AI trends")]},
        config=session.config,
    )
    result2 = graph.invoke(
        {"messages": [HumanMessage(content="Now summarize")]},
        config=session.config,
    )
# Summary prints automatically at end of block
```

### Method C: `instrument()` — Wrap Once, Trace Forever

Permanently instrument a compiled graph:

```python
from flowyml import instrument_graph

# One-time setup
traced_graph = instrument_graph(graph, name="my_agent", project="prod")

# Every call is now auto-traced — no config needed!
result = traced_graph.invoke({"messages": [HumanMessage(content="Hello")]})
result = traced_graph.invoke({"messages": [HumanMessage(content="Bye")]})
```

### Method D: Direct Callback Handler

Maximum control for advanced use cases:

```python
from flowyml import FlowyMLCallbackHandler

handler = FlowyMLCallbackHandler(session_name="my_agent", project="demo")
result = graph.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"callbacks": [handler]},
)
handler.session.print_summary()
```

---

## 2. LangChain Integration

Works with any LangChain chain, runnable, or agent — no LangGraph needed.

```python
from flowyml.integrations.langchain import trace_chain, observe_chain

# Context Manager
with trace_chain("qa_chain", project="support") as session:
    result = chain.invoke(
        {"question": "What is quantum computing?"},
        config=session.config,
    )

# Decorator
@observe_chain(name="summarizer", project="nlp")
def summarize(text: str, flowyml_session=None):
    return chain.invoke({"text": text}, config=flowyml_session.config)

# Permanent instrumentation
from flowyml.integrations.langchain import instrument_chain
traced = instrument_chain(chain, name="qa_chain")
result = traced.invoke({"question": "..."})  # Auto-traced!
```

---

## 3. OpenAI SDK Integration

Track every OpenAI API call without LangChain — works directly with the `openai` package.

### Drop-in Replacement (Easiest)

```python
from flowyml import TracedOpenAI

# Replace openai.OpenAI() with TracedOpenAI()
client = TracedOpenAI(project="my_app")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Explain quantum computing"}],
)

# Tokens, cost, and latency tracked automatically
client.finalize()  # Prints summary & saves to FlowyML
```

### Patch Existing Client

```python
import openai
from flowyml import patch_openai

client = openai.OpenAI()
tracer = patch_openai(client, project="my_app")

# Use normally — everything is traced behind the scenes
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)

# Embeddings are tracked too
embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input="Hello world",
)

tracer.session.print_summary()
```

### Streaming Support

Streaming responses are automatically tracked — tokens are counted and cost
is calculated when the stream completes:

```python
client = TracedOpenAI(project="my_app")

stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a poem"}],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")

client.finalize()  # Full token count & cost available
```

---

## 4. Generic / Any Framework

Works with CrewAI, AutoGen, Haystack, DSPy, or any custom code.

### Decorator

```python
from flowyml.integrations.generic import observe

@observe(name="research_crew", project="analytics")
def run_crew(topic: str, flowyml_session=None):
    crew = Crew(agents=[...], tasks=[...])
    result = crew.kickoff(inputs={"topic": topic})

    # Log the LLM calls manually if the framework doesn't expose callbacks
    from flowyml.integrations.generic import log_llm_call
    log_llm_call(
        model="gpt-4o",
        prompt=topic,
        response=str(result),
        prompt_tokens=500,
        completion_tokens=300,
        tracer=flowyml_session,
    )
    return result
```

### Context Manager

```python
from flowyml.integrations.generic import trace

with trace("my_pipeline", project="demo") as tracer:
    # Start a span for each step
    span = tracer.start_span("llm", "embeddings_step")
    embeddings = compute_embeddings(texts)
    span.set_tokens(prompt_tokens=len(texts) * 10, model="text-embedding-3-small")
    tracer.end_span(span, outputs={"count": len(embeddings)})

    span2 = tracer.start_span("llm", "generation_step")
    result = generate_response(embeddings)
    span2.set_tokens(prompt_tokens=200, completion_tokens=500, model="gpt-4o")
    tracer.end_span(span2, outputs={"response": result})
```

### `span()` Context Manager (Simplest)

```python
from flowyml.integrations.generic import span

with span("my_llm_call", "llm") as s:
    result = my_custom_llm(prompt="Hello")
    s.set_tokens(prompt_tokens=5, completion_tokens=10, model="my-model")
    s.outputs = {"response": result}
```

### Fire-and-Forget Logging

```python
from flowyml import log_llm_call, log_tool_call, log_embedding_call

# Log individual calls without any wrapping
log_llm_call(
    model="gpt-4o",
    prompt="Summarize this",
    response="Here's the summary...",
    prompt_tokens=50,
    completion_tokens=100,
)

log_tool_call(
    name="web_search",
    tool_input="latest AI news",
    tool_output="Found 10 results...",
)

log_embedding_call(
    model="text-embedding-3-small",
    input_text=["Hello", "World"],
    token_count=4,
)
```

---

## What Gets Tracked Automatically

Every integration captures the same comprehensive telemetry:

| Metric | Description |
|--------|-------------|
| 🤖 **LLM Calls** | Count, model, prompts, responses |
| 🔧 **Tool Calls** | Name, input, output, duration |
| 🔗 **Chain Steps** | Execution order, parent-child relationships |
| 📊 **Token Usage** | Prompt, completion, and total tokens |
| 💰 **Cost Estimation** | Per-call and session-total USD cost |
| ⏱ **Latency** | Per-step and total duration |
| ❌ **Errors** | Full error context and stack traces |
| 🏷 **Models** | All models used in the session |
| 📐 **Embeddings** | Embedding calls, dimensions, token count |
| 📋 **Trace Tree** | Full parent-child span hierarchy |

### Supported Models for Cost Estimation

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4-Turbo, GPT-4, GPT-3.5-Turbo, o1, o1-mini, o3-mini |
| **Anthropic** | Claude 3.5 Sonnet/Haiku, Claude 3 Opus/Sonnet/Haiku |
| **Google** | Gemini 2.0 Flash, Gemini 1.5 Pro/Flash |
| **Mistral** | Large, Medium, Small |
| **Cohere** | Command R+, Command R |

---

## Viewing Traces in FlowyML UI

All traces are automatically saved and visible in the FlowyML dashboard:

```python
# Start UI
flowyml ui

# Traces are at:
# http://localhost:8765/api/traces
# http://localhost:8765/api/runs
```

Retrieve traces programmatically:

```python
from flowyml.storage.sql import SQLMetadataStore

store = SQLMetadataStore()
traces = store.get_trace(session_id)
```

---

## Configuration Reference

All integration functions accept these common parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Function name / `"genai_session"` | Name for the trace session |
| `project` | `str \| None` | `None` | Project name for organization |
| `tags` | `dict` | `{}` | Custom tags for filtering |
| `auto_log` | `bool` | `True` | Persist traces to FlowyML storage |
| `verbose` | `bool` | `False` | Log each event to console |
| `print_summary` | `bool` | `True` | Print summary table on completion |

---

## Advanced: Custom Cost Models

Extend the built-in cost table with your own models:

```python
from flowyml.integrations.base import MODEL_COSTS

# Add custom model
MODEL_COSTS["my-custom-model"] = {
    "prompt": 0.001,      # $ per 1K prompt tokens
    "completion": 0.003,  # $ per 1K completion tokens
}
```

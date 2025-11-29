# GenAI & LLM Tracing 🕵️

flowyml provides built-in observability for Large Language Models (LLMs), giving you X-ray vision into your GenAI applications.

> [!NOTE]
> **What you'll learn**: How to track token usage, costs, and latency for every LLM call
>
> **Key insight**: LLMs are black boxes. Tracing turns them into transparent, measurable components.

## Why Tracing Matters

**Without tracing**:
- **Hidden costs**: "Why is our OpenAI bill $500 this month?"
- **Latency spikes**: "Why is the chatbot taking 10 seconds?"
- **Quality issues**: "What exact prompt caused this hallucination?"

**With flowyml tracing**:
- **Cost transparency**: See cost per call, per user, or per pipeline
- **Performance metrics**: Pinpoint slow steps in your RAG chain
- **Full context**: See the exact prompt and completion for every interaction

## 🕵️ LLM Call Tracing

You can trace any function as an LLM call or a chain of calls using the `@trace_llm` decorator. flowyml automatically captures inputs, outputs, and metadata.

## 🕵️ LLM Call Tracing

You can trace any function as an LLM call or a chain of calls using the `@trace_llm` decorator.

### Basic Usage

```python
from flowyml import trace_llm
import openai

@trace_llm(name="text_generation")
def generate_text(prompt: str):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# This call will be automatically traced and logged
result = generate_text("Write a haiku about ML pipelines")
```

### Real-World Pattern: RAG Pipeline

Trace a complete Retrieval Augmented Generation (RAG) workflow to see where time is spent.

```python
from flowyml import trace_llm

@trace_llm(name="rag_chain", event_type="chain")
def rag_pipeline(query: str):
    # 1. Retrieve context (Tool)
    context = retrieve_context(query)

    # 2. Generate answer (LLM)
    answer = generate_answer(query, context)
    return answer

@trace_llm(name="retrieval", event_type="tool")
def retrieve_context(query: str):
    # Simulate vector DB lookup
    return "flowyml documentation..."

@trace_llm(name="generation", event_type="llm", model="gpt-4")
def generate_answer(query: str, context: str):
    # This call's tokens and cost will be tracked
    return openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"Context: {context}"},
            {"role": "user", "content": query}
        ]
    )
```

> [!TIP]
> **Pro Tip**: Use `event_type="chain"` for the parent function and `"llm"` or `"tool"` for children. This creates a beautiful nested waterfall view in the UI.

## 📊 Viewing Traces

Traces are automatically persisted to the metadata store and can be visualized in the flowyml UI.

### In the UI

Navigate to the **Traces** tab in the flowyml Dashboard (`http://localhost:8080/traces`). You will see:

- **Timeline View**: A waterfall chart of your traces.
- **Latency & Cost**: Aggregated metrics for each trace.
- **Inputs & Outputs**: Full inspection of prompts and completions.
- **Token Usage**: Detailed breakdown of prompt vs. completion tokens.

### Programmatic Access

You can also retrieve traces via the Python API for analysis.

```python
from flowyml.storage.metadata import SQLiteMetadataStore

store = SQLiteMetadataStore()
trace = store.get_trace(trace_id="<trace_id>")

print(f"Latency: {trace.latency}ms")
print(f"Tokens: {trace.total_tokens}")
```

## 🏷️ Trace Attributes

You can add custom attributes to your traces for better filtering and analysis.

```python
@trace_llm(name="categorize", attributes={"model_version": "v2", "temperature": 0.7})
def categorize_text(text):
    # ...
```

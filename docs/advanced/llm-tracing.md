# GenAI & LLM Tracing 🕵️

UniFlow provides built-in tracing for Large Language Model (LLM) interactions, allowing you to monitor token usage, costs, latency, and full execution traces of your GenAI pipelines.

## 🕵️ LLM Call Tracing

You can trace any function as an LLM call or a chain of calls using the `@trace_llm` decorator.

### Basic Usage

```python
from uniflow import trace_llm
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

### Nested Traces (Chains & Agents)

You can nest traces to visualize complex workflows like RAG (Retrieval Augmented Generation) or Agents.

```python
from uniflow import trace_llm

@trace_llm(name="rag_pipeline", event_type="chain")
def rag_pipeline(query: str):
    # This child trace will be nested under 'rag_pipeline'
    context = retrieve_context(query)
    answer = generate_answer(query, context)
    return answer

@trace_llm(name="retrieval", event_type="tool")
def retrieve_context(query: str):
    # Simulate retrieval
    return "UniFlow is a great tool."

@trace_llm(name="generation", event_type="llm")
def generate_answer(query: str, context: str):
    # Simulate generation
    return f"Based on {context}, I answer: {query}"
```

## 📊 Viewing Traces

Traces are automatically persisted to the metadata store and can be visualized in the UniFlow UI.

### In the UI

Navigate to the **Traces** tab in the UniFlow Dashboard (`http://localhost:8080/traces`). You will see:

- **Timeline View**: A waterfall chart of your traces.
- **Latency & Cost**: Aggregated metrics for each trace.
- **Inputs & Outputs**: Full inspection of prompts and completions.
- **Token Usage**: Detailed breakdown of prompt vs. completion tokens.

### Programmatic Access

You can also retrieve traces via the Python API for analysis.

```python
from uniflow.storage.metadata import SQLiteMetadataStore

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

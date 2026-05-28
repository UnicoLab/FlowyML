---
title: Context API — FlowyML
description: "Full API reference for the context() function and Context class: parameter injection, environment configs, and runtime overrides."
---

<div class="hero-section" markdown>

## 📜 Context API

Context separates configuration from code — inject parameters into steps without hard-coding values.

<span class="feature-badge">🎛️ Parameters</span>
<span class="feature-badge">🌍 Environments</span>
<span class="feature-badge">🔀 Overrides</span>

</div>

## `context()` Function

```python
from flowyml import context

ctx = context(
    dataset_path="data/train.csv",
    epochs=50,
    learning_rate=0.001,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `**kwargs` | `Any` | — | Arbitrary key-value pairs. Keys matching step parameter names are injected automatically. |

!!! info "Immutable by Design"
    Once created, a context object is immutable. Use `ctx.override()` to create a **new** context with updated values.

## `Context` Methods & Properties

| Method / Property | Signature | Description |
|-------------------|-----------|-------------|
| `override` | `override(**kwargs) → Context` | Return a new context with specified keys replaced. Original is unchanged. |
| `merge` | `merge(other: Context) → Context` | Combine two contexts. Values from `other` take precedence on conflict. |
| `to_dict` | `to_dict() → dict` | Serialize all parameters to a plain dictionary. |
| `get` | `get(key, default=None)` | Retrieve a single parameter value with an optional default. |
| `pipeline_name` | `str` (property) | Name of the pipeline this context is bound to (set at runtime). |
| `run_id` | `str` (property) | Unique identifier for the current pipeline run. |
| `environment` | `str` (property) | Current environment name (e.g., `dev`, `staging`, `prod`). |

## Usage Examples

### Basic Context

```python linenums="1"
from flowyml import Pipeline, step, context

@step(outputs=["data"])
def load(dataset_path: str = "default.csv"):
    return pd.read_csv(dataset_path)

ctx = context(dataset_path="gs://bucket/train.csv")
pipeline = Pipeline("basic", context=ctx)
pipeline.add_step(load)
pipeline.run()  # load receives dataset_path="gs://bucket/train.csv"
```

### Environment-Specific Configs

```python linenums="1"
import os
from flowyml import context

base = context(
    batch_size=32,
    learning_rate=0.001,
)

if os.getenv("FLOWYML_ENV") == "prod":
    ctx = base.override(
        dataset_path="gs://prod-bucket/data.csv",
        batch_size=256,
    )
else:
    ctx = base.override(
        dataset_path="local/dev_sample.csv",
        batch_size=16,
    )
```

### Runtime Override via CLI

```bash
flowyml run pipeline.py \
  --context dataset_path=gs://bucket/new_data.csv \
  --context epochs=100
```

!!! tip "Override Precedence"
    Values are resolved in this order (highest priority first):

    1. **CLI `--context` flags** — always win
    2. **`pipeline.run(**overrides)`** — programmatic overrides
    3. **`context()` constructor** — base configuration
    4. **Step parameter defaults** — fallback values

### Accessing Context Inside Steps

```python linenums="1"
from flowyml import step, get_context

@step(outputs=["report"])
def generate_report():
    ctx = get_context()
    print(f"Pipeline: {ctx.pipeline_name}")
    print(f"Run ID:   {ctx.run_id}")
    print(f"Env:      {ctx.environment}")
    return {"run_id": ctx.run_id, "status": "complete"}
```

## Autodoc

::: flowyml.core.context.Context
    options:
        show_root_heading: false

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🎢 Pipeline API
Pass contexts to pipelines and control execution behavior.

[View Pipeline API →](pipeline.md)

</div>

<div class="header-card" markdown>

### 👣 Step API
See how step parameters receive injected context values.

[View Step API →](step.md)

</div>

<div class="header-card" markdown>

### 📦 Assets API
Artifacts produced by steps — Model, Dataset, and Metrics.

[View Assets API →](assets.md)

</div>

</div>

---
title: Step API — FlowyML
description: "Full API reference for the @step decorator and Step class: parameters, caching, retries, resource hints, and patterns."
---

<div class="hero-section" markdown>

## 👣 Step API

Steps are the atomic units of work in a FlowyML pipeline — pure functions decorated with `@step`.

<span class="feature-badge">🎯 Decorator</span>
<span class="feature-badge">💾 Caching</span>
<span class="feature-badge">🔄 Retries</span>
<span class="feature-badge">🖥️ Resources</span>

</div>

## `@step` Decorator Parameters

```python
from flowyml import step

@step(
    outputs=["model"],
    inputs=["data"],
    cache=True,
    retries=3,
    timeout=600,
)
def train(data):
    ...
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `outputs` | `list[str]` | `[]` | Named artifacts this step produces. Used to wire the DAG. |
| `inputs` | `list[str]` | `[]` | Named artifacts this step consumes. Automatically resolved from upstream steps. |
| `cache` | `bool` | `True` | Enable content-addressed caching. Skips re-execution when inputs haven't changed. |
| `retries` | `int` | `0` | Number of automatic retries on failure before the step is marked as failed. |
| `timeout` | `int | None` | `None` | Maximum execution time in seconds. `None` means no limit. |
| `resources` | `dict | None` | `None` | Resource hints (e.g., `{"gpu": 1, "memory": "8Gi"}`). Interpreted by the orchestrator. |
| `tags` | `list[str]` | `[]` | Arbitrary tags for filtering and grouping in the UI. |
| `description` | `str | None` | `None` | Human-readable description shown in the UI DAG view. |

## Step Function Patterns

### Single Output

```python linenums="1"
@step(outputs=["cleaned_data"])
def clean(raw_data):
    """Return value is automatically mapped to 'cleaned_data'."""
    return raw_data.dropna()
```

### Multiple Outputs

```python linenums="1"
@step(outputs=["X_train", "X_test", "y_train", "y_test"])
def split(data):
    """Return a tuple — values are mapped to outputs in order."""
    X_train, X_test, y_train, y_test = train_test_split(data)
    return X_train, X_test, y_train, y_test
```

### Context Injection

```python linenums="1"
@step(outputs=["data"])
def load(dataset_path: str = "default.csv"):
    """Parameters with defaults are auto-injected from context."""
    return pd.read_csv(dataset_path)
```

!!! info "How Context Injection Works"
    If the pipeline's `context` contains a key matching a step parameter name, the context value is injected automatically. The function default is used as a fallback.

### No Outputs (Side-Effect Steps)

```python linenums="1"
@step()
def notify(model_name: str = "model"):
    """Steps with no outputs are valid — useful for notifications or logging."""
    send_slack_message(f"Model {model_name} training complete!")
```

## Common Examples

### Cached Training Step with Retries

```python linenums="1"
@step(
    inputs=["X_train", "y_train"],
    outputs=["model"],
    cache=True,
    retries=2,
    timeout=3600,
    resources={"gpu": 1, "memory": "16Gi"},
)
def train_model(X_train, y_train, epochs: int = 50, lr: float = 0.001):
    model = build_model(lr=lr)
    model.fit(X_train, y_train, epochs=epochs)
    return model
```

### Dynamic Step with map_task

```python linenums="1"
from flowyml import step, map_task

@step(outputs=["predictions"])
def predict_batch(model, batch):
    return model.predict(batch)

# Map across multiple batches in parallel
pipeline.add_step(map_task(predict_batch, items=batches))
```

!!! tip "When to Disable Caching"
    Disable caching (`cache=False`) for steps that depend on external state — e.g., fetching live data from an API or reading the latest file from a bucket.

## Autodoc

### Decorator `@step`

::: flowyml.core.step.step
    options:
        show_root_heading: false

### Class `Step`

::: flowyml.core.step.Step
    options:
        show_root_heading: false

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🎢 Pipeline API
Wire steps into a DAG and execute with `Pipeline.run()`.

[View Pipeline API →](pipeline.md)

</div>

<div class="header-card" markdown>

### 📜 Context API
Inject parameters into steps with environment-specific configs.

[View Context API →](context.md)

</div>

<div class="header-card" markdown>

### 📦 Assets API
Wrap step outputs as Model, Dataset, or Metrics artifacts.

[View Assets API →](assets.md)

</div>

</div>

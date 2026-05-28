---
title: Pipeline API — FlowyML
description: "Full API reference for the Pipeline class: construction, step management, execution, scheduling, and lifecycle."
---

<div class="hero-section" markdown>

## 🎢 Pipeline API

The central orchestrator that wires steps into a directed acyclic graph and manages execution.

<span class="feature-badge">🔧 Build</span>
<span class="feature-badge">▶️ Execute</span>
<span class="feature-badge">📅 Schedule</span>

</div>

## Constructor

```python
from flowyml import Pipeline

pipeline = Pipeline(
    name="my_pipeline",
    context=ctx,           # optional
    description="...",     # optional
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | **required** | Unique identifier for the pipeline. Used in UI, logs, and artifact paths. |
| `context` | `Context | None` | `None` | A `context()` object for parameter injection into steps. |
| `description` | `str | None` | `None` | Human-readable description shown in the UI dashboard. |
| `tags` | `list[str]` | `[]` | Arbitrary tags for filtering and grouping pipeline runs. |
| `version` | `str | None` | `None` | Explicit version string. Auto-incremented if omitted. |

## Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_step` | `add_step(fn, **overrides)` | Register a decorated `@step` function. Overrides let you change `cache`, `retries`, etc. at add-time. |
| `run` | `run(**runtime_ctx) → PipelineResult` | Execute all steps in topological order. Returns a result object with `.success`, `.outputs`, `.duration`. |
| `build` | `build() → DAG` | Compile the pipeline into a DAG without executing. Useful for validation and visualization. |
| `schedule` | `schedule(cron: str, **kwargs)` | Register a cron-style schedule for recurring execution. |
| `dry_run` | `dry_run(**runtime_ctx) → PipelineResult` | Simulate execution — resolves the DAG and validates inputs/outputs without running step bodies. |
| `visualize` | `visualize(format="mermaid")` | Render the pipeline DAG as Mermaid, DOT, or ASCII art. |

## Usage Examples

### 1️⃣ Basic Pipeline

```python linenums="1"
from flowyml import Pipeline, step

@step(outputs=["data"])
def load_data():
    return [1, 2, 3]

@step(inputs=["data"], outputs=["result"])
def transform(data):
    return [x * 2 for x in data]

pipeline = Pipeline("basic")
pipeline.add_step(load_data)
pipeline.add_step(transform)

result = pipeline.run()
print(result.outputs)  # {"result": [2, 4, 6]}
```

### 2️⃣ Pipeline with Context

```python linenums="1"
from flowyml import Pipeline, step, context

@step(outputs=["data"])
def load_data(dataset_path: str = "data.csv"):
    return pd.read_csv(dataset_path)

ctx = context(dataset_path="gs://bucket/train.csv")
pipeline = Pipeline("with_context", context=ctx)
pipeline.add_step(load_data)

result = pipeline.run()
```

!!! tip "Runtime Overrides"
    You can also pass overrides directly to `run()`:
    ```python
    result = pipeline.run(dataset_path="local/test.csv")
    ```

### 3️⃣ Sub-Pipeline Composition

```python linenums="1"
from flowyml import Pipeline, step
from flowyml.core.pipeline import SubPipelineStep

# Define a reusable sub-pipeline
preprocess = Pipeline("preprocess")
preprocess.add_step(clean_data)
preprocess.add_step(normalize)

# Embed it inside a larger pipeline
main = Pipeline("training")
main.add_step(SubPipelineStep(preprocess))
main.add_step(train_model)
main.add_step(evaluate)

result = main.run()
```

### 4️⃣ Scheduled Execution

```python linenums="1"
from flowyml import Pipeline, step

pipeline = Pipeline("nightly_retrain")
pipeline.add_step(fetch_latest_data)
pipeline.add_step(retrain_model)
pipeline.add_step(deploy_if_better)

# Run every day at 2 AM UTC
pipeline.schedule("0 2 * * *")
```

### 5️⃣ Dry Run & Validation

```python linenums="1"
pipeline = Pipeline("validate_me")
pipeline.add_step(load_data)
pipeline.add_step(transform)

# Validate without executing step bodies
result = pipeline.dry_run()
print(result.dag)       # Inspect resolved DAG
print(result.outputs)   # Expected output keys
```

!!! warning "Dry Run Limitations"
    Dry runs validate the DAG topology and type compatibility but cannot catch runtime errors inside step functions.

## `PipelineResult`

The object returned by `run()` and `dry_run()`:

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | Whether all steps completed without error. |
| `outputs` | `dict` | Final outputs keyed by artifact name. |
| `duration` | `float` | Total wall-clock time in seconds. |
| `steps` | `list[StepResult]` | Per-step results with timing and status. |
| `dag` | `DAG` | The compiled directed acyclic graph. |

## Autodoc

::: flowyml.core.pipeline.Pipeline
    options:
        show_root_heading: false
        show_source: true

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 👣 Step API
Decorator options, caching, retries, resource requirements, and input/output contracts.

[View Step API →](step.md)

</div>

<div class="header-card" markdown>

### 📜 Context API
Parameter injection, environment-specific configs, and runtime overrides.

[View Context API →](context.md)

</div>

<div class="header-card" markdown>

### 📦 Assets API
Model, Dataset, and Metrics — first-class artifacts with lineage tracking.

[View Assets API →](assets.md)

</div>

</div>

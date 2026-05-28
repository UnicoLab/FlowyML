---
title: Steps — FlowyML Core Concepts
description: "Learn how to define, configure, and compose Steps — the building blocks of FlowyML pipelines. Covers the @step decorator, inputs/outputs, caching, error handling, and testing."
---

<div class="hero-section" markdown>

## ☞ Steps

Steps are the atomic units of work in FlowyML pipelines. Decorate any Python function with `@step`, declare its inputs and outputs, and FlowyML handles the rest — caching, retries, parallel execution, and artifact tracking.

<span class="feature-badge">🎯 Type-Safe</span>
<span class="feature-badge">💾 Cacheable</span>
<span class="feature-badge">🔄 Retriable</span>
<span class="feature-badge">🧩 Composable</span>

</div>

!!! info "What you'll learn"
    How to design reusable, testable steps that compose into production pipelines. Well-designed steps are **pure, focused, and composable**.

## Why Steps Matter 👣

**Without steps**, you have:
- Functions scattered across files, hard to reuse
- No automatic caching of expensive operations
- Manual error handling and retries
- No visibility into what's running or failed

**With flowyml steps**, you get:
- **Automatic dependency tracking**: flowyml knows execution order
- **Intelligent caching**: Skip redundant computation automatically
- **Built-in retry logic**: Handle transient failures gracefully
- **Full observability**: See inputs, outputs, duration for every execution
- **Testability**: Each step is a pure function you can unit test

## Step Design Principles ⚖️

### 1. Pure Functions 🧪

```python
# ✅ Good: Pure function, deterministic output
@step(outputs=["processed"])
def clean_data(raw_data):
    return raw_data.dropna().reset_index(drop=True)

# ❌ Bad: Side effects, global state
@step
def clean_data_impure():
    global df_global  # Don't do this!
    df_global = df_global.dropna()
    return df_global
```

**Why**: Pure functions are testable, cacheable, and parallelizable. Side effects break caching and make debugging nightmares.

### 2. Single Responsibility 🎯

```python
# ✅ Good: Focused steps, independently cacheable
@step(outputs=["split"])
def split_data(data, test_size=0.2): ...

@step(inputs=["split"], outputs=["model"])
def train_model(split): ...

# ❌ Bad: Monolithic step, can't cache parts
@step(outputs=["model"])
def split_and_train_and_evaluate(data):
    split = split_data(data)      # Can't cache this separately
    model = train_model(split)    # Or this
    metrics = evaluate(model)     # Or this
    return model, metrics
```

**Why**: Granular steps enable better caching. Tweaking training doesn't re-run data splitting.

### 3. Explicit vs. Implicit 📢

```python
# ✅ Good: Clear inputs/outputs
@step(inputs=["raw_data"], outputs=["clean_data"])
def clean(raw_data):
    return process(raw_data)

# ⚠️ Less clear: flowyml can't validate dependencies
@step
def clean(data):
    return process(data)
```

**Why**: Explicit `inputs`/`outputs` enable DAG visualization, validation, and better error messages.

## Anatomy of a Step 🦴

A step is a Python function with the `@step` decorator:

```python
from flowyml import step

@step(outputs=["result"])
def my_step(input_data):
    # Do some work
    processed = input_data * 2
    return processed
```

## The @step Decorator 🪄

The `@step` decorator accepts several arguments to configure behavior:

### Configuration Options

| Argument | Type | Description | Default |
|----------|------|-------------|------------|
| `inputs` | `List[str]` | Names of input assets this step requires | `[]` |
| `outputs` | `List[str]` | Names of output assets this step produces | `[]` |
| `cache` | `str \| bool` | Caching strategy: `"code_hash"`, `"input_hash"`, or `False` | `"code_hash"` |
| `retry` | `int` | Number of retry attempts on failure | `0` |
| `timeout` | `int` | Maximum execution time in seconds | `None` |
| `resources` | `dict` | Resource requirements (e.g., `{"gpu": 1}`) | `None` |
| `execution_group`| `str` | Name of the group to run steps together | `None` |

!!! tip "Performance: Step Grouping"
    Use `execution_group` to run multiple steps in the same container. This eliminates the container startup overhead for consecutive small steps. See [Step Grouping](../advanced/step-grouping.md) for details.

### Example with Full Configuration

```python
@step(
    inputs=["raw_dataset"],
    outputs=["trained_model"],
    cache="input_hash",
    retry=3,
    timeout=3600,
    resources={"gpu": 1, "memory": "16Gi"}
)
def train_model(raw_dataset, learning_rate: float):
    """Train a machine learning model."""
    model = train(raw_dataset, lr=learning_rate)
    return model
```

## Inputs and Outputs 🔌

### Defining Dependencies

Steps declare their dependencies through `inputs` and `outputs`:

```python
@step(outputs=["data"])
def load():
    return [1, 2, 3, 4, 5]

@step(inputs=["data"], outputs=["processed"])
def process(data):
    return [x * 2 for x in data]

# flowyml automatically determines execution order
pipeline = Pipeline("etl")
pipeline.add_step(load)
pipeline.add_step(process)  # Runs after load()
```

### How Wiring Works

1. **Step Outputs**: When a step completes, its output is stored with the name specified in `outputs`
2. **Step Inputs**: For the next step, flowyml matches `inputs` names to stored outputs
3. **Auto-Injection**: The values are automatically passed as function arguments

```python
# After load() completes, output is stored as "data"
# When process() runs, "data" is injected as the 'data' parameter
```

## Multiple Inputs and Outputs 📦

### Multiple Outputs

A step can return multiple values using tuples:

```python
@step(outputs=["train_data", "test_data"])
def split_data(data, split_ratio=0.8):
    split_point = int(len(data) * split_ratio)
    return data[:split_point], data[split_point:]
```

### Multiple Inputs

A step can depend on multiple previous steps:

```python
@step(outputs=["data"])
def load_data():
    return [1, 2, 3]

@step(outputs=["labels"])
def load_labels():
    return ["a", "b", "c"]

@step(inputs=["data", "labels"], outputs=["dataset"])
def combine(data, labels):
    return list(zip(data, labels))
```

## Context and Parameter Injection 🧠

Steps can automatically receive parameters from the pipeline's context:

```python
from flowyml import Pipeline, context

ctx = context(
    learning_rate=0.001,
    epochs=100,
    batch_size=32
)

@step(outputs=["model"])
def train(data, learning_rate: float, epochs: int):
    # learning_rate and epochs automatically injected from context!
    print(f"Training with lr={learning_rate} for {epochs} epochs")
    return trained_model

pipeline = Pipeline("training", context=ctx)
```

### Type-Based Artifact Routing (1.8.0) 🧠

One of FlowyML's most powerful features is **Type-Based Routing**. By using type hints in your function signature, FlowyML can automatically route your outputs to the correct infrastructure (e.g., sending a `Model` to Vertex AI Model Registry).

### How it Works

Simply add a return type hint to your `@step` function:

```python
from flowyml import step, Model, Dataset

@step
def train_model(data: pd.DataFrame) -> Model:
    # ... training logic ...
    return Model(trained_obj, name="my_classifier")

@step
def load_data() -> Dataset:
    # ... loading logic ...
    return Dataset(df, name="raw_data")
```

### Why Use Type Hints?

1.  **Auto-Routing**: `Model` objects go to model registries, `Dataset` objects go to feature stores or data buckets.
2.  **Infrastructure Abstraction**: You don't need to know the GCS/S3 path inside your training function.
3.  **Validation**: FlowyML ensures that downstream steps receive the correct object types.

!!! tip "Pro Tip"
    Use the `Model`, `Dataset`, and `Metrics` classes provided by FlowyML to get the full benefit of auto-extraction and routing.

---

## Caching Strategies 💾

flowyml supports intelligent caching to avoid re-running expensive steps:

### `cache="code_hash"` (Default)

Caches based on the step's code. Re-runs only if the function code changes:

```python
@step(cache="code_hash")
def expensive_computation(data):
    # Cached unless this function's code changes
    return complex_calculation(data)
```

### `cache="input_hash"`

Caches based on input values. Re-runs if inputs change:

```python
@step(cache="input_hash")
def preprocess(data, config):
    # Re-runs only if data or config changes
    return clean(data, config)
```

### `cache=False`

Disable caching for this step:

```python
@step(cache=False)
def fetch_latest_data():
    # Always runs (e.g., for fetching real-time data)
    return api.fetch()
```

See [Caching](../advanced/caching.md) for more details.

## Error Handling and Retries 🔄

### Automatic Retries

Configure retry attempts for flaky operations:

```python
@step(retry=3)
def fetch_external_data():
    # Retries up to 3 times on failure
    response = requests.get(API_URL)
    return response.json()
```

### Timeout Protection

Set maximum execution time:

```python
@step(timeout=300)  # 5 minutes
def long_running_task():
    # Fails if exceeds 5 minutes
    return expensive_operation()
```

### Advanced Error Handling

Use decorators for sophisticated error handling:

```python
from flowyml import retry, on_failure, CircuitBreaker

def fallback_data():
    return {"status": "unavailable"}

@step
@retry(max_attempts=3, backoff=2.0)
@on_failure(fallback_data)
@CircuitBreaker(failure_threshold=5)
def fetch_data():
    return external_api.get_data()
```

See [Error Handling](../advanced/debugging.md) for comprehensive guide.

## Resource Requirements 💪

Specify compute resources needed for a step:

```python
# CPU-intensive
@step(resources={"cpu": "4", "memory": "16Gi"})
def train_cpu():
    ...

# GPU-accelerated
@step(resources={"gpu": "nvidia-tesla-v100", "gpu_count": 2})
def train_gpu():
    ...
```

Resources are used by:
- **Local execution**: For monitoring/limiting
- **Cloud stacks**: To provision appropriate instances
- **Kubernetes**: To set pod resources

## Decision Guide: Caching ⚖️

| Scenario | Use | Why |
|----------|-----|-----|
| Expensive computation, stable code | `code_hash` (default) | Re-runs only when logic changes |
| Data preprocessing | `input_hash` | Re-runs when input data changes |
| Real-time data fetching | `cache=False` | Always get latest |
| Model training (hours) | `input_hash` | Don't retrain unless data/params change |
| API calls (rate-limited) | `input_hash` | Cache responses, respect limits |

**Pro tip**: Use `input_hash` for expensive operations where inputs determine outputs. Use `code_hash` for pure transformations.

---

## Step Testing Patterns 🧪

### Unit Testing Steps

Steps are just functions — test them like functions:

```python
import pytest
from my_pipeline import clean_data, train_model

def test_clean_data():
    # Arrange
    raw = pd.DataFrame({"a": [1, None, 3]})

    # Act
    result = clean_data(raw)

    # Assert
    assert result["a"].isnull().sum() == 0
    assert len(result) == 2

def test_train_model():
    X = np.random.rand(100, 10)
    y = np.random.rand(100)

    model = train_model(X, y, learning_rate=0.01, epochs=10)

    assert model is not None
    assert hasattr(model, 'predict')
```

**Why this works**: Steps are pure functions. No pipeline infrastructure needed for unit tests.

### Integration Testing Steps

```python
def test_pipeline_integration():
    from flowyml import Pipeline, context

    ctx = context(learning_rate=0.01)
    pipeline = Pipeline("test_pipeline", context=ctx)
    pipeline.add_step(load_data)
    pipeline.add_step(train_model)

    result = pipeline.run()

    assert result.success
    assert "model" in result.outputs
```

---

## Step Execution Lifecycle ♻️

Understanding what happens when a step runs:

1. **Validation**: Check all required inputs are available
2. **Cache Check**: Look for cached result matching strategy
3. **Execution**: Run the step function if not cached
4. **Materialization**: Save outputs to artifact store (if configured)
5. **Result Storage**: Store output for downstream steps
6. **Lineage**: Record provenance metadata

```python
# This all happens automatically!
result = pipeline.run()

# You get full observability:
for step_name, step_result in result.step_results.items():
    print(f"{step_name}: {step_result.duration_seconds:.2f}s, cached={step_result.cached}")
```

!!! tip "Performance insight"
    Viewing cached steps in the UI shows how much time you're saving. A well-cached pipeline can go from hours to minutes during iteration.

## Best Practices 💡

### 1. Make Steps Pure Functions

Steps should be deterministic and side-effect free when possible:

```python
# ✅ Good - pure function
@step
def transform(data):
    return [x * 2 for x in data]

# ⚠️ Be careful - side effects
@step
def transform_with_side_effect(data):
    global counter
    counter += 1  # Side effect
    return [x * 2 for x in data]
```

### 2. Name Steps Descriptively

```python
# ✅ Good
@step(outputs=["cleaned_data"])
def remove_duplicates_and_nulls(raw_data):
    ...

# ❌ Bad
@step(outputs=["data"])
def process(data):
    ...
```

### 3. Keep Steps Focused

Each step should do one thing well:

```python
# ✅ Good - separate concerns
@step(outputs=["cleaned"])
def clean_data(raw):
    ...

@step(inputs=["cleaned"], outputs=["features"])
def engineer_features(cleaned):
    ...

# ❌ Bad - doing too much
@step
def clean_and_engineer_and_train(raw):
    cleaned = clean(raw)
    features = engineer(cleaned)
    model = train(features)
    return model
```

### 4. Use Type Hints

Type hints improve code clarity and enable better IDE support:

```python
from typing import List, Dict
import pandas as pd

@step(outputs=["dataframe"])
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)
```

### 5. Document Your Steps

```python
@step(inputs=["features"], outputs=["predictions"])
def predict(features: pd.DataFrame, threshold: float = 0.5) -> pd.Series:
    """Generate predictions from features.

    Args:
        features: Input feature matrix
        threshold: Classification threshold

    Returns:
        Binary predictions
    """
    ...
```

## Advanced Step Patterns ⚡

### Conditional Execution

```python
from flowyml import when, unless

@step
@when(lambda x: x > 100)
def expensive_path(data):
    # Only runs if data > 100
    ...

@step
@unless(lambda x: x is None)
def process_if_exists(data):
    # Skips if data is None
    ...
```

### Parallel Processing

```python
from flowyml import parallel_map

@step
def process_items(items: List):
    # Process items in parallel
    return parallel_map(heavy_function, items, num_workers=4)
```

### Dynamic Step Generation

```python
def create_training_step(model_type: str):
    @step(outputs=[f"{model_type}_model"])
    def train():
        return train_model(model_type)
    return train

# Create multiple training steps
for model_type in ["xgboost", "random_forest", "neural_net"]:
    step_func = create_training_step(model_type)
    pipeline.add_step(step_func)
```

## Next Steps 📚

- **[Pipelines](pipelines.md)**: Connect steps into workflows
- **[Context](context.md)**: Master parameter injection
- **[Caching](../advanced/caching.md)**: Learn how to skip expensive steps with intelligent caching.
- **[Debugging](../advanced/debugging.md)**: Use the interactive debugger with `debug=True`.

---

## 📍 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 📜 Context
Learn how FlowyML auto-injects parameters into your steps.

[Context Guide →](context.md)
</div>

<div class="header-card" markdown>
### 🎢 Pipelines
See how steps are assembled into full ML workflows.

[Pipelines Guide →](pipelines.md)
</div>

<div class="header-card" markdown>
### ⚡ Advanced Workflows
Explore map tasks, dynamic workflows, and sub-pipelines.

[Advanced →](../advanced_features.md)
</div>

</div>

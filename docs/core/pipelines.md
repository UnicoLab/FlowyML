# Pipelines 🚀

Pipelines are the core abstraction in flowyml — they represent workflows that orchestrate your ML operations from data to deployment.

> [!NOTE]
> **What you'll learn**: How to design, build, and run production-grade pipelines
>
> **Key insight**: A well-designed pipeline is infrastructure-agnostic. Write it once, run it anywhere (local, staging, production) without code changes.

## Why Pipelines Matter

Without pipelines, ML workflows are often:
- **Scripts scattered across notebooks** — Hard to reproduce, impossible to version
- **Tightly coupled to infrastructure** — Rewrite for every environment
- **Manually orchestrated** — Prone to human error, doesn't scale
- **Opaque** — Can't see what's running, debug failures, or track lineage

**flowyml pipelines solve this** by providing:
- **Declarative workflows** — Define what to do, not how to execute it
- **Automatic dependency resolution** — Steps run in the right order
- **Built-in observability** — Track every run, inspect every artifact
- **Environment portability** — Same code, different stacks

## Pipeline Design Principles

Before diving into code, understand these design principles:

### 1. **Steps Should Be Pure Functions**

```python
# ✅ Good: Pure function, testable in isolation
@step(outputs=["processed"])
def clean_data(raw_data):
    return raw_data.dropna().reset_index(drop=True)

# ❌ Bad: Side effects, hard to test
@step
def clean_data():
    global df  # Don't do this!
    df = df.dropna()
```

**Why**: Pure functions are testable, cacheable, and parallelizable.

### 2. **One Step, One Responsibility**

```python
# ✅ Good: Focused steps
@step(outputs=["split_data"])
def split_data(data): ...

@step(inputs=["split_data"], outputs=["model"])
def train_model(split_data): ...

# ❌ Bad: Doing too much
@step(outputs=["model"])
def split_and_train(data):
    # Splitting and training in one step = can't cache independently
    split = split_data(data)
    model = train(split)
    return model
```

**Why**: Granular steps enable better caching, debugging, and reuse.

### 3. **Configuration Belongs in Context**

```python
# ✅ Good: Context injection
ctx = context(learning_rate=0.001, epochs=10)
pipeline = Pipeline("training", context=ctx)

@step(outputs=["model"])
def train(data, learning_rate: float, epochs: int):
    # Parameters injected automatically
    ...

# ❌ Bad: Hardcoded configuration
@step(outputs=["model"])
def train(data):
    learning_rate = 0.001  # Can't change without code edit
    epochs = 10
```

**Why**: Separation of code and config enables dev/staging/prod with one codebase.

## Creating Your First Pipeline

Here's a complete, runnable example:

```python
from flowyml import Pipeline, step, context

# Define steps
@step(outputs=["raw_data"])
def extract():
    return [1, 2, 3, 4, 5]

@step(inputs=["raw_data"], outputs=["processed_data"])
def transform(raw_data):
    return [x * 2 for x in raw_data]

# Create pipeline
pipeline = Pipeline("etl_pipeline")

# Add steps in execution order
pipeline.add_step(extract)
pipeline.add_step(transform)

# Run the pipeline
result = pipeline.run()

if result.success:
    print(f"✓ Processed data: {result.outputs['processed_data']}")
```

**What just happened**: flowyml built a DAG, determined execution order, and ran your steps. No Airflow DAG files, no Kubeflow YAML, just Python.

## Pipeline Configuration ⚙️

The `Pipeline` class accepts several configuration options:

```python
from flowyml import Pipeline, context

ctx = context(
    learning_rate=0.001,
    batch_size=32
)

pipeline = Pipeline(
    name="training_pipeline",
    context=ctx,              # Context for parameter injection
    enable_cache=True,        # Enable intelligent caching
    cache_dir="./my_cache",   # Custom cache directory
    stack=my_stack,           # Execution stack (local, cloud, etc.)
    project_name="ml_project" # Automatically creates/attaches to project
)
```

### Configuration Options

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `name` | `str` | Pipeline name (required) | - |
| `context` | `Context` | Context object for parameter injection | `Context()` |
| `executor` | `Executor` | Custom executor | `LocalExecutor()` |
| `enable_cache` | `bool` | Enable step caching | `True` |
| `cache_dir` | `str` | Cache storage directory | `.flowyml/cache` |
| `stack` | `Stack` | Execution stack (local/cloud) | `None` |

## Execution Graph (DAG) 🕸️

When you add steps to a pipeline, flowyml builds a **Directed Acyclic Graph (DAG)**:

- **Nodes**: Steps in the pipeline
- **Edges**: Data dependencies between steps

flowyml analyzes the `inputs` and `outputs` of each step to determine the execution order automatically.

```python
@step(outputs=["data"])
def step_a():
    return [1, 2, 3]

@step(inputs=["data"], outputs=["result"])
def step_b(data):
    return sum(data)

# flowyml automatically determines step_a must run before step_b
```

## Running Pipelines ▶️

### Basic Execution

```python
# Run the pipeline
result = pipeline.run()

# Check success
if result.success:
    print(f"✓ Pipeline completed successfully!")
    print(f"Outputs: {result.outputs}")
else:
    print(f"✗ Pipeline failed")
```

### With Runtime Overrides

You can override configuration at runtime:

```python
# Override context
result = pipeline.run(context={"learning_rate": 0.05})

# Use different stack
result = pipeline.run(stack=my_production_stack)

# Enable debug mode
result = pipeline.run(debug=True)
```

## The `PipelineResult` Object

The result of a pipeline execution is a `PipelineResult` object:

```python
result = pipeline.run()

# Properties
result.run_id              # Unique run identifier
result.pipeline_name       # Pipeline name
result.success             # Boolean: overall success
result.outputs             # Dict: all step outputs
result.step_results        # Dict: detailed results per step
result.duration_seconds    # Total execution time

# Methods
result.summary()           # Human-readable summary
result.to_dict()          # Convert to dictionary
result["step_name"]       # Access specific output
```

### Example: Inspecting Results

```python
result = pipeline.run()

if result.success:
    print(result.summary())

    # Access step results
    for step_name, step_result in result.step_results.items():
        print(f"Step: {step_name}")
        print(f"  Duration: {step_result.duration_seconds:.2f}s")
        print(f"  Cached: {step_result.cached}")
        if step_result.artifact_uri:
            print(f"  Artifact: {step_result.artifact_uri}")
```

## Pipeline Building

### Adding Steps

Steps are added in the order they should be registered with the pipeline:

```python
pipeline = Pipeline("ml_workflow")

# Add steps
pipeline.add_step(load_data)
pipeline.add_step(preprocess)
pipeline.add_step(train_model)
pipeline.add_step(evaluate)

# Add returns the pipeline for chaining
pipeline = (Pipeline("workflow")
    .add_step(step1)
    .add_step(step2)
    .add_step(step3)
)
```

### DAG Visualization

```python
# Build the DAG
pipeline.build()

# Visualize the execution graph
print(pipeline.dag.visualize())
```

Output:
```
Step Execution Order:
  1. load_data
  2. preprocess (depends on: load_data)
  3. train_model (depends on: preprocess)
  4. evaluate (depends on: train_model)
```

## Working with Stacks 🧩

Stacks define where and how your pipeline executes:

```python
from flowyml import LocalStack

# Create a local stack with custom paths
stack = LocalStack(
    artifact_path=".flowyml/artifacts",
    metadata_path=".flowyml/metadata.db"
)

# Use stack in pipeline
pipeline = Pipeline("my_pipeline", stack=stack)

# Or set at runtime
result = pipeline.run(stack=stack)
```

See the [Stack Architecture](../architecture/stacks.md) guide for more details on stacks.

## Advanced Features

### Conditional Execution

```python
from flowyml import when

@step(outputs=["data"])
def load():
    return {"quality": 0.95}

@step(inputs=["data"], outputs=["model"])
@when(lambda data: data["quality"] > 0.9)
def train(data):
    return "trained_model"

# train() only executes if quality > 0.9
```

### Parallel Execution

```python
from flowyml import parallel_map

@step
def process_batch(items):
    return parallel_map(expensive_function, items, num_workers=4)
```

### Error Handling

```python
from flowyml import retry, on_failure

@step
@retry(max_attempts=3, backoff=2.0)
@on_failure(fallback_function)
def flaky_step():
    # Retries up to 3 times with exponential backoff
    return fetch_external_data()
```

## Pipeline Patterns & Anti-Patterns

### ✅ Pattern: Environment-Agnostic Design

```python
# Same pipeline code works everywhere
ctx_dev = context(data_path="./local_data.csv", batch_size=32)
ctx_prod = context(data_path="gs://bucket/data.csv", batch_size=512)

# Development
pipeline = Pipeline("ml_training", context=ctx_dev)
pipeline.run()

# Production (same code!)
pipeline = Pipeline("ml_training", context=ctx_prod, stack=prod_stack)
pipeline.run()
```

**Why this works**: Zero code changes from dev to prod. Just swap context and stack.

### ❌ Anti-Pattern: Environment-Specific Branches

```python
# Don't do this!
@step(outputs=["data"])
def load_data():
    if os.getenv("ENV") == "production":
        return load_from_gcs()
    else:
        return load_from_local()
```

**Why it's bad**: Logic pollution, hard to test, environments drift apart.

**Fix**: Use context and stacks to handle environment differences.

---

### ✅ Pattern: Composition Over Inheritance

```python
# Reusable, composable steps
@step(outputs=["data"])
def load_csv(path: str):
    return pd.read_csv(path)

@step(inputs=["data"], outputs=["clean"])
def clean(data):
    return data.dropna()

# Build multiple pipelines from same steps
etl_pipeline = Pipeline("etl").add_step(load_csv).add_step(clean)
validation_pipeline = Pipeline("validation").add_step(load_csv).add_step(validate)
```

**Why this works**: Steps are building blocks. Mix and match for different workflows.

### ❌ Anti-Pattern: Monolithic Pipelines

```python
# Don't do this!
@step(outputs=["everything"])
def do_everything():
    data = load()
    clean = process(data)
    model = train(clean)
    metrics = evaluate(model)
    deploy(model)
    return metrics
```

**Why it's bad**: Can't cache parts, can't parallelize, can't reuse, hard to debug.

---

### ✅ Pattern: Fail Fast with Validation Steps

```python
@step(outputs=["data"])
def load_data():
    return fetch_data()

@step(inputs=["data"])
def validate_data(data):
    if len(data) < 100:
        raise ValueError("Insufficient data")
    if data['target'].isnull().any():
        raise ValueError("Missing target values")
    # Validation passes, no output needed

@step(inputs=["data"], outputs=["model"])
def train_model(data):
    # Only runs if validation passed
    return train(data)
```

**Why this works**: Catch problems early, save expensive compute on bad data.

---

## Decision Guide: When to Split Steps

| Scenario | Split? | Reason |
|----------|--------|--------|
| Step takes >5 minutes to run | ✅ Yes | Better caching granularity |
| Might want to run parts separately | ✅ Yes | Enables reuse |
| Operation is expensive (GPU, API calls) | ✅ Yes | Cache results independently |
| Tightly coupled operations (save + load same artifact) | ❌ No | Keep together for atomicity |
| Fast operations (<1 second) | ❌ Maybe | Balance overhead vs. benefit |

---

## Real-World Pipeline Examples

### ML Training Pipeline

```python
from flowyml import Pipeline, step, context
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

ctx = context(
    data_path="data/train.csv",
    test_size=0.2,
    n_estimators=100,
    random_state=42
)

@step(outputs=["raw_data"])
def load_data(data_path: str):
    return pd.read_csv(data_path)

@step(inputs=["raw_data"], outputs=["X_train", "X_test", "y_train", "y_test"])
def split_data(raw_data, test_size: float, random_state: int):
    X = raw_data.drop('target', axis=1)
    y = raw_data['target']
    return train_test_split(X, y, test_size=test_size, random_state=random_state)

@step(inputs=["X_train", "y_train"], outputs=["model"])
def train(X_train, y_train, n_estimators: int):
    model = RandomForestClassifier(n_estimators=n_estimators)
    model.fit(X_train, y_train)
    return model

@step(inputs=["model", "X_test", "y_test"], outputs=["accuracy"])
def evaluate(model, X_test, y_test):
    return model.score(X_test, y_test)

# Create pipeline with project (will create project if it doesn't exist)
pipeline = Pipeline("ml_training", context=ctx, project_name="ml_platform")
pipeline.add_step(load_data)
pipeline.add_step(split_data)
pipeline.add_step(train)
pipeline.add_step(evaluate)

result = pipeline.run()
print(f"Model accuracy: {result.outputs['accuracy']:.2%}")
```

**Why this design works**:
- Each step is independently cacheable
- Parameters in context, not hardcoded
- Can easily add more steps (preprocessing, feature engineering)
- Testable components

---

## Best Practices Summary

1. **Name descriptively**: `customer_churn_prediction` > `pipeline1`
2. **Explicit dependencies**: Always declare `inputs` and `outputs`
3. **One responsibility per step**: Split complex logic into focused steps
4. **Context for configuration**: Never hardcode parameters
5. **Enable caching in dev**: Speed up iteration, disable in prod if needed
6. **Fail fast**: Validate early, don't waste compute on bad data
7. **Test in isolation**: Each step should be unit-testable
8. **Document assumptions**: Use docstrings to explain step requirements
9. **Version your pipelines**: Use Git for pipeline code versioning
10. **Monitor in production**: Use the UI to track runs and catch failures

## Next Steps 📚

**Master the building blocks**:
- **[Steps](steps.md)**: Deep dive into step configuration, decorators, and best practices
- **[Context](context.md)**: Learn parameter injection patterns and environment management
- **[Assets](assets.md)**: Work with typed artifacts (Datasets, Models, Metrics)

**Level up your pipelines**:
- **[Caching](../advanced/caching.md)**: Optimize iteration speed with intelligent caching
- **[Conditional Execution](../advanced/conditional.md)**: Build adaptive workflows
- **[Parallel Execution](../advanced/parallel.md)**: Speed up independent operations
- **[Error Handling](../advanced/error-handling.md)**: Build resilient production pipelines

**Deploy to production**:
- **[Stack Architecture](../architecture/stacks.md)**: Understand local vs. cloud execution
- **[Projects](../user-guide/projects.md)**: Organize multi-tenant deployments
- **[Scheduling](../user-guide/scheduling.md)**: Automate recurring pipelines

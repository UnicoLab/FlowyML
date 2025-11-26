# Pipelines 🚀

Pipelines are the core abstraction in UniFlow. They represent a workflow of connected steps that transform data.

## Creating Your First Pipeline

A pipeline in UniFlow is created using the `Pipeline` class and decorated steps:

```python
from uniflow import Pipeline, step, context

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
```

## Pipeline Configuration ⚙️

The `Pipeline` class accepts several configuration options:

```python
from uniflow import Pipeline, context

ctx = context(
    learning_rate=0.001,
    batch_size=32
)

pipeline = Pipeline(
    name="training_pipeline",
    context=ctx,              # Context for parameter injection
    enable_cache=True,        # Enable intelligent caching
    cache_dir="./my_cache",   # Custom cache directory
    stack=my_stack            # Execution stack (local, cloud, etc.)
)
```

### Configuration Options

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `name` | `str` | Pipeline name (required) | - |
| `context` | `Context` | Context object for parameter injection | `Context()` |
| `executor` | `Executor` | Custom executor | `LocalExecutor()` |
| `enable_cache` | `bool` | Enable step caching | `True` |
| `cache_dir` | `str` | Cache storage directory | `.uniflow/cache` |
| `stack` | `Stack` | Execution stack (local/cloud) | `None` |

## Execution Graph (DAG) 🕸️

When you add steps to a pipeline, UniFlow builds a **Directed Acyclic Graph (DAG)**:

- **Nodes**: Steps in the pipeline
- **Edges**: Data dependencies between steps

UniFlow analyzes the `inputs` and `outputs` of each step to determine the execution order automatically.

```python
@step(outputs=["data"])
def step_a():
    return [1, 2, 3]

@step(inputs=["data"], outputs=["result"])  
def step_b(data):
    return sum(data)

# UniFlow automatically determines step_a must run before step_b
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
from uniflow import LocalStack

# Create a local stack with custom paths
stack = LocalStack(
    artifact_path=".uniflow/artifacts",
    metadata_path=".uniflow/metadata.db"
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
from uniflow import when

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
from uniflow import parallel_map

@step
def process_batch(items):
    return parallel_map(expensive_function, items, num_workers=4)
```

### Error Handling

```python
from uniflow import retry, on_failure

@step
@retry(max_attempts=3, backoff=2.0)
@on_failure(fallback_function)
def flaky_step():
    # Retries up to 3 times with exponential backoff
    return fetch_external_data()
```

## Best Practices 💡

### 1. Name Your Pipelines Descriptively

```python
# ✅ Good
pipeline = Pipeline("customer_churn_prediction")

# ❌ Bad
pipeline = Pipeline("pipeline1")
```

### 2. Define Clear Inputs and Outputs

```python
# ✅ Good - explicit dependencies
@step(inputs=["raw_data"], outputs=["clean_data"])
def clean(raw_data):
    return process(raw_data)

# ⚠️ Less clear
@step
def clean(data):
    return process(data)
```

### 3. Keep Steps Focused

Each step should do one thing well. Break complex operations into multiple steps.

### 4. Use Context for Configuration

```python
# ✅ Good - configuration in context
ctx = context(model_type="xgboost", max_depth=10)
pipeline = Pipeline("training", context=ctx)

# ❌ Bad - hardcoded values
@step
def train():
    model = XGBoost(max_depth=10)  # Hard to change
```

### 5. Enable Caching for Development

```python
# Fast iteration during development
pipeline = Pipeline("dev_pipeline", enable_cache=True)

# Disable for production runs
pipeline = Pipeline("prod_pipeline", enable_cache=False)
```

## Next Steps 📚

- **[Steps](steps.md)**: Master step configuration and decorators
- **[Context](context.md)**: Learn about parameter injection
- **[Caching](caching.md)**: Understand intelligent caching
- **[Artifacts](artifacts.md)**: Work with datasets and models

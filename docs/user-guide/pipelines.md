# Pipelines 🚀

Pipelines are the core abstraction in UniFlow. They represent a workflow of connected steps that transform data.

## Defining Pipelines

UniFlow supports two ways to define pipelines: **Declarative** (recommended) and **Imperative**.

### Declarative Style

The declarative style uses the `@pipeline` decorator. This is the most pythonic way to define pipelines and allows UniFlow to inspect the graph structure easily.

```python
from uniflow import pipeline, step

@step
def extract():
    return [1, 2, 3]

@step
def transform(data):
    return [x * 2 for x in data]

@pipeline
def etl_pipeline():
    # Define the flow naturally
    data = extract()
    result = transform(data)
    return result
```

!!! tip "Why Declarative?"
    Declarative pipelines are easier to read and allow UniFlow to perform static analysis, optimization, and better visualization in the UI.

### Imperative Style

The imperative style involves manually creating a `Pipeline` object and adding steps. This is useful for dynamic pipeline construction.

```python
from uniflow import Pipeline

p = Pipeline("etl_pipeline")
p.add_step(extract)
p.add_step(transform)
```

## Execution Graph (DAG) 🕸️

When you define a pipeline, UniFlow builds a **Directed Acyclic Graph (DAG)**.
- **Nodes**: Steps in the pipeline.
- **Edges**: Data dependencies between steps.

UniFlow analyzes the inputs and outputs of each step to determine the execution order. If Step B requires an output from Step A, Step A will always run first.

## Pipeline Configuration ⚙️

You can configure pipelines with various options:

```python
@pipeline(
    name="training_pipeline",
    context=my_context,
    enable_cache=True,
    cache_dir="./custom_cache"
)
def my_pipeline():
    ...
```

## Running Pipelines ▶️

To run a pipeline, simply call it like a function (if using declarative style) or call `.run()` (if using imperative style).

```python
# Declarative
run = etl_pipeline()

# Imperative
run = p.run()
```

### The `PipelineRun` Object

The result of a pipeline execution is a `PipelineRun` object, which contains:
- `success`: Boolean indicating overall status.
- `result`: The return value of the pipeline function.
- `outputs`: A dictionary of all step outputs.
- `step_results`: Detailed results for each step (success, duration, logs).

```python
if run.success:
    print(f"Pipeline finished in {run.duration}s")
    print(f"Final output: {run.result}")
else:
    print(f"Pipeline failed: {run.error}")
```

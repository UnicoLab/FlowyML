# Dynamic Workflows

Dynamic workflows let steps generate sub-pipelines at runtime based on intermediate results. The generated DAG is expanded and executed inline.

## Basic Usage

```python
from flowyml import dynamic, Pipeline, step

@dynamic(outputs=["best_model"])
def hyperparameter_search(config: dict):
    sub = Pipeline("hp_search")

    for lr in config["learning_rates"]:
        @step(outputs=[f"model_lr_{lr}"])
        def train(learning_rate=lr):
            return train_model(learning_rate)
        sub.add_step(train)

    return sub

# Use in pipeline
pipeline.add_step(hyperparameter_search)
```

## How It Works

1. The `@dynamic` function executes like a normal step
2. It returns a `Pipeline` object (the sub-pipeline)
3. The sub-pipeline is built and executed inline
4. Results are wrapped in `DynamicWorkflowResult`

## Use Cases

- **Hyperparameter sweeps**: generate training runs based on search space
- **Conditional fan-out**: create branches based on data properties
- **Data-driven pipelines**: structure depends on input characteristics

## Direct Results

If your dynamic function returns a non-Pipeline value, it's treated as a direct result:

```python
@dynamic
def maybe_expand(data: dict):
    if data["size"] < 100:
        return simple_transform(data)  # Direct result
    return build_complex_pipeline(data)  # Returns Pipeline
```

# Conditional Execution 🔀

flowyml supports dynamic pipeline execution paths based on runtime conditions. Build smart workflows that adapt to data quality, model performance, or external factors.

!!! info "What you'll learn"
    How to build adaptive pipelines that change behavior based on data. Real-world pipelines aren't linear — they need to make decisions.

## Why Conditional Logic Matters

**Without conditional logic**:
- **Manual intervention**: Stopping pipelines manually if accuracy is low
- **Rigid workflows**: One size fits all, regardless of data volume or quality
- **Separate pipelines**: Maintaining "Training" and "Deployment" pipelines separately

**With flowyml conditional logic**:
- **Automated decisions**: "If accuracy > 90%, deploy. Else, retrain."
- **Adaptive behavior**: "If data > 1GB, use Spark. Else, use Pandas."
- **Unified workflows**: Handle edge cases within the same pipeline

## Conditional Patterns

## 🔀 Conditional Steps

You can use the `conditional` decorator or utility to define branching logic.

### Using `If` Condition

```python
from flowyml import Pipeline, step, If

@step(outputs=["accuracy"])
def evaluate_model():
    return 0.95

@step
def deploy_model():
    print("Deploying model...")

@step
def retrain_model():
    print("Retraining model...")

pipeline = Pipeline("conditional_deploy")

pipeline.add_step(evaluate_model)

# Define conditional logic
# If accuracy > 0.9, run deploy_model, else run retrain_model
pipeline.add_control_flow(
    If(
        condition=lambda ctx: ctx.steps['evaluate_model'].outputs['accuracy'] > 0.9,
        then_step=deploy_model,
        else_step=retrain_model
    )
)
```

### Skipping Steps

You can also conditionally skip steps.

```python
@step(skip_if=lambda ctx: ctx.params['dry_run'] is True)
def upload_to_s3(data):
    # This will be skipped if dry_run is True
    s3.upload(data)
```

## The Execution Context (`ctx`)

When writing conditions, you have access to a rich `ctx` object that allows you to inspect the state of the entire pipeline run.

### Accessing Step Outputs

You can access the outputs of previous steps using `ctx.steps`:

```python
# Accessing a simple value
condition=lambda ctx: ctx.steps['evaluate'].outputs['accuracy'] > 0.9

# Accessing multiple outputs
condition=lambda ctx: ctx.steps['data_loader'].outputs['train_size'] > 1000
```

### Working with Assets (Typed Artifacts)

If your steps return `Model`, `Dataset`, or `Metrics` objects, you can access their metadata directly:

```python
# Accessing Model accuracy from metadata
condition=lambda ctx: ctx.steps['train'].outputs['model'].metadata['accuracy'] > 0.9

# Accessing Dataset statistics
condition=lambda ctx: ctx.steps['load'].outputs['dataset'].statistics['row_count'] > 0
```

!!! note "Asset Metadata"
    The `metadata` attribute in the context is a merged dictionary containing both the Asset's `properties` and `tags`.

### Accessing Context Parameters

You can access pipeline parameters defined in your `context()`:

```python
# Using context parameters in conditions
condition=lambda ctx: ctx.params['environment'] == 'production'
```

## Detailed Pattern Examples

### Pattern 1: Metrics-Based Deployment
Use `Metrics` assets to make complex decisions.

```python
from flowyml import Pipeline, step, If, Metrics

@step(outputs=["eval_metrics"])
def evaluate() -> Metrics:
    return Metrics({"f1_score": 0.92, "latency_ms": 150})

pipeline.add_control_flow(
    If(
        condition=lambda ctx: (
            ctx.steps['evaluate'].outputs['eval_metrics']['f1_score'] > 0.9 and
            ctx.steps['evaluate'].outputs['eval_metrics']['latency_ms'] < 200
        ),
        then_step=deploy_prod,
        else_step=send_alert
    )
)
```

### Pattern 2: Multi-Environment Logic
Build one pipeline that behaves differently based on the environment.

```python
@step
def smoke_test():
    print("Running quick smoke test...")

@step
def full_validation():
    print("Running comprehensive validation suite...")

pipeline.add_control_flow(
    If(
        condition=lambda ctx: ctx.params['env'] == 'dev',
        then_step=smoke_test,
        else_step=full_validation
    )
)
```

## Decision Guide: Control Flow

| Pattern | Use When | Example |
|---------|----------|---------|
| `If / Switch` | **Branching logic**: Choose between different paths | Deploy vs. Retrain |
| `skip_if` | **Optional steps**: Skip a step based on a flag | Skip upload in `dry_run` |
| `Asset Access` | **Data-driven decisions**: Branch based on metrics | Deploy if F1 > 0.9 |

!!! tip "Best Practice"
    Keep conditions simple. If your logic is complex, move it into a dedicated `@step` that outputs a boolean flag, then check that flag in the `If` condition.

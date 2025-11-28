# Conditional Execution 🔀

UniFlow supports dynamic pipeline execution paths based on runtime conditions. Build smart workflows that adapt to data quality, model performance, or external factors.

> [!NOTE]
> **What you'll learn**: How to build adaptive pipelines that change behavior based on data
>
> **Key insight**: Real-world pipelines aren't linear. They need to make decisions (e.g., "Is this model good enough to deploy?").

## Why Conditional Logic Matters

**Without conditional logic**:
- **Manual intervention**: Stopping pipelines manually if accuracy is low
- **Rigid workflows**: One size fits all, regardless of data volume or quality
- **Separate pipelines**: Maintaining "Training" and "Deployment" pipelines separately

**With UniFlow conditional logic**:
- **Automated decisions**: "If accuracy > 90%, deploy. Else, retrain."
- **Adaptive behavior**: "If data > 1GB, use Spark. Else, use Pandas."
- **Unified workflows**: Handle edge cases within the same pipeline

## Conditional Patterns

## 🔀 Conditional Steps

You can use the `conditional` decorator or utility to define branching logic.

### Using `If` Condition

```python
from uniflow import Pipeline, step, If

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

## Decision Guide: Control Flow

| Pattern | Use When | Example |
|---------|----------|---------|
| `If / Switch` | **Branching logic**: Choose between different paths | Deploy vs. Retrain |
| `skip_if` | **Optional steps**: Skip a step based on a flag | Skip upload in `dry_run` |
| Dynamic DAG | **Complex routing**: Structure depends on data | Route A for images, Route B for text |

### Pattern 1: The Deployment Gate

The most common pattern: only deploy if the model meets a threshold.

```python
from uniflow import If

pipeline.add_control_flow(
    If(condition=lambda ctx: ctx["accuracy"] > 0.95)
    .then(deploy_to_prod)
    .else_(notify_slack_failure)
)
```

### Pattern 2: The Dry Run

Skip side-effects when testing.

```python
@step(skip_if=lambda ctx: ctx.params.get("dry_run", False))
def upload_to_s3(data):
    # This won't run if dry_run=True
    s3.upload(data)
```

> [!TIP]
> **Best Practice**: Keep conditions simple. If your logic is complex, move it into a dedicated `@step` that outputs a boolean flag, then check that flag in the `If` condition.

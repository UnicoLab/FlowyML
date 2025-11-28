# Conditional Execution 🔀

UniFlow supports dynamic pipeline execution paths based on runtime conditions. This allows you to build flexible workflows that adapt to data quality, model performance, or external factors.

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

## 🔄 Dynamic DAGs

For more complex scenarios, you can dynamically construct the DAG at runtime.

```python
@step
def decide_path(data):
    if data['type'] == 'image':
        return 'image_processing'
    else:
        return 'text_processing'

# Note: Dynamic DAG modification is an advanced feature and requires careful handling of dependencies.
```

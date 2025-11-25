# Context & Parameters 🧠

UniFlow provides a powerful context system that allows you to manage parameters, configuration, and runtime state across your pipeline steps without manual plumbing.

## The Context Object

The `Context` object serves as a container for:
1.  **Global Parameters**: Hyperparameters, configuration settings, environment variables.
2.  **Runtime State**: Information about the current run, execution timestamp, etc.
3.  **Dependency Injection**: Automatically providing parameters to steps that need them.

### Creating a Context

You can create a context with any number of keyword arguments:

```python
from uniflow import context

# Define parameters
ctx = context(
    learning_rate=0.001,
    batch_size=64,
    model_type="resnet50",
    random_seed=42
)
```

## Automatic Injection 💉

The most powerful feature of UniFlow's context is **automatic injection**. If a step function argument matches a key in the context, UniFlow will automatically inject the value when the step is executed.

### Example

```python
from uniflow import step, pipeline, context

# 1. Define Context
ctx = context(
    lr=0.01,
    epochs=10
)

# 2. Define Step with matching arguments
@step
def train_model(data, lr: float, epochs: int):
    # 'lr' and 'epochs' are automatically injected from context!
    print(f"Training with lr={lr}, epochs={epochs}")
    return "model"

# 3. Run Pipeline with Context
@pipeline(context=ctx)
def my_pipeline():
    # No need to pass lr/epochs manually!
    return train_model(data="raw_data")
```

!!! note "Clean Code"
    This keeps your pipeline definitions clean and separates configuration from logic.

## Parameter Overrides 🔄

You can override context parameters at runtime when executing the pipeline:

```python
# Override 'epochs' for this specific run
my_pipeline(context={"epochs": 20})
```

## Accessing Context Manually 🖐️

If you need to access the full context object within a step (e.g., to access dynamic properties), you can request the `context` object itself:

```python
@step
def dynamic_step(context):
    # Access any parameter
    print(context.params)
    
    # Access run ID
    print(context.run_id)
```

## Best Practices 🌟

1.  **Group Parameters**: Use nested dictionaries for related parameters (e.g., `model_params={...}`).
2.  **Type Hints**: Always use type hints in your step functions. UniFlow uses them for validation.
3.  **Defaults**: Provide default values in your step functions for optional parameters.

```python
@step
def robust_step(param1, optional_param: str = "default"):
    ...
```

# Steps 👣

Steps are the atomic units of work in a UniFlow pipeline. They are regular Python functions wrapped with the `@step` decorator.

## Anatomy of a Step

A step is defined by decorating a function with `@step`.

```python
from uniflow import step

@step
def my_step(input_data):
    # Do some work
    return processed_data
```

## Configuration 🛠️

The `@step` decorator accepts several arguments to control behavior:

| Argument | Type | Description | Default |
|----------|------|-------------|---------|
| `inputs` | `List[str]` | Names of input assets required by this step. | `[]` |
| `outputs` | `List[str]` | Names of output assets produced by this step. | `[]` |
| `cache` | `str` \| `bool` | Caching strategy (`"code_hash"`, `"input_hash"`, `False`). | `"code_hash"` |
| `retry` | `int` | Number of times to retry on failure. | `0` |
| `timeout` | `int` | Maximum execution time in seconds. | `None` |
| `resources` | `dict` | Resource requirements (e.g., `{"gpu": 1}`). | `None` |

### Example with Configuration

```python
@step(
    inputs=["raw_dataset"],
    outputs=["trained_model"],
    retry=3,
    timeout=3600,
    resources={"gpu": 1}
)
def train_model(raw_dataset, learning_rate: float):
    ...
```

## Inputs and Outputs 🔌

UniFlow uses variable names to wire steps together.

### Implicit Wiring (Recommended)
When using the declarative pipeline style, you pass the output of one step as the input to another. UniFlow handles the wiring automatically.

```python
@pipeline
def flow():
    data = load_data()      # Returns a proxy object
    model = train(data)     # Passes the proxy to the next step
```

### Explicit Wiring
You can also explicitly name inputs and outputs. This is useful when steps are decoupled or when using the imperative style.

```python
@step(outputs=["my_data"])
def producer():
    return [1, 2, 3]

@step(inputs=["my_data"])
def consumer(my_data):
    print(my_data)
```

## Multiple Outputs 📦

A step can return multiple values. If `outputs` is defined, the return value should match the number of outputs.

```python
@step(outputs=["train_data", "test_data"])
def split_data(data):
    # ... logic ...
    return train_set, test_set
```

## Context Access 🧠

Steps can access the global pipeline context. Parameters in the context are automatically injected if the step function arguments match the parameter names.

```python
# Context has {"lr": 0.01}
@step
def train(data, lr: float):
    # lr is 0.01
    ...
```

!!! info "Learn More"
    See [Context & Parameters](context.md) for more details on dependency injection.

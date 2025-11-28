# Context & Parameters 🧠

UniFlow's context system eliminates configuration hell by providing automatic parameter injection across pipeline steps.

> [!NOTE]
> **What you'll learn**: How to manage configuration without hardcoding, enabling the same pipeline to run in dev/staging/prod
>
> **Key insight**: Context separates **what** your pipeline does from **how** it's configured. Change parameters, not code.

## Why Context Matters

**Without context**, ML pipelines suffer from:
- **Hardcoded parameters**: `learning_rate = 0.001` buried in code
- **Environment coupling**: Different code for dev vs. prod
- **Configuration sprawl**: Parameters scattered across files
- **Manual wiring**: Pass every parameter through every function

**With UniFlow context**, you get:
- **Automatic injection**: Parameters flow to steps that need them
- **Environment flexibility**: Same code, different configs
- **Centralized configuration**: All parameters in one place
- **Type safety**: Type hints validate parameters automatically

> [!TIP]
> **The killer feature**: Run the same pipeline with different configs just by swapping context. No code changes to go from dev (small dataset, CPU) to prod (full dataset, GPU).

## The Context Object

The `Context` object serves as a container for:
1. **Global Parameters**: Hyperparameters, configuration settings
2. **Environment Variables**: Paths, endpoints, credentials
3. **Runtime Settings**: Batch sizes, resource requirements
4. **Domain Logic**: Business rules, thresholds

### Creating a Context

You can create a context with any number of keyword arguments:

```python
from uniflow import context

# Define parameters
ctx = context(
    learning_rate=0.001,
    batch_size=64,
    model_type="resnet50",
    random_seed=42,
    data_path="./data/train.csv"
)
```

### Using Context with Pipelines

```python
from uniflow import Pipeline, context

ctx = context(learning_rate=0.01, epochs=100)

# Pass context to pipeline
pipeline = Pipeline("training_pipeline", context=ctx)
```

## Automatic Injection 💉

The most powerful feature of UniFlow's context is **automatic parameter injection**. If a step function argument matches a key in the context, UniFlow will automatically inject the value when the step is executed.

### Example

```python
from uniflow import Pipeline, step, context

# 1. Define Context
ctx = context(
    learning_rate=0.01,
    epochs=10,
    batch_size=32
)

# 2. Define Steps with matching parameter names
@step(outputs=["model"])
def train_model(data, learning_rate: float, epochs: int):
    # 'learning_rate' and 'epochs' are automatically injected from context!
    print(f"Training with lr={learning_rate}, epochs={epochs}")
    model = train(data, lr=learning_rate, epochs=epochs)
    return model

@step(inputs=["model"], outputs=["metrics"])
def evaluate(model, batch_size: int):
    # 'batch_size' automatically injected!
    return evaluate_model(model, batch_size=batch_size)

# 3. Create Pipeline with Context
pipeline = Pipeline("ml_pipeline", context=ctx)
pipeline.add_step(train_model)
pipeline.add_step(evaluate)

# 4. Run - parameters automatically injected!
result = pipeline.run()
```

### How It Works

1. **Parameter Matching**: UniFlow inspects each step function's signature
2. **Context Lookup**: For each parameter, it checks if a matching key exists in the context
3. **Automatic Injection**: If found, the value is injected when calling the step
4. **Type Validation**: Type hints are used to validate injected values

```python
# This step signature:
def train(data, learning_rate: float, epochs: int):
    ...

# With this context:
ctx = context(learning_rate=0.01, epochs=100)

# Results in this call:
train(data=previous_output, learning_rate=0.01, epochs=100)
```

## Parameter Overrides 🔄

You can override context parameters at runtime:

```python
# Original context
ctx = context(learning_rate=0.01, epochs=10)
pipeline = Pipeline("training", context=ctx)

# Override for this specific run
result = pipeline.run(context={"epochs": 20, "learning_rate": 0.05})
# Now uses epochs=20 and learning_rate=0.05
```

### Use Cases for Overrides

1. **Experimentation**: Try different hyperparameters quickly
2. **Production vs Development**: Different settings for different environments
3. **A/B Testing**: Run same pipeline with variations

```python
# Compare different learning rates
for lr in [0.001, 0.01, 0.1]:
    result = pipeline.run(context={"learning_rate": lr})
    print(f"LR={lr}: accuracy={result.outputs['metrics'].accuracy}")
```

## Context Updates

You can also update the context dynamically:

```python
ctx = context(epochs=10)

# Update context
ctx.update({"learning_rate": 0.01, "batch_size": 32})

# Now context has all three parameters
```

## Accessing Context Data 🔍

### Individual Parameters

Most commonly, you just declare parameters in your step function:

```python
@step
def my_step(param1: str, param2: int):
    # param1 and param2 injected from context
    print(f"{param1}, {param2}")
```

### Full Context Access

If you need access to the entire context object:

```python
@step
def inspect_context(context):
    # Access all parameters
    print(f"All params: {context.to_dict()}")

    # Check if parameter exists
    if "optional_param" in context:
        use_param(context["optional_param"])
```

### Context Properties

The Context object provides useful methods:

```python
ctx = context(a=1, b=2, c=3)

# Convert to dictionary
params_dict = ctx.to_dict()  # {"a": 1, "b": 2, "c": 3}

# Iterate over parameters
for key, value in ctx.items():
    print(f"{key}={value}")

# Get keys
keys = list(ctx.keys())  # ["a", "b", "c"]

# Check membership
if "a" in ctx:
    print(ctx["a"])
```

## Mixing Input Data and Context Parameters

Steps can receive both pipeline data (from previous steps) and context parameters:

```python
@step(outputs=["data"])
def load_data(file_path: str):
    # file_path from context
    return pd.read_csv(file_path)

@step(inputs=["data"], outputs=["processed"])
def process(data, threshold: float, normalize: bool):
    # 'data' from previous step (load_data output)
    # 'threshold' and 'normalize' from context
    if normalize:
        data = normalize_data(data)
    return filter_by_threshold(data, threshold)

ctx = context(
    file_path="data/train.csv",
    threshold=0.5,
    normalize=True
)
```

## Type Hints and Validation 🎯

Type hints serve two purposes:

1. **Documentation**: Clarify expected types
2. **Validation**: Help UniFlow match parameters correctly

```python
from typing import List, Dict, Optional

@step
def train(
    data: List[float],           # From previous step
    learning_rate: float,        # From context - must be float
    layers: List[int],           # From context - must be list of ints
    config: Dict[str, any],      # From context - must be dict
    optional_param: Optional[str] = None  # Optional context parameter
):
    ...

ctx = context(
    learning_rate=0.01,          # ✓ Matches type
    layers=[128, 64, 32],        # ✓ Matches type
    config={"dropout": 0.5},     # ✓ Matches type
    # optional_param not provided - uses default None
)
```

## Advanced Patterns

### Environment-Specific Contexts

```python
import os

def get_context():
    env = os.getenv("ENV", "development")

    if env == "production":
        return context(
            data_path="s3://prod-bucket/data",
            batch_size=256,
            use_gpu=True
        )
    else:
        return context(
            data_path="./local_data",
            batch_size=32,
            use_gpu=False
        )

pipeline = Pipeline("adaptive", context=get_context())
```

### Nested Configuration

```python
ctx = context(
    model_config={
        "type": "transformer",
        "hidden_size": 768,
        "num_layers": 12
    },
    training_config={
        "learning_rate": 0.001,
        "warmup_steps": 1000
    }
)

@step
def train(model_config: dict, training_config: dict):
    # Access nested configuration
    model = create_model(**model_config)
    optimizer = create_optimizer(**training_config)
    ...
```

### Context Inheritance

```python
# Base context
base_ctx = context(
    random_seed=42,
    verbose=True
)

# Extend for specific use case
training_ctx = context(
    **base_ctx.to_dict(),
    learning_rate=0.01,
    epochs=100
)
```

## Best Practices 🌟

### 1. Use Descriptive Parameter Names

```python
# ✅ Good - clear and specific
ctx = context(
    learning_rate=0.01,
    max_epochs=100,
    early_stopping_patience=10
)

# ❌ Bad - unclear abbreviations
ctx = context(
    lr=0.01,
    e=100,
    p=10
)
```

### 2. Always Use Type Hints

```python
# ✅ Good - types make injection reliable
@step
def process(data, threshold: float, iterations: int):
    ...

# ⚠️ Less ideal - no type information
@step
def process(data, threshold, iterations):
    ...
```

### 3. Provide Sensible Defaults

```python
# ✅ Good - works with or without context values
@step
def train(
    data,
    learning_rate: float = 0.001,
    epochs: int = 10,
    verbose: bool = False
):
    ...

# Can run without providing these in context
```

### 4. Group Related Parameters

```python
# ✅ Good - organized into logical groups
ctx = context(
    # Data parameters
    data_path="./data",
    validation_split=0.2,

    # Model parameters
    model_type="resnet50",
    pretrained=True,

    # Training parameters
    learning_rate=0.001,
    batch_size=32,
    epochs=100
)
```

### 5. Document Your Context Requirements

```python
def create_training_pipeline(context):
    """Create a training pipeline.

    Required context parameters:
        - data_path (str): Path to training data
        - learning_rate (float): Learning rate for optimizer
        - epochs (int): Number of training epochs

    Optional context parameters:
        - batch_size (int): Batch size, default 32
        - random_seed (int): Random seed, default 42
    """
    pipeline = Pipeline("training", context=context)
    # ...
    return pipeline
```

## Debugging Context Issues 🔧

### Check Context Contents

```python
ctx = context(a=1, b=2, c=3)

# Print all parameters
print(ctx.to_dict())

# Check during pipeline execution
pipeline = Pipeline("debug", context=ctx)
result = pipeline.run(debug=True)  # Shows parameter injection
```

### Missing Parameter Errors

If a step requires a parameter not in the context or previous outputs:

```python
@step
def needs_param(required_param: str):
    ...

# If context doesn't have 'required_param', execution fails
pipeline.run()  # Error: Missing required parameters: ['required_param']
```

## Next Steps 📚

- **[Pipelines](pipelines.md)**: Learn how to build workflows
- **[Steps](steps.md)**: Master step configuration
- **[Configuration](configuration.md)**: External configuration files
- **[Caching](caching.md)**: Understand caching with context

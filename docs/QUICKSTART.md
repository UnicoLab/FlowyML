# 🌊 Flowy - Quick Start Guide

## Installation

```bash
# Install from source
cd flowy_package
pip install -e .

# Or install with extras
pip install -e ".[pytorch]"
pip install -e ".[ui]"      # With UI support
pip install -e ".[all]"     # Everything
```

## 🖥️ UI Setup (Optional but Recommended)

Get real-time visualization of your pipelines:

```bash
# 1. Install with UI support
pip install -e ".[ui]"

# 2. Build the frontend (one-time setup)
cd flowy/ui/frontend
npm install
npm run build
cd ../../..

# 3. Start the UI server
flowy ui start --open-browser

# 4. Check it's running
flowy ui status
```

Now you can monitor pipelines at **http://localhost:8080**!

**See [UI_GUIDE.md](UI_GUIDE.md) for detailed instructions.**


## Your First Pipeline in 5 Minutes

### 1. Basic Pipeline with Context Injection

The killer feature of Flowy is **automatic parameter injection** - no more manual wiring!

```python
from flowy import Pipeline, step, context

# Define context once
ctx = context(
    learning_rate=0.001,
    epochs=10,
    batch_size=32,
    model_type="resnet50"
)

# Parameters automatically injected based on function signature!
@step(outputs=["model"])
def train_model(learning_rate: float, epochs: int, model_type: str):
    print(f"Training {model_type} with lr={learning_rate} for {epochs} epochs")
    # Your training code here
    return {"type": model_type, "accuracy": 0.95}

# Create and run
pipeline = Pipeline("my_first_pipeline", context=ctx)
pipeline.add_step(train_model)

result = pipeline.run(debug=True)
print(f"Model trained: {result['model']}")
```

### 2. Asset-Centric Pipeline

Track your ML assets (datasets, models, metrics) with full lineage:

```python
from flowy import Dataset, Model, Metrics

@step(outputs=["dataset"])
def load_data(data_path: str):
    # Load your data
    data = load_from_disk(data_path)
    
    # Return as Dataset asset
    return Dataset.create(
        data=data,
        name="training_data",
        properties={"samples": len(data)}
    )

@step(inputs=["dataset"], outputs=["model", "metrics"])
def train(dataset: Dataset, learning_rate: float):
    # Train model
    model = train_on_data(dataset.data, lr=learning_rate)
    
    # Return Model and Metrics with lineage
    return (
        Model.create(
            data=model,
            name="trained_model",
            trained_on=dataset  # Automatic lineage!
        ),
        Metrics.create(accuracy=0.95, loss=0.05)
    )
```

### 3. Caching for Fast Iterations

Flowy automatically caches step outputs to speed up development:

```python
@step(outputs=["processed"], cache="code_hash")
def expensive_preprocessing(raw_data):
    # This only runs once until you change the code
    return process(raw_data)

# First run: executes preprocessing
result1 = pipeline.run()

# Second run: uses cache! 100x faster
result2 = pipeline.run()

# Check cache stats
print(pipeline.cache_stats())
```

### 4. Experiment Tracking

Track multiple runs and compare results:

```python
from flowy import Experiment

exp = Experiment(
    name="hyperparameter_tuning",
    description="Testing different learning rates"
)

# Run multiple experiments
for lr in [0.001, 0.01, 0.1]:
    ctx = context(learning_rate=lr, epochs=10)
    pipeline = Pipeline(f"lr_{lr}", context=ctx)
    # ... add steps ...
    
    result = pipeline.run()
    exp.log_run(
        result.run_id,
        metrics={"accuracy": result["metrics"].get_metric("accuracy")},
        parameters={"learning_rate": lr}
    )

# Find best run
best = exp.get_best_run(metric="accuracy", maximize=True)
print(f"Best learning rate: {best}")
```

## Key Concepts

### Context Management

Context provides automatic parameter injection:

```python
ctx = context(
    # Training params
    learning_rate=0.001,
    epochs=10,
    
    # Data params
    data_path="./data",
    batch_size=32,
    
    # Infrastructure
    device="cuda",
    num_workers=4
)

# All these parameters are automatically available to steps!
```

### Step Decorator

The `@step` decorator defines pipeline steps:

```python
@step(
    inputs=["input_asset"],      # Input asset names
    outputs=["output_asset"],    # Output asset names
    cache="code_hash",           # Caching strategy
    retry=3,                     # Retry on failure
    timeout=3600                 # Timeout in seconds
)
def my_step(input_asset, param_from_context: float):
    # Your logic here
    return result
```

### Assets

First-class objects with lineage tracking:

- `Dataset` - Training/test data
- `Model` - Trained models
- `Metrics` - Evaluation metrics
- `Artifact` - Generic artifacts (configs, checkpoints)

### Caching Strategies

- `"code_hash"` - Cache until code changes
- `"input_hash"` - Cache based on inputs
- `False` - Disable caching
- Custom function for advanced control

## Common Patterns

### Data Processing Pipeline

```python
@step(outputs=["raw_data"])
def load():
    return Dataset.create(data=load_csv("data.csv"))

@step(inputs=["raw_data"], outputs=["clean_data"])
def clean(raw_data: Dataset):
    cleaned = remove_nulls(raw_data.data)
    return Dataset.create(data=cleaned, parent=raw_data)

@step(inputs=["clean_data"], outputs=["features"])
def extract_features(clean_data: Dataset):
    features = compute_features(clean_data.data)
    return Dataset.create(data=features, parent=clean_data)
```

### Training Pipeline

```python
@step(outputs=["train_data", "test_data"])
def split_data():
    train, test = load_and_split()
    return (
        Dataset.create(data=train, name="train"),
        Dataset.create(data=test, name="test")
    )

@step(inputs=["train_data"], outputs=["model"])
def train(train_data: Dataset, lr: float, epochs: int):
    model = train_model(train_data.data, lr, epochs)
    return Model.create(data=model, trained_on=train_data)

@step(inputs=["model", "test_data"], outputs=["metrics"])
def evaluate(model: Model, test_data: Dataset):
    acc = evaluate_model(model.data, test_data.data)
    return Metrics.create(accuracy=acc)
```

### Pipeline with Branches

```python
@step(outputs=["data"])
def load():
    return load_data()

# Two parallel branches
@step(inputs=["data"], outputs=["model_a"])
def train_model_a(data):
    return train_resnet(data)

@step(inputs=["data"], outputs=["model_b"])
def train_model_b(data):
    return train_vgg(data)

# Merge branches
@step(inputs=["model_a", "model_b"], outputs=["comparison"])
def compare(model_a, model_b):
    return {"best": select_best(model_a, model_b)}
```

## Tips & Best Practices

1. **Use Context for Configuration** - Put all hyperparameters in context
2. **Enable Caching During Development** - Speeds up iterations dramatically
3. **Use Assets for Important Objects** - Datasets, models, metrics
4. **Run with debug=True** - See detailed execution logs
5. **Track Experiments** - Compare different runs systematically

## Next Steps

- Read the full documentation
- Check out advanced examples
- Join the community
- Contribute to the project!

---

**Welcome to the future of ML pipelines! 🌊**

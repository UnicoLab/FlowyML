---
title: Cheatsheet — FlowyML
description: "Quick reference guide for common FlowyML commands, patterns, and recipes."
---

<div class="hero-section" markdown>

## 📝 Cheatsheet

A quick reference guide for common FlowyML commands, patterns, and recipes. Bookmark this page for instant access to the syntax you need.

<span class="feature-badge">💻 CLI</span>
<span class="feature-badge">🐍 Python API</span>
<span class="feature-badge">🎯 Patterns</span>

</div>

## CLI Commands 💻

### Project Management
```bash
# Initialize a new project
flowyml init my-project

# Initialize with a specific template
flowyml init my-project --template basic
```

### UI Management
```bash
# Start the UI server
flowyml ui start

# Stop the UI server
flowyml ui stop

# Check UI status
flowyml ui status
```

### Pipeline Execution
```bash
# Run a pipeline script
python my_pipeline.py

# Run with specific configuration
FLOWYML_ENV=production python my_pipeline.py
```

### Cache Management
```bash
# Clear all cache
flowyml cache clear

# Clear cache for specific pipeline
flowyml cache clear --pipeline my_pipeline
```

## Python API 🐍

### Basic Pipeline
```python
from flowyml import Pipeline, step

@step(outputs=["data"])
def step_one():
    return "data"

@step(inputs=["data"])
def step_two(data):
    return f"processed {data}"

# Create and run pipeline
pipeline = Pipeline("my_pipeline")
pipeline.add_step(step_one)
pipeline.add_step(step_two)
result = pipeline.run()
```

### Explicit Pipeline Construction
```python
from flowyml import Pipeline, step

p = Pipeline("explicit_pipeline")
p.add_step(step_one)
p.add_step(step_two)
p.run()
```

### Step Configuration
```python
@step(
    inputs=["raw_data"],       # Input asset names
    outputs=["model"],         # Output asset names
    cache="code_hash",         # Caching strategy
    retry=3,                   # Retry attempts
    timeout=3600,              # Timeout in seconds
    resources={"gpu": 1}       # Resource requirements
)
def train(raw_data):
    ...
```

### Context & Parameters
```python
from flowyml import context, pipeline

# Define context with parameters
ctx = context(
    learning_rate=0.01,
    batch_size=32,
    env="dev"
)

@step
def train(learning_rate, batch_size):
    # Parameters are auto-injected by name!
    ...

@pipeline(context=ctx)
def train_pipeline():
    return train()
```

### Assets
```python
from flowyml import Dataset, Model, Metrics

# Create a dataset
ds = Dataset.create(
    data=df,
    name="training_data",
    properties={"source": "s3://..."}
)

# Create metrics
metrics = Metrics.create(
    accuracy=0.95,
    loss=0.02
)
```

## Directory Structure 📂

```
my-project/
├── flowyml.yaml         # Project configuration
├── .flowyml/            # Internal storage
│   ├── artifacts/       # Stored assets
│   ├── cache/           # Execution cache
│   └── runs/            # Run metadata
├── src/                 # Source code
│   └── pipelines/       # Pipeline definitions
└── notebooks/           # Jupyter notebooks
```

## Evaluations 🎯

```python
from flowyml import step, evaluate
from flowyml.evaluations import accuracy, precision, f1_score

@step(inputs=["model", "test_data"], outputs=["eval_results"])
def evaluate_model(model, test_data):
    results = evaluate(
        model=model,
        data=test_data,
        scorers=[accuracy, precision, f1_score],
        quality_gate={"accuracy": 0.9}  # Fail if below
    )
    return results
```

## Scheduling ⏰

```bash
# Schedule from CLI
flowyml schedule add --pipeline my_pipeline \
    --cron "0 6 * * *" \
    --name "Daily Training"

# List schedules
flowyml schedule list

# Remove schedule
flowyml schedule remove --name "Daily Training"
```

## Stack Switching ☁️

```bash
# Development (local)
export FLOWYML_STACK=local

# Production (cloud)
export FLOWYML_STACK=production

# Same code, different infrastructure
python my_pipeline.py
```

---

## 📍 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>
### ✨ Features Explorer
Full deep dive into all FlowyML capabilities.

[Features →](../FEATURES.md)
</div>

<div class="header-card" markdown>
### 🚀 Quick Reference
Concise reference with even more patterns.

[Quick Ref →](../QUICK_REFERENCE.md)
</div>

<div class="header-card" markdown>
### 📚 Examples
Full working code examples.

[Examples →](../examples.md)
</div>

</div>

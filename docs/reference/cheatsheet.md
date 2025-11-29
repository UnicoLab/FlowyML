# flowyml Cheatsheet 📝

A quick reference guide for common flowyml commands and patterns.

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
flowyml_ENV=production python my_pipeline.py
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

@step
def step_one():
    return "data"

@step(inputs=["data"])
def step_two(data):
    return f"processed {data}"

# Declarative style
@pipeline
def my_pipeline():
    d = step_one()
    return step_two(d)

run = my_pipeline()
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

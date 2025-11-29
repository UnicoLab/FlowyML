# Configuration: YAML vs. Class-Based ⚙️

flowyml offers flexible configuration options to suit different development styles and deployment needs. You can define your pipelines and settings using either Python classes (for maximum flexibility and IDE support) or YAML files (for separation of concerns and easy modification without code changes).

## 🐍 Class-Based Configuration (Python)

This is the default and most powerful way to configure flowyml. It leverages Python's type system and allows for dynamic configuration logic.

### Example

```python
from flowyml import context, Pipeline

# Define configuration using Python objects
ctx = context(
    learning_rate=0.001,
    batch_size=64,
    optimizer="adam",
    layers=[128, 64, 10]
)

pipeline = Pipeline("my_pipeline", context=ctx)
```

**Pros:**
- Full power of Python (loops, conditionals, imports).
- IDE autocompletion and type checking.
- Easy to debug.

## 📄 YAML-Based Configuration

YAML configuration is ideal for production deployments where you want to change parameters without modifying code, or for defining pipeline structures declaratively.

### Example `pipeline.yaml`

```yaml
name: training_pipeline
project: default
context:
  learning_rate: 0.001
  batch_size: 64
  optimizer: adam
  layers:
    - 128
    - 64
    - 10

steps:
  - name: load_data
    function: my_module.load_data
  - name: train
    function: my_module.train
    inputs: [load_data]
```

### Loading YAML Configuration

```python
from flowyml import Pipeline

# Load pipeline from YAML
pipeline = Pipeline.from_yaml("pipeline.yaml")

# Run it
pipeline.run()
```

**Pros:**
- Language-agnostic format.
- Easy to inject into CI/CD pipelines.
- Clear separation of code and configuration.

## 🔄 Hybrid Approach

You can also mix both approaches. For example, define the pipeline structure in Python but load specific parameters from a YAML file.

```python
import yaml
from flowyml import context, Pipeline

# Load params
with open("config.yaml") as f:
    config = yaml.safe_load(f)

# Inject into context
ctx = context(**config)

pipeline = Pipeline("hybrid_pipeline", context=ctx)
```

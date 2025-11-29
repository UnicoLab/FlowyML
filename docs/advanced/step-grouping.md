# Step Grouping

**Efficiently execute multiple steps in the same environment/container**

---

## Overview

Step grouping allows you to run multiple pipeline steps within the same Docker container or remote executor, significantly reducing overhead and improving efficiency. This is particularly useful when you have several logically related steps that would benefit from sharing an execution environment.

---

## Quick Start

```python
from flowyml import step, Pipeline
from flowyml.core.resources import ResourceRequirements, GPUConfig

# Define steps with the same execution_group
@step(outputs=["raw_data"], execution_group="preprocessing")
def load_data():
    return {"records": 1000}

@step(inputs=["raw_data"], outputs=["clean_data"], execution_group="preprocessing")
def clean_data(raw_data: dict):
    return {**raw_data, "status": "cleaned"}

@step(inputs=["clean_data"], outputs=["features"], execution_group="preprocessing")
def extract_features(clean_data: dict):
    return {**clean_data, "features": ["f1", "f2", "f3"]}

# Create and run pipeline
pipeline = Pipeline("data_pipeline")
pipeline.add_step(load_data)
pipeline.add_step(clean_data)
pipeline.add_step(extract_features)

# All three steps run in the same container
result = pipeline.run()
```

---

## How It Works

### 1. Define Groups

Add the `execution_group` parameter to steps you want to group together:

```python
@step(outputs=["data"], execution_group="my_group")
def step_1():
    return "data"

@step(inputs=["data"], outputs=["result"], execution_group="my_group")
def step_2(data: str):
    return f"{data}_processed"
```

### 2. Automatic Analysis

flowyml automatically:
- ✅ Analyzes the pipeline DAG
- ✅ Groups consecutive steps with the same `execution_group`
- ✅ Splits non-consecutive steps into subgroups
- ✅ Aggregates resource requirements

### 3. Efficient Execution

Grouped steps:
- Run sequentially in the same process/container
- Share the same environment and dependencies
- Pass outputs directly without serialization overhead
- Use aggregated resources (max CPU, memory, GPU)

---

## Resource Aggregation

When steps are grouped, their resource requirements are intelligently aggregated:

```python
@step(
    outputs=["data"],
    execution_group="training",
    resources=ResourceRequirements(cpu="2", memory="4Gi")
)
def prepare_data():
    return "data"

@step(
    inputs=["data"],
    outputs=["model"],
    execution_group="training",
    resources=ResourceRequirements(
        cpu="8",
        memory="16Gi",
        gpu=GPUConfig(gpu_type="nvidia-v100", count=2)
    )
)
def train_model(data: str):
    return "model"

# Group resources: cpu="8", memory="16Gi", gpu=V100 x2
```

**Aggregation Strategy:**
- **CPU**: Maximum across all steps
- **Memory**: Maximum across all steps
- **Storage**: Maximum across all steps
- **GPU**:
  - Count: Maximum
  - Type: Best GPU (A100 > V100 > T4)
  - Memory: Maximum
- **Node Affinity**: Union of constraints

---

## Sequential Analysis

### Consecutive Steps (Grouped)

```python
# A → B → C (all in same group) ✅ Grouped together
@step(outputs=["a"], execution_group="proc")
def step_a(): return 1

@step(inputs=["a"], outputs=["b"], execution_group="proc")
def step_b(a): return a + 1

@step(inputs=["b"], outputs=["c"], execution_group="proc")
def step_c(b): return b + 1
```

###  Non-Consecutive Steps (Split)

```python
# A (group1) → X (no group) → B (group1)
# Result: A and B run separately (not consecutive)

@step(outputs=["a"], execution_group="group1")
def step_a(): return 1

@step(outputs=["x"])  # Different group
def step_x(): return 100

@step(inputs=["x"], outputs=["b"], execution_group="group1")
def step_b(x): return x + 1
```

---

## Advanced Features

### Mixed Grouped and Ungrouped Steps

```python
# Some steps grouped, others standalone
@step(outputs=["config"])  # Standalone
def load_config():
    return {"batch_size": 32}

@step(inputs=["config"], outputs=["data"], execution_group="prep")
def fetch_data(config):
    return "data"

@step(inputs=["data"], outputs=["processed"], execution_group="prep")
def process_data(data):
    return "processed"

@step(inputs=["processed"], outputs=["deployed"])  # Standalone
def deploy(processed):
    return "deployed"
```

### Compatibility with All Features

Step grouping works seamlessly with:

- ✅ **Caching** (all strategies: `code_hash`, `input_hash`, `False`)
- ✅ **Retries** (per-step retry configuration)
- ✅ **Conditional execution** (condition functions)
- ✅ **Versioned pipelines** (`VersionedPipeline`)
- ✅ **Resource specifications** (dict or `ResourceRequirements`)
- ✅ **GPU scheduling**
- ✅ **Node affinity** and tolerations

---

## Best Practices

### ✅ DO: Group Related Steps

```python
# Good: Logically related preprocessing steps
@step(outputs=["raw"], execution_group="preprocessing")
def load(): ...

@step(inputs=["raw"], outputs=["clean"], execution_group="preprocessing")
def clean(): ...

@step(inputs=["clean"], outputs=["features"], execution_group="preprocessing")
def extract(): ...
```

### ❌ DON'T: Group Unrelated Steps

```python
# Bad: Unrelated steps that could run in parallel
@step(outputs=["data1"], execution_group="bad_group")
def load_dataset_a(): ...

@step(outputs=["data2"], execution_group="bad_group")  # Independent!
def load_dataset_b(): ...
```

### ✅ DO: Use for Cost Optimization

```python
# Good: Multiple lightweight steps share expensive GPU instance
@step(outputs=["data"], execution_group="gpu_tasks",
      resources=ResourceRequirements(gpu=GPUConfig("nvidia-a100", count=1)))
def prepare_on_gpu(): ...

@step(inputs=["data"], outputs=["result"], execution_group="gpu_tasks")
def inference_on_gpu(data): ...

# Both steps reuse the same A100 instance
```

---

## Inspecting Groups

After building a pipeline, you can inspect the created groups:

```python
pipeline = Pipeline("my_pipeline")
pipeline.add_step(step_a)
pipeline.add_step(step_b)
pipeline.add_step(step_c)
pipeline.build()

# Check groups
print(f"Number of groups: {len(pipeline.step_groups)}")

for group in pipeline.step_groups:
    print(f"\nGroup: {group.group_name}")
    print(f"  Steps: {[s.name for s in group.steps]}")
    print(f"  Execution order: {group.execution_order}")
    if group.aggregated_resources:
        print(f"  CPU: {group.aggregated_resources.cpu}")
        print(f"  Memory: {group.aggregated_resources.memory}")
        if group.aggregated_resources.gpu:
            print(f"  GPU: {group.aggregated_resources.gpu.count}x {group.aggregated_resources.gpu.gpu_type}")
```

---

## Examples

### Example 1: Data Pipeline

```python
@step(outputs=["raw"], execution_group="etl")
def extract():
    return fetch_from_source()

@step(inputs=["raw"], outputs=["transformed"], execution_group="etl")
def transform(raw):
    return apply_transformations(raw)

@step(inputs=["transformed"], outputs=["loaded"], execution_group="etl")
def load(transformed):
    save_to_warehouse(transformed)
    return "success"
```

### Example 2: ML Training Pipeline

```python
@step(
    outputs=["dataset"],
    execution_group="training",
    resources=ResourceRequirements(cpu="4", memory="8Gi")
)
def prepare_dataset():
    return load_and_preprocess()

@step(
    inputs=["dataset"],
    outputs=["model"],
    execution_group="training",
    resources=ResourceRequirements(
        cpu="8",
        memory="32Gi",
        gpu=GPUConfig("nvidia-a100", count=2)
    )
)
def train_model(dataset):
    return train(dataset, epochs=100)

@step(
    inputs=["model"],
    outputs=["metrics"],
    execution_group="training",
    resources=ResourceRequirements(cpu="2", memory="4Gi")
)
def evaluate_model(model):
    return evaluate(model)

# Entire training workflow runs in one A100 instance
# Resources: cpu="8", memory="32Gi", gpu=2x A100
```

---

## See Also

- [Resource Specification](../core/resources.md) - Define resource requirements
- [Pipeline Execution](../core/pipelines.md) - Understand pipeline execution
- [Caching](caching.md) - Optimize with caching strategies
- [Examples](/examples/step_grouping_example.py) - Full working examples

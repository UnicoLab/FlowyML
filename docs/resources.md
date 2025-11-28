# Step-Level Resource Specification

UniFlow provides comprehensive step-level resource specification that allows you to declare CPU, GPU, memory, and other compute requirements for individual pipeline steps. These specifications are automatically translated to orchestrator-specific formats (Kubernetes, Google Vertex AI, AWS SageMaker, etc.).

## Overview

Resource specification enables you to:
- **Define compute resources** per step (CPU, memory, storage)
- **Request GPUs** with specific types, counts, and memory
- **Control node placement** with affinity rules and tolerations
- **Optimize costs** by right-sizing resources for each step
- **Ensure compatibility** across different orchestrators

## Quick Start

### Simple CPU and Memory

```python
from uniflow.core import step
from uniflow.core.resources import ResourceRequirements

@step(resources=ResourceRequirements(cpu="2", memory="4Gi"))
def preprocess_data(data):
    # Runs with 2 CPU cores and 4GB memory
    return processed_data
```

### GPU Training

```python
from uniflow.core.resources import ResourceRequirements, GPUConfig

@step(
    resources=ResourceRequirements(
        cpu="4",
        memory="16Gi",
        gpu=GPUConfig(gpu_type="nvidia-tesla-v100", count=2, memory="16Gi")
    )
)
def train_model(dataset):
    # Runs with 4 CPUs, 16GB RAM, and 2 V100 GPUs
    return model
```

## Resource Specification API

### ResourceRequirements

The main class for specifying step resources:

```python
ResourceRequirements(
    cpu: Optional[str] = None,           # CPU cores
    memory: Optional[str] = None,        # RAM amount
    storage: Optional[str] = None,       # Ephemeral storage
    gpu: Optional[GPUConfig] = None,     # GPU configuration
    node_affinity: Optional[NodeAffinity] = None  # Node selection
)
```

**Parameters:**

- **`cpu`**: CPU cores required
  - Formats: `"2"` (2 cores), `"500m"` (0.5 cores), `"2.5"` (2.5 cores)
  - Kubernetes-style: `"500m"` = 500 millicores = 0.5 cores

- **`memory`**: RAM required
  - Formats: `"4Gi"`, `"8192Mi"`, `"4G"`, `"1073741824"` (bytes)
  - Binary units: Ki, Mi, Gi, Ti (1024-based)
  - Decimal units: K, M, G, T (1000-based)

- **`storage`**: Ephemeral storage required
  - Same format as memory: `"100Gi"`, `"500G"`, etc.

- **`gpu`**: GPU configuration (see GPUConfig below)

- **`node_affinity`**: Node placement rules (see NodeAffinity below)

### GPUConfig

Specify GPU requirements:

```python
GPUConfig(
    gpu_type: str,                       # GPU type/model
    count: int = 1,                      # Number of GPUs
    memory: Optional[str] = None         # GPU memory per device
)
```

**Common GPU Types:**
- NVIDIA: `"nvidia-tesla-v100"`, `"nvidia-tesla-t4"`, `"nvidia-a100"`, `"nvidia-h100"`
- Cloud-specific:
  - GCP: `"nvidia-tesla-v100"`, `"nvidia-tesla-p100"`, `"nvidia-tesla-a100"`
  - AWS: `"nvidia-tesla-v100"`, `"nvidia-a10g"`, `"nvidia-h100"`
  - Azure: `"nvidia-tesla-v100"`, `"nvidia-tesla-t4"`, `"nvidia-a100"`

**Example:**

```python
gpu=GPUConfig(
    gpu_type="nvidia-a100",
    count=8,
    memory="80Gi"
)
```

### NodeAffinity

Control which nodes your step runs on (primarily for Kubernetes):

```python
NodeAffinity(
    required: dict[str, str] = {},       # Hard constraints
    preferred: dict[str, str] = {},      # Soft constraints
    tolerations: list[dict] = []         # Tolerate node taints
)
```

**Example:**

```python
node_affinity=NodeAffinity(
    required={"gpu": "true", "zone": "us-central1-a"},
    preferred={"instance-type": "n1-standard-8"},
    tolerations=[
        {"key": "nvidia.com/gpu", "operator": "Exists"},
        {"key": "dedicated", "value": "gpu", "effect": "NoSchedule"}
    ]
)
```

## Complete Examples

### Example 1: Data Processing Pipeline

```python
from uniflow.core import step
from uniflow.core.resources import ResourceRequirements

@step(resources=ResourceRequirements(cpu="1", memory="2Gi"))
def load_data(path):
    # Small resource footprint for data loading
    return data

@step(resources=ResourceRequirements(cpu="8", memory="32Gi"))
def process_data(data):
    # High memory processing
    return processed

@step(resources=ResourceRequirements(cpu="2", memory="4Gi"))
def save_results(processed):
    # Moderate resource saving
    return status
```

### Example 2: GPU Training with Node Affinity

```python
from uniflow.core import step
from uniflow.core.resources import ResourceRequirements, GPUConfig, NodeAffinity

@step(
    resources=ResourceRequirements(
        cpu="16",
        memory="128Gi",
        storage="500Gi",
        gpu=GPUConfig(gpu_type="nvidia-a100", count=8, memory="80Gi"),
        node_affinity=NodeAffinity(
            required={
                "cloud.google.com/gke-nodepool": "gpu-pool",
                "nvidia.com/gpu.present": "true"
            },
            tolerations=[
                {"key": "nvidia.com/gpu", "operator": "Exists"},
                {"key": "dedicated", "value": "gpu-training", "effect": "NoSchedule"}
            ]
        )
    )
)
def distributed_training(dataset):
    # Large-scale distributed training on specific GPU nodes
    return model
```

### Example 3: Multi-Step ML Pipeline

```python
from uniflow.core import step
from uniflow.core.resources import ResourceRequirements, GPUConfig

# Preprocessing: Moderate resources
@step(resources=ResourceRequirements(cpu="4", memory="16Gi"))
def preprocess(raw_data):
    return features

# Training: GPU-intensive
@step(resources=ResourceRequirements(
    cpu="8", memory="64Gi",
    gpu=GPUConfig(gpu_type="nvidia-tesla-v100", count=4)
))
def train(features):
    return model

# Evaluation: CPU-only
@step(resources=ResourceRequirements(cpu="2", memory="8Gi"))
def evaluate(model, test_data):
    return metrics

# Deployment: Lightweight
@step(resources=ResourceRequirements(cpu="1", memory="2Gi"))
def deploy(model):
    return endpoint
```

## Backward Compatibility

Resource specifications are fully backward compatible with the dict format:

```python
# Old dict format (still works)
@step(resources={"cpu": "2", "memory": "4Gi"})
def old_style_step():
    pass

# New ResourceRequirements format (recommended)
@step(resources=ResourceRequirements(cpu="2", memory="4Gi"))
def new_style_step():
    pass
```

## Orchestrator Support

Resource specifications are automatically translated to orchestrator-specific formats:

### Local Orchestrator

- Resource monitoring with warnings if limits exceeded
- Optional hard limits via cgroups (if available)
- GPU detection and allocation

### Kubernetes Orchestrator

Translates to Kubernetes pod specifications:

```yaml
resources:
  requests:
    cpu: "2"
    memory: "4Gi"
    nvidia.com/gpu: "2"
  limits:
    cpu: "4"
    memory: "16Gi"
    nvidia.com/gpu: "2"
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: gpu
          operator: In
          values:
          - "true"
```

### Google Vertex AI Orchestrator

Translates to Vertex AI machine types and accelerators:

```python
# UniFlow resource spec
resources=ResourceRequirements(
    cpu="16", memory="64Gi",
    gpu=GPUConfig(gpu_type="nvidia-tesla-v100", count=4)
)

# Translates to Vertex AI:
# machine_type: "n1-standard-16"
# accelerator_type: "NVIDIA_TESLA_V100"
# accelerator_count: 4
```

### AWS SageMaker Orchestrator

Translates to SageMaker instance types:

```python
# UniFlow resource spec
resources=ResourceRequirements(
    cpu="8", memory="32Gi",
    gpu=GPUConfig(gpu_type="nvidia-tesla-v100", count=1)
)

# Translates to SageMaker:
# instance_type: "ml.p3.2xlarge"  # V100 GPU instance
```

## Best Practices

### 1. Right-Size Your Resources

```python
# ❌ Over-provisioning wastes money
@step(resources=ResourceRequirements(cpu="64", memory="512Gi"))
def simple_preprocessing(data):
    return data.lower()

# ✅ Match resources to workload
@step(resources=ResourceRequirements(cpu="2", memory="4Gi"))
def simple_preprocessing(data):
    return data.lower()
```

### 2. Use GPUs Only When Needed

```python
# ❌ Don't use GPU for CPU-bound tasks
@step(resources=ResourceRequirements(
    gpu=GPUConfig(gpu_type="nvidia-a100", count=1)
))
def json_parsing(file):
    return parse_json(file)

# ✅ Reserve GPUs for compute-intensive tasks
@step(resources=ResourceRequirements(cpu="2", memory="4Gi"))
def json_parsing(file):
    return parse_json(file)

@step(resources=ResourceRequirements(
    cpu="8", memory="32Gi",
    gpu=GPUConfig(gpu_type="nvidia-a100", count=4)
))
def train_neural_network(data):
    return model
```

### 3. Use Node Affinity for Specific Hardware

```python
# Target specific node pools with specialized hardware
@step(resources=ResourceRequirements(
    cpu="32", memory="256Gi",
    gpu=GPUConfig(gpu_type="nvidia-h100", count=8),
    node_affinity=NodeAffinity(
        required={"hardware": "latest-gen"},
        tolerations=[{"key": "expensive", "operator": "Exists"}]
    )
))
def cutting_edge_training(data):
    return model
```

### 4. Consider Storage for Large Datasets

```python
@step(resources=ResourceRequirements(
    cpu="16",
    memory="64Gi",
    storage="1Ti"  # Large ephemeral storage for intermediate files
))
def process_large_dataset(data_path):
    # Downloads and processes terabytes of data
    return processed
```

## Validation

Resource specifications are validated at step creation time:

```python
# ✅ Valid formats
ResourceRequirements(cpu="2")                    # Integer cores
ResourceRequirements(cpu="2.5")                  # Decimal cores
ResourceRequirements(cpu="500m")                 # Millicores
ResourceRequirements(memory="4Gi")               # Gibibytes
ResourceRequirements(memory="4G")                # Gigabytes
ResourceRequirements(memory="4096Mi")            # Mebibytes

# ❌ Invalid formats (will raise ValueError)
ResourceRequirements(cpu="invalid")              # Not a number
ResourceRequirements(memory="4Zb")               # Invalid unit
ResourceRequirements(gpu=GPUConfig(gpu_type="v100", count=0))  # Count must be >= 1
```

## Migration from ZenML

If you're migrating from ZenML, UniFlow resource specifications are similar:

```python
# ZenML
from zenml import step
from zenml.config import ResourceSettings

@step(settings={"resources": ResourceSettings(
    cpu_count=2, memory="4GB", gpu_count=1
)})
def zenml_step():
    pass

# UniFlow
from uniflow.core import step
from uniflow.core.resources import ResourceRequirements, GPUConfig

@step(resources=ResourceRequirements(
    cpu="2",
    memory="4Gi",  # Note: Gi not GB
    gpu=GPUConfig(gpu_type="nvidia-tesla-v100", count=1)
))
def uniflow_step():
    pass
```

## Troubleshooting

### Resources Not Applied

**Problem:** Resources specified but not enforced

**Solution:** Ensure your orchestrator supports resource specifications:
```python
# Check if resources are set
my_step = my_function_step
print(f"Resources: {my_step.resources}")
```

### GPU Not Available

**Problem:** GPU requested but not available in cluster

**Solution:** Use node affinity to target GPU nodes:
```python
@step(resources=ResourceRequirements(
    gpu=GPUConfig(gpu_type="nvidia-v100", count=1),
    node_affinity=NodeAffinity(
        required={"accelerator": "nvidia-gpu"}
    )
))
def gpu_step():
    import torch
    assert torch.cuda.is_available(), "GPU not found!"
```

### Out of Memory Errors

**Problem:** Step crashes with OOM

**Solution:** Increase memory allocation:
```python
# Before
@step(resources=ResourceRequirements(memory="4Gi"))
def memory_intensive():
    pass

# After
@step(resources=ResourceRequirements(memory="16Gi"))  # Increased 4x
def memory_intensive():
    pass
```

## Related Documentation

- [Orchestrators Guide](./orchestrators.md) - Configure different orchestrators
- [Pipeline Optimization](./optimization.md) - Optimize pipeline performance
- [Cost Management](./cost_management.md) - Control cloud spending
- [Kubernetes Integration](./kubernetes.md) - Deploy on Kubernetes

## API Reference

For complete API documentation, see:
- [`uniflow.core.resources.ResourceRequirements`](../api/resources.md#resourcerequirements)
- [`uniflow.core.resources.GPUConfig`](../api/resources.md#gpuconfig)
- [`uniflow.core.resources.NodeAffinity`](../api/resources.md#nodeaffinity)

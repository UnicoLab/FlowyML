# GCP Stack Configuration Examples

This directory contains example configurations for running flowyml pipelines on Google Cloud Platform.

## Quick Start

### 1. Basic GCP Stack Setup

```python
from flowyml.stacks.gcp import GCPStack
from flowyml.stacks.components import ResourceConfig, DockerConfig
from flowyml.stacks.registry import StackRegistry
from flowyml import Pipeline, step

# Create GCP stack
gcp_stack = GCPStack(
    name="production",
    project_id="my-gcp-project",
    region="us-central1",
    bucket_name="my-flowyml-artifacts",
    registry_uri="gcr.io/my-gcp-project",
    service_account="flowyml-sa@my-project.iam.gserviceaccount.com"
)

# Register the stack
registry = StackRegistry()
registry.register_stack(gcp_stack, set_active=True)

# Your pipeline will now run on GCP!
```

### 2. Resource Configuration

Define compute resources for your pipeline steps:

```python
from flowyml.stacks.components import ResourceConfig

# CPU-only workload
cpu_resources = ResourceConfig(
    cpu="4",
    memory="16Gi",
    machine_type="n1-highmem-4"
)

# GPU workload
gpu_resources = ResourceConfig(
    cpu="8",
    memory="32Gi",
    gpu="nvidia-tesla-t4",
    gpu_count=2,
    machine_type="n1-highmem-8"
)

# High-memory workload
memory_intensive = ResourceConfig(
    cpu="16",
    memory="128Gi",
    machine_type="n1-highmem-16"
)
```

### 3. Docker Configuration

Configure Docker images for containerized execution:

```python
from flowyml.stacks.components import DockerConfig

# Using pre-built image
docker_config = DockerConfig(
    image="gcr.io/my-project/ml-pipeline:v1.0",
    env_vars={
        "PYTHONUNBUFFERED": "1",
        "TF_CPP_MIN_LOG_LEVEL": "2"
    }
)

# Building from Dockerfile
docker_from_file = DockerConfig(
    dockerfile="./Dockerfile",
    build_context=".",
    build_args={
        "PYTHON_VERSION": "3.11"
    }
)

# Using requirements list
docker_with_deps = DockerConfig(
    base_image="python:3.11-slim",
    requirements=[
        "tensorflow>=2.12.0",
        "scikit-learn>=1.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    ],
    env_vars={
        "CUDA_VISIBLE_DEVICES": "0,1"
    }
)
```

### 4. Complete ML Training Example

```python
from flowyml import Pipeline, step, Dataset, Model, Metrics
from flowyml.stacks.gcp import GCPStack
from flowyml.stacks.components import ResourceConfig, DockerConfig
from flowyml.stacks.registry import StackRegistry
import tensorflow as tf

# Setup GCP stack
gcp_stack = GCPStack(
    name="ml-training",
    project_id="my-ml-project",
    region="us-central1",
    bucket_name="ml-training-artifacts",
    registry_uri="gcr.io/my-ml-project"
)

registry = StackRegistry()
registry.register_stack(gcp_stack)

# Define resource requirements
training_resources = ResourceConfig(
    cpu="8",
    memory="32Gi",
    gpu="nvidia-tesla-v100",
    gpu_count=4,
    machine_type="n1-highmem-8"
)

# Define Docker configuration
training_docker = DockerConfig(
    image="gcr.io/my-ml-project/tf-training:latest",
    requirements=[
        "tensorflow>=2.12.0",
        "tensorboard>=2.12.0",
    ],
    env_vars={
        "TF_FORCE_GPU_ALLOW_GROWTH": "true",
        "CUDA_VISIBLE_DEVICES": "0,1,2,3"
    }
)

# Define pipeline steps
@step
def load_data(data_path: str):
    """Load training data from GCS."""
    # Data loading logic
    data = ...
    return Dataset.create(
        data=data,
        name="training_data",
        source=data_path
    )

@step
def train_ml_model(dataset: Dataset):
    """Train model with TensorFlow."""
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(10, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    # Training logic
    history = model.fit(...)

    return Model.create(
        data=model,
        name="trained_model",
        framework="tensorflow",
        parent=dataset
    )

@step
def evaluate_model(model: Model, dataset: Dataset):
    """Evaluate model performance."""
    # Evaluation logic
    accuracy = ...

    return Metrics.create(
        accuracy=accuracy,
        name="evaluation_metrics",
        parent=model
    )

# Create and run pipeline
pipeline = Pipeline(
    "ml_training_pipeline",
    stack=gcp_stack  # Use GCP stack
)

pipeline.add_step(load_data)
pipeline.add_step(train_ml_model)
pipeline.add_step(evaluate_model)

# Run on GCP with specified resources
result = pipeline.run(
    context={"data_path": "gs://my-bucket/train_data.csv"},
    resources=training_resources,
    docker_config=training_docker
)
```

### 5. Multi-Environment Setup

Seamlessly switch between local development and cloud production:

```python
from flowyml.stacks import LocalStack
from flowyml.stacks.gcp import GCPStack
from flowyml.stacks.registry import StackRegistry

# Create registry
registry = StackRegistry()

# Local stack for development
local_stack = LocalStack(name="local")
registry.register_stack(local_stack)

# GCP stack for production
gcp_stack = GCPStack(
    name="production",
    project_id="my-project",
    region="us-central1",
    bucket_name="prod-artifacts"
)
registry.register_stack(gcp_stack)

# Development: use local stack
registry.set_active_stack("local")
pipeline = Pipeline("my_pipeline")
# ... runs locally

# Production: switch to GCP
registry.set_active_stack("production")
pipeline = Pipeline("my_pipeline")
# ... runs on GCP!
```

### 6. Custom Dockerfile Example

Create a `Dockerfile` for your pipeline:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install flowyml
RUN pip install flowyml

# Copy pipeline code
COPY . /app
WORKDIR /app

# Set entrypoint
ENTRYPOINT ["python", "-m", "flowyml.cli.run"]
```

## GCP Setup Checklist

Before running pipelines on GCP, ensure:

1. **GCP Project Setup**
   - [ ] GCP project created
   - [ ] Billing enabled
   - [ ] APIs enabled: Vertex AI, Cloud Storage, Container Registry

2. **Service Account**
   - [ ] Service account created
   - [ ] Roles assigned: Vertex AI User, Storage Admin
   - [ ] Key downloaded (for local development)

3. **Storage**
   - [ ] GCS bucket created for artifacts
   - [ ] Appropriate IAM permissions set

4. **Container Registry**
   - [ ] Container registry configured
   - [ ] Docker authenticated to GCR

5. **Networking** (optional)
   - [ ] VPC network configured
   - [ ] Firewall rules set

## Authentication

### Local Development

```bash
# Authenticate with gcloud
gcloud auth login
gcloud config set project MY_PROJECT_ID

# Configure Docker for GCR
gcloud auth configure-docker

# Set application default credentials
gcloud auth application-default login
```

### Production (Service Account)

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

## Advanced Configurations

### Custom Machine Types

```python
resources = ResourceConfig(
    cpu="96",
    memory="360Gi",
    machine_type="n1-highmem-96"  # Custom high-memory VM
)
```

### Multiple GPU Types

```python
# T4 for inference
inference_gpu = ResourceConfig(
    gpu="nvidia-tesla-t4",
    gpu_count=1,
    machine_type="n1-standard-4"
)

# V100 for training
training_gpu = ResourceConfig(
    gpu="nvidia-tesla-v100",
    gpu_count=8,
    machine_type="n1-highmem-16"
)

# A100 for large-scale training
large_scale_gpu = ResourceConfig(
    gpu="nvidia-tesla-a100",
    gpu_count=8,
    machine_type="a2-highgpu-8g"
)
```

## Cost Optimization Tips

1. **Use Preemptible VMs** for fault-tolerant workloads
2. **Right-size resources** - start small and scale up
3. **Use regional buckets** to reduce data transfer costs
4. **Clean up artifacts** regularly
5. **Monitor spending** with GCP billing alerts

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Check service account roles
   - Verify IAM permissions on bucket

2. **Image Not Found**
   - Ensure Docker image is pushed to GCR
   - Check registry URI format

3. **Resource Quota Exceeded**
   - Request quota increase in GCP Console
   - Use smaller machine types

4. **Job Fails Immediately**
   - Check container logs in Vertex AI
   - Verify environment variables

## Next Steps

- Read the [Stack Architecture Guide](../architecture.md)
- Explore [Advanced Orchestration](../advanced/orchestration.md)
- Check out [Monitoring and Logging](../monitoring.md)

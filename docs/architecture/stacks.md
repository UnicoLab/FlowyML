# 🏗️ Stack Architecture Guide

## Overview

flowyml's stack system provides a flexible, modular architecture for running pipelines across different infrastructure environments. Similar to ZenML, stacks are composable collections of components that define where and how your pipelines execute.

## Core Concepts

### Stack Components

A **Stack** is composed of several components:

```
┌─────────────────────────────────────┐
│           flowyml Stack             │
├─────────────────────────────────────┤
│ ▸ Orchestrator (optional)           │
│   - Vertex AI, Kubeflow, Airflow   │
│                                     │
│ ▸ Executor                          │
│   - Local, Remote, Kubernetes      │
│                                     │
│ ▸ Artifact Store                    │
│   - Local FS, GCS, S3, Azure       │
│                                     │
│ ▸ Metadata Store                    │
│   - SQLite, PostgreSQL, MySQL      │
│                                     │
│ ▸ Container Registry (optional)     │
│   - GCR, ECR, Docker Hub           │
└─────────────────────────────────────┘
```

### Component Types

#### 1. **Orchestrator**
Manages pipeline workflow execution and scheduling.

- **Vertex AI**: Google Cloud's managed ML platform
- **Kubeflow**: Kubernetes-native ML workflows
- **Airflow**: Workflow scheduling and monitoring
- **None**: Direct execution (development)

#### 2. **Executor**
Runs individual pipeline steps.

- **LocalExecutor**: Runs steps in current process
- **RemoteExecutor**: Submits to remote compute
- **KubernetesExecutor**: Runs in K8s pods
- **VertexAIExecutor**: Runs on Vertex AI

#### 3. **Artifact Store**
Stores pipeline artifacts and outputs.

- **LocalArtifactStore**: Local filesystem
- **GCSArtifactStore**: Google Cloud Storage
- **S3ArtifactStore**: Amazon S3
- **AzureBlobStore**: Azure Blob Storage

#### 4. **Metadata Store**
Tracks pipeline runs, metrics, and lineage.

- **SQLiteMetadataStore**: Local SQLite database
- **PostgreSQLMetadataStore**: PostgreSQL database
- **CloudSQLMetadataStore**: Google Cloud SQL

#### 5. **Container Registry**
Manages Docker images for containerized execution.

- **GCRContainerRegistry**: Google Container Registry
- **ECRContainerRegistry**: AWS Elastic Container Registry
- **DockerHubRegistry**: Docker Hub

## Stack Types

### Local Stack

For development and testing:

```python
from flowyml.stacks import LocalStack

stack = LocalStack(
    name="local",
    artifact_path=".flowyml/artifacts",
    metadata_path=".flowyml/metadata.db"
)
```

**Use Cases:**
- Local development
- Unit testing
- Prototyping
- Small datasets

### GCP Stack

For production on Google Cloud Platform:

```python
from flowyml.stacks.gcp import GCPStack

stack = GCPStack(
    name="production",
    project_id="my-gcp-project",
    region="us-central1",
    bucket_name="my-artifacts",
    registry_uri="gcr.io/my-project"
)
```

**Use Cases:**
- Production ML training
- Large-scale data processing
- Team collaboration
- CI/CD pipelines

### AWS Stack (Coming Soon)

```python
from flowyml.stacks.aws import AWSStack

stack = AWSStack(
    name="aws-prod",
    region="us-east-1",
    s3_bucket="my-artifacts",
    ecr_registry="123456789.dkr.ecr.us-east-1.amazonaws.com"
)
```

### Kubernetes Stack (Coming Soon)

```python
from flowyml.stacks.k8s import KubernetesStack

stack = KubernetesStack(
    name="k8s-cluster",
    namespace="flowyml",
    storage_class="standard"
)
```

## Resource Configuration

Define compute resources for your pipelines:

```python
from flowyml.stacks.components import ResourceConfig

# CPU-intensive workload
cpu_config = ResourceConfig(
    cpu="8",
    memory="32Gi",
    disk_size="100Gi"
)

# GPU workload
gpu_config = ResourceConfig(
    cpu="16",
    memory="64Gi",
    gpu="nvidia-tesla-v100",
    gpu_count=4,
    machine_type="n1-highmem-16"
)

# Memory-intensive workload
memory_config = ResourceConfig(
    cpu="32",
    memory="256Gi",
    machine_type="n1-megamem-96"
)
```

## Docker Configuration

Containerize your pipelines:

```python
from flowyml.stacks.components import DockerConfig

# Pre-built image
docker_config = DockerConfig(
    image="gcr.io/my-project/ml-pipeline:v1.0"
)

# Build from Dockerfile
docker_config = DockerConfig(
    dockerfile="./Dockerfile",
    build_context=".",
    build_args={"PYTHON_VERSION": "3.11"}
)

# Dynamic requirements
docker_config = DockerConfig(
    base_image="python:3.11-slim",
    requirements=[
        "tensorflow>=2.12.0",
        "pandas>=2.0.0"
    ],
    env_vars={
        "PYTHONUNBUFFERED": "1",
        "TF_CPP_MIN_LOG_LEVEL": "2"
    }
)
```

## Stack Registry

Manage multiple stacks and switch seamlessly:

```python
from flowyml.stacks.registry import StackRegistry

# Create registry
registry = StackRegistry()

# Register stacks
registry.register_stack(local_stack)
registry.register_stack(gcp_stack)
registry.register_stack(aws_stack)

# List available stacks
print(registry.list_stacks())
# ['local', 'gcp-prod', 'aws-prod']

# Switch stacks
registry.set_active_stack("local")      # Development
registry.set_active_stack("gcp-prod")   # Production

# Get active stack
active = registry.get_active_stack()
```

## Using Stacks with Pipelines

### Method 1: Direct Assignment

```python
from flowyml import Pipeline
from flowyml.stacks.gcp import GCPStack

stack = GCPStack(...)
pipeline = Pipeline("my_pipeline", stack=stack)
```

### Method 2: Global Registry

```python
from flowyml import Pipeline
from flowyml.stacks.registry import set_active_stack

# Set active stack globally
set_active_stack("production")

# All new pipelines use active stack
pipeline = Pipeline("my_pipeline")
```

### Method 3: Per-Run Override

```python
pipeline = Pipeline("my_pipeline")

# Run locally
pipeline.run(stack=local_stack)

# Run on GCP
pipeline.run(stack=gcp_stack)
```

## Best Practices

### 1. **Environment-Based Configuration**

```python
import os
from flowyml.stacks import LocalStack
from flowyml.stacks.gcp import GCPStack

env = os.getenv("ENVIRONMENT", "local")

if env == "production":
    stack = GCPStack(...)
elif env == "staging":
    stack = GCPStack(..., bucket_name="staging-artifacts")
else:
    stack = LocalStack()
```

### 2. **Configuration Files**

```yaml
# flowyml.yaml
stacks:
  local:
    type: local
    artifact_path: .flowyml/artifacts

  production:
    type: gcp
    project_id: ${GCP_PROJECT_ID}
    region: us-central1
    bucket_name: ${GCP_BUCKET}
```

### 3. **Validation**

```python
# Always validate before production
stack.validate()

# Check configuration
print(stack.to_dict())
```

### 4. **Cost Optimization**

```python
# Use preemptible instances for fault-tolerant workloads
ResourceConfig(
    machine_type="n1-standard-4",
    preemptible=True  # 80% cost savings
)

# Right-size resources
ResourceConfig(
    cpu="2",  # Start small
    memory="8Gi",
    autoscaling=True  # Scale as needed
)
```

## Advanced Patterns

### Multi-Cloud Setup

```python
# GCP for training
train_stack = GCPStack(name="gcp-train", ...)

# AWS for inference
inference_stack = AWSStack(name="aws-inference", ...)

# Different pipelines, different clouds
training_pipeline.run(stack=train_stack)
inference_pipeline.run(stack=inference_stack)
```

### Hybrid Execution

```python
# Some steps local, some on cloud
@step(stack=local_stack)
def preprocess():
    ...

@step(stack=gcp_stack, resources=gpu_config)
def train():
    ...

@step(stack=local_stack)
def evaluate():
    ...
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

2. **Permission Denied**
   - Check service account roles
   - Verify IAM permissions

3. **Resource Quota**
   - Request quota increase
   - Use smaller machine types

4. **Image Not Found**
   - Push image to registry
   - Check image URI format

## Next Steps

- [GCP Stack Guide](https://github.com/UnicoLab/FlowyML/tree/main/examples/gcp_stack/README.md)
- [Resource Optimization](https://github.com/UnicoLab/FlowyML/tree/main/docs/architecture/resource-optimization.md)
- [CI/CD Integration](https://github.com/UnicoLab/FlowyML/tree/main/docs/architecture/cicd.md)

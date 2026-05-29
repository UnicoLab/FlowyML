---
title: "Stack Configuration — FlowyML"
description: "Configure FlowyML stacks to decouple code from infrastructure. Switch between local, Docker, GCP, AWS, and Azure with one environment variable."
---

FlowyML provides **clean separation of concerns** between your ML code and infrastructure configuration. Your code uses abstract functions, and the configuration determines where things actually go.

<div class="hero-section" markdown>

## 🔄 Same Code, Any Infrastructure

Write once, deploy anywhere. Swap from local SQLite → GCS + Vertex AI → S3 + SageMaker with a single config change. No code rewrites.

</div>

---

## 🏗️ The Principle

```
┌─────────────────────────────────┐
│         Your ML Code            │
│  (uses abstract functions)      │
│                                 │
│  save_model(model, "classifier")│
│  log_metrics({"accuracy": 0.95})│
│  save_artifact(data, "data.pkl")│
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│       flowyml.yaml              │
│  (configuration determines      │
│   where data actually goes)     │
│                                 │
│  artifact_store: gcs/s3/azure   │
│  experiment_tracker: mlflow     │
│  orchestrator: vertex_ai/k8s    │
└─────────────────────────────────┘
```

**Switching from GCS to S3?** Just edit `flowyml.yaml`. No code changes needed.

---

## 🚀 Quick Start

### 1️⃣ Initialize Your Stack

```bash
# Create flowyml.yaml with your plugins
flowyml stack init --tracker mlflow --store gcs --orchestrator vertex_ai
```

This creates:

```yaml linenums="1"
# flowyml.yaml
plugins:
  experiment_tracker:
    type: mlflow
    tracking_uri: http://localhost:5000
    experiment_name: my_experiments

  artifact_store:
    type: gcs
    bucket: my-ml-artifacts
    prefix: experiments/
    project: my-gcp-project

  orchestrator:
    type: vertex_ai
    project: my-gcp-project
    location: us-central1
    staging_bucket: gs://my-staging-bucket
```

### 2️⃣ Install the Plugins

```bash
# Install all plugins in your stack
flowyml stack install

# Or install individually
flowyml plugin install mlflow
flowyml plugin install gcs
flowyml plugin install vertex_ai
```

### 3️⃣ Write Clean ML Code

```python linenums="1"
from flowyml.plugins import (
    start_run, end_run,
    log_params, log_metrics,
    save_artifact, save_model,
)

# Your code is infrastructure-agnostic
def train_model(data, hyperparams):
    start_run("training_v1")
    log_params(hyperparams)

    model = train(data, **hyperparams)

    log_metrics({
        "accuracy": evaluate(model),
        "loss": compute_loss(model),
    })

    # Saves to whatever is configured in flowyml.yaml
    save_model(model, "models/classifier")
    save_artifact(data.stats, "data/statistics.json")

    end_run()
    return model
```

### 4️⃣ Switch Stack Without Code Changes

**Going to production on AWS?** Just update `flowyml.yaml`:

```yaml linenums="1"
# flowyml.yaml - Production AWS
plugins:
  experiment_tracker:
    type: mlflow
    tracking_uri: https://mlflow.prod.company.com

  artifact_store:
    type: s3
    bucket: prod-ml-artifacts
    prefix: models/
    region: us-east-1

  orchestrator:
    type: kubernetes
    namespace: ml-production
```

**Same code, different infrastructure.** ✨

---

## 📋 Configuration Options

### 🔬 Experiment Trackers

```yaml linenums="1"
# MLflow
experiment_tracker:
  type: mlflow
  tracking_uri: http://localhost:5000
  experiment_name: my_experiments

# Weights & Biases
experiment_tracker:
  type: wandb
  project: my-project
  entity: my-team

# Neptune
experiment_tracker:
  type: neptune
  project: my-workspace/my-project
  api_token: ${NEPTUNE_API_TOKEN}  # Use env var
```

### 💾 Artifact Stores

```yaml linenums="1"
# Google Cloud Storage
artifact_store:
  type: gcs
  bucket: my-ml-artifacts
  prefix: experiments/
  project: my-gcp-project

# AWS S3
artifact_store:
  type: s3
  bucket: my-ml-artifacts
  prefix: experiments/
  region: us-east-1

# Azure Blob Storage
artifact_store:
  type: azure_blob
  account_name: mystorageaccount
  container: ml-artifacts
```

### ☁️ Orchestrators

```yaml linenums="1"
# Vertex AI
orchestrator:
  type: vertex_ai
  project: my-gcp-project
  location: us-central1
  staging_bucket: gs://my-staging-bucket

# Kubernetes
orchestrator:
  type: kubernetes
  namespace: ml-pipelines
  service_account: ml-runner

# Airflow
orchestrator:
  type: airflow
  dag_folder: /opt/airflow/dags
```

### 🐳 Container Registries

```yaml linenums="1"
# Google Artifact Registry
container_registry:
  type: gcr
  project: my-gcp-project
  location: us-central1
  repository: ml-images
  use_artifact_registry: true

# AWS ECR
container_registry:
  type: ecr
  repository: ml-images
  region: us-east-1

# Docker Hub
container_registry:
  type: docker
  username: myuser
  repository: myuser/ml-images
```

---

## 🐳 Docker & Containerization

When running pipelines **remotely** (Vertex AI, SageMaker, Kubernetes), each step runs inside a Docker container. Understanding when FlowyML builds images for you vs. when you must build and push manually is critical.

### 🤖 Auto-Build (Remote Orchestrators)

With cloud orchestrators like **Vertex AI** and **SageMaker**, FlowyML can **automatically build a Docker image** from your code and push it to the configured container registry:

```yaml linenums="1"
# flowyml.yaml — auto-build enabled
plugins:
  orchestrator:
    type: vertex_ai
    project: my-gcp-project
    location: us-central1
    staging_bucket: gs://my-staging-bucket

  container_registry:
    type: gcr
    project: my-gcp-project
    location: us-central1
    repository: ml-pipelines

  # FlowyML auto-generates a Dockerfile, builds it, and pushes to GCR
  docker:
    auto_build: true                 # Enable auto-build (default: true)
    base_image: python:3.11-slim     # Base Docker image
    requirements_file: requirements.txt  # or pyproject.toml
    include_files:                   # Additional files to copy
      - src/
      - configs/
```

!!! info "🔧 What happens under the hood"
    1. FlowyML generates a `Dockerfile` from your config
    2. Installs dependencies from `requirements.txt` or `pyproject.toml`
    3. Copies your source code into the image
    4. Builds the image locally via Docker
    5. Pushes to the configured container registry
    6. Submits the pipeline with the image URI

### 🔨 Manual Build + Push

If you need **full control** over the Docker image (custom system packages, GPU drivers, multi-stage builds), build and push it yourself:

```dockerfile linenums="1"
# Dockerfile
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Your code
COPY src/ /app/src/
COPY flowyml.yaml /app/flowyml.yaml

WORKDIR /app
```

Build and push:

```bash
# Build
docker build -t us-central1-docker.pkg.dev/my-project/ml-pipelines/training:v1 .

# Push
docker push us-central1-docker.pkg.dev/my-project/ml-pipelines/training:v1
```

Reference the pre-built image in your config:

```yaml linenums="1"
plugins:
  docker:
    auto_build: false
    image: us-central1-docker.pkg.dev/my-project/ml-pipelines/training:v1
```

### 🎮 GPU Images

For GPU workloads, start from an NVIDIA base image:

```dockerfile linenums="1"
# Dockerfile.gpu
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY src/ /app/src/
WORKDIR /app
```

```yaml linenums="1"
# flowyml.yaml — GPU config
plugins:
  docker:
    auto_build: false
    image: us-central1-docker.pkg.dev/my-project/ml-images/gpu-training:latest
```

!!! tip "💡 When to use auto-build vs. manual"
    | Scenario | Recommended |
    |----------|-------------|
    | Quick prototyping | ✅ Auto-build |
    | Standard Python dependencies only | ✅ Auto-build |
    | Custom system packages (ffmpeg, CUDA) | 🔨 Manual build |
    | Multi-stage builds for smaller images | 🔨 Manual build |
    | CI/CD pipeline with image caching | 🔨 Manual build |
    | GPU workloads with NVIDIA base | 🔨 Manual build |

---

## 📦 Dependency Management

FlowyML supports both `requirements.txt` and `pyproject.toml` (Poetry/PDM) for managing Python dependencies in containerized environments.

### 📄 Using `requirements.txt`

The simplest approach — works everywhere:

```txt
# requirements.txt
flowyml[all]>=1.9.0
scikit-learn>=1.3.0
pandas>=2.0.0
mlflow>=2.8.0
google-cloud-aiplatform>=1.38.0
```

```yaml linenums="1"
# flowyml.yaml
plugins:
  docker:
    requirements_file: requirements.txt
```

### 📦 Using Poetry (`pyproject.toml`)

For teams using Poetry:

```toml linenums="1"
# pyproject.toml
[tool.poetry]
name = "my-ml-project"
version = "0.1.0"
python = "^3.11"

[tool.poetry.dependencies]
flowyml = {version = "^1.9.0", extras = ["all"]}
scikit-learn = "^1.3.0"
pandas = "^2.0.0"
```

```yaml linenums="1"
# flowyml.yaml
plugins:
  docker:
    requirements_file: pyproject.toml  # FlowyML detects format automatically
    package_manager: poetry             # or "pip" (default)
```

!!! warning "⚠️ Poetry in Docker"
    When using Poetry, FlowyML generates a `poetry.lock` export step in the Dockerfile. For manual builds, add:
    ```dockerfile
    RUN pip install poetry && poetry export -f requirements.txt -o /tmp/reqs.txt
    RUN pip install -r /tmp/reqs.txt
    ```

---

## 💪 Step Resources & GPU Allocation

Configure CPU, memory, and GPU resources per step. This is essential for remote execution where steps run in separate containers.

### ⚙️ Configuring Resources on Steps

```python linenums="1"
from flowyml import step

# CPU + Memory
@step(
    resources={"cpu": "4", "memory": "16Gi"}
)
def preprocess_data():
    """Runs with 4 CPUs and 16GB RAM."""
    ...

# GPU Allocation
@step(
    resources={
        "cpu": "8",
        "memory": "32Gi",
        "accelerator_type": "NVIDIA_TESLA_T4",
        "accelerator_count": 1,
    }
)
def train_model():
    """Runs on a T4 GPU with 32GB RAM."""
    ...

# Multiple GPUs
@step(
    resources={
        "cpu": "16",
        "memory": "64Gi",
        "accelerator_type": "NVIDIA_TESLA_A100",
        "accelerator_count": 4,
    }
)
def train_large_model():
    """Runs on 4x A100 GPUs."""
    ...
```

### 📋 Available Resource Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cpu` | `str` | Number of CPU cores | `"4"`, `"0.5"` |
| `memory` | `str` | RAM allocation | `"16Gi"`, `"512Mi"` |
| `accelerator_type` | `str` | GPU type | `"NVIDIA_TESLA_T4"`, `"NVIDIA_TESLA_A100"` |
| `accelerator_count` | `int` | Number of GPUs | `1`, `4`, `8` |
| `disk` | `str` | Ephemeral disk | `"100Gi"` |
| `timeout` | `int` | Max execution time (seconds) | `3600` |

### 🏗️ Default Resources via YAML

Set defaults for all steps, then override per-step:

```yaml linenums="1"
# flowyml.yaml
pipeline_defaults:
  resources:
    cpu: "2"
    memory: "8Gi"
    timeout: 1800  # 30 minutes

# Per-step overrides always take precedence
```

!!! tip "💡 Resource right-sizing"
    Start with smaller resources and scale up. Use `@step(resources={"cpu": "1", "memory": "4Gi"})` for data preprocessing and reserve GPUs only for training steps. This reduces costs significantly.

---

## 🔑 Environment Variables

You can use environment variables anywhere in your config:

```yaml linenums="1"
plugins:
  experiment_tracker:
    type: mlflow
    tracking_uri: ${MLFLOW_TRACKING_URI}

  artifact_store:
    type: s3
    bucket: ${ML_BUCKET}
    access_key: ${AWS_ACCESS_KEY_ID}
    secret_key: ${AWS_SECRET_ACCESS_KEY}
```

---

## 🖥️ Stack Management Commands

```bash
# Create initial configuration
flowyml stack init --tracker mlflow --store gcs

# Show current stack
flowyml stack show

# Validate configuration
flowyml stack validate

# Install all plugins in stack
flowyml stack install

# List all stacks
flowyml stack list
```

---

## 🔀 Named Multi-Stack Support

FlowyML supports **named stacks** for managing development, staging, and production environments in a single config file:

```yaml linenums="1"
# flowyml.yaml
stacks:
  local:
    orchestrator: { type: local }
    artifact_store: { type: local, path: "./artifacts" }

  gcp-dev:
    orchestrator: { type: vertex_ai, project: ${GCP_PROJECT} }
    artifact_store: { type: gcs, bucket: dev-ml-artifacts }
    experiment_tracker: { type: mlflow }

  gcp-prod:
    orchestrator: { type: vertex_ai, project: ${GCP_PROJECT} }
    artifact_store: { type: gcs, bucket: prod-ml-artifacts }
    model_registry: { type: vertex_model_registry }
    model_deployer: { type: vertex_endpoint }
    artifact_routing:
      Model: { store: gcs, register: true, deploy: true }
      Metrics: { log_to_tracker: true }

  aws-staging:
    orchestrator: { type: sagemaker, region: us-east-1 }
    artifact_store: { type: s3, bucket: staging-ml }
    model_registry: { type: sagemaker_model_registry }

active_stack: local
```

### 🔄 Switching Stacks

```bash
# Via environment variable
FLOWYML_STACK=gcp-prod flowyml run my_pipeline

# Via CLI
flowyml stack set gcp-prod
flowyml stack list
flowyml stack show gcp-prod
```

```python linenums="1"
# Via context manager
from flowyml.plugins import use_stack

with use_stack("gcp-prod"):
    pipeline.run()

# Via decorator
from flowyml.plugins import use_stack_decorator

@use_stack_decorator("gcp-prod")
def production_training():
    pipeline.run()
```

---

## 🔀 Type-Based Artifact Routing

Route artifacts automatically based on their type annotations:

```python linenums="1"
from flowyml.core import step, Model, Dataset, Metrics

@step
def train() -> Model:
    """Returns Model - auto-routes to store + registry + endpoint"""
    return Model(clf, name="classifier", version="1.0.0")

@step
def evaluate() -> Metrics:
    """Returns Metrics - auto-logged to tracker"""
    return Metrics({"accuracy": 0.95})
```

Configure routing rules per type:

```yaml linenums="1"
artifact_routing:
  Model:
    store: gcs
    register: true
    deploy: true
    endpoint_name: prod-model
  Dataset:
    store: gcs
    path: "{run_id}/data/{step_name}"
  Metrics:
    log_to_tracker: true
  Parameters:
    log_to_tracker: true
```

→ **Deep Dive**: [Type Routing Guide](type_routing.md)

---

## 📚 API Reference

### Tracking Functions

| Function | Description |
|----------|-------------|
| `start_run(name)` | Start a new experiment run |
| `end_run()` | End the current run |
| `log_params(dict)` | Log parameters |
| `log_metrics(dict)` | Log metrics |
| `set_tag(key, value)` | Set a tag |

### Artifact Functions

| Function | Description |
|----------|-------------|
| `save_artifact(obj, path)` | Save any artifact |
| `load_artifact(path)` | Load an artifact |
| `artifact_exists(path)` | Check if exists |
| `list_artifacts(path)` | List artifacts |

### Model Functions

| Function | Description |
|----------|-------------|
| `save_model(model, path)` | Save model with tracking |
| `load_model(path)` | Load a model |

### Container Functions

| Function | Description |
|----------|-------------|
| `push_image(name, tag)` | Push Docker image |
| `get_image_uri(name, tag)` | Get image URI |

### Utility Functions

| Function | Description |
|----------|-------------|
| `show_stack()` | Show configured stack |
| `validate_stack()` | Validate all plugins installed |

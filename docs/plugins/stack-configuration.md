# FlowyML Stack Configuration

FlowyML provides **clean separation of concerns** between your ML code and infrastructure configuration. Your code uses abstract functions, and the configuration determines where things actually go.

## The Principle

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

## Quick Start

### 1. Initialize Your Stack

```bash
# Create flowyml.yaml with your plugins
flowyml stack init --tracker mlflow --store gcs --orchestrator vertex_ai
```

This creates:

```yaml
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

### 2. Install the Plugins

```bash
# Install all plugins in your stack
flowyml stack install

# Or install individually
flowyml plugin install mlflow
flowyml plugin install gcs
flowyml plugin install vertex_ai
```

### 3. Write Clean ML Code

```python
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

### 4. Switch Stack Without Code Changes

**Going to production on AWS?** Just update `flowyml.yaml`:

```yaml
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

## Configuration Options

### Experiment Trackers

```yaml
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

### Artifact Stores

```yaml
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

### Orchestrators

```yaml
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

### Container Registries

```yaml
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

## Environment Variables

You can use environment variables in your config:

```yaml
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

## Stack Management Commands

```bash
# Create initial configuration
flowyml stack init --tracker mlflow --store gcs

# Show current stack
flowyml stack show

# Validate configuration
flowyml stack validate

# Install all plugins in stack
flowyml stack install
```

## Named Multi-Stack Support

FlowyML supports **named stacks** for managing development, staging, and production environments in a single config:

```yaml
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

### Switching Stacks

```bash
# Via environment variable
FLOWYML_STACK=gcp-prod flowyml run my_pipeline

# Via CLI
flowyml stack set gcp-prod
flowyml stack list
flowyml stack show gcp-prod
```

```python
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

## Type-Based Artifact Routing

Route artifacts automatically based on their type annotations:

```python
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

```yaml
artifact_routing:
  Model:
    store: gcs                    # Save to GCS
    register: true                # Register to model registry
    deploy: true                  # Deploy to endpoint
    endpoint_name: prod-model     # Endpoint name
  Dataset:
    store: gcs
    path: "{run_id}/data/{step_name}"  # Path template
  Metrics:
    log_to_tracker: true          # Log to experiment tracker
  Parameters:
    log_to_tracker: true
```

See [Type Routing Guide](type_routing.md) for full documentation.

## API Reference

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

### Orchestration Functions

| Function | Description |
|----------|-------------|
| `run_pipeline(pipeline, id)` | Run a pipeline |

### Utility Functions

| Function | Description |
|----------|-------------|
| `show_stack()` | Show configured stack |
| `validate_stack()` | Validate all plugins installed |

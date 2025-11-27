# Configuration Guide

## Overview

UniFlow uses YAML configuration files for declarative infrastructure setup. This guide covers all configuration options and best practices.

## Configuration File

### Location

UniFlow searches for configuration in this order:
1. `uniflow.yaml` (current directory)
2. `uniflow.yml`
3. `.uniflow/config.yaml`
4. `.uniflow/config.yml`
5. Custom path via `--config` flag

### Basic Structure

```yaml
# Stack definitions
stacks:
  ...

# Resource presets
resources:
  ...

# Docker configuration
docker:
  ...

# Component loading
components:
  ...

# Default stack
default_stack: local
```

## Stack Configuration

### Local Stack

```yaml
stacks:
  local:
    type: local
    artifact_store:
      path: .uniflow/artifacts
    metadata_store:
      path: .uniflow/metadata.db
```

### GCP Stack

```yaml
stacks:
  production:
    type: gcp
    project_id: ${GCP_PROJECT_ID}
    region: us-central1

    artifact_store:
      type: gcs
      bucket: ${GCP_BUCKET}
      prefix: uniflow  # Optional prefix for all artifacts

    container_registry:
      type: gcr
      uri: gcr.io/${GCP_PROJECT_ID}

    orchestrator:
      type: vertex_ai
      service_account: ${GCP_SERVICE_ACCOUNT}
      network: projects/${GCP_PROJECT_ID}/global/networks/prod-vpc  # Optional
      encryption_key: ${GCP_ENCRYPTION_KEY}  # Optional
```

### Custom Stack with Plugins

```yaml
stacks:
  airflow_stack:
    type: local

    orchestrator:
      type: airflow
      dag_folder: ~/airflow/dags
      default_args:
        owner: uniflow
        retries: 2

    artifact_store:
      type: minio
      endpoint: localhost:9000
      bucket: ml-artifacts
      access_key: ${MINIO_ACCESS_KEY}
      secret_key: ${MINIO_SECRET_KEY}
      secure: false
```

## Resource Configuration

### CPU Workloads

```yaml
resources:
  # Light processing
  small:
    cpu: "1"
    memory: "4Gi"
    disk_size: "20Gi"

  # Standard processing
  medium:
    cpu: "4"
    memory: "16Gi"
    disk_size: "50Gi"

  # Heavy processing
  large:
    cpu: "16"
    memory: "64Gi"
    disk_size: "200Gi"
```

### GPU Workloads

```yaml
resources:
  # Single GPU
  gpu_small:
    cpu: "4"
    memory: "16Gi"
    gpu: "nvidia-tesla-t4"
    gpu_count: 1
    disk_size: "100Gi"

  # Multi-GPU training
  gpu_large:
    cpu: "16"
    memory: "96Gi"
    gpu: "nvidia-tesla-v100"
    gpu_count: 4
    disk_size: "500Gi"
    machine_type: "n1-highmem-16"

  # A100 for large-scale
  gpu_xlarge:
    cpu: "96"
    memory: "360Gi"
    gpu: "nvidia-tesla-a100"
    gpu_count: 8
    disk_size: "1000Gi"
    machine_type: "a2-highgpu-8g"
```

### Specialized Workloads

```yaml
resources:
  # Memory-intensive
  high_memory:
    cpu: "32"
    memory: "256Gi"
    disk_size: "100Gi"
    machine_type: "n1-megamem-96"

  # CPU-intensive
  high_cpu:
    cpu: "96"
    memory: "86Gi"
    disk_size: "100Gi"
    machine_type: "n1-highcpu-96"
```

## Docker Configuration

### Using Existing Dockerfile

```yaml
docker:
  dockerfile: ./Dockerfile
  build_context: .
  build_args:
    PYTHON_VERSION: "3.11"
    BASE_IMAGE: "slim"
  env_vars:
    PYTHONUNBUFFERED: "1"
    TF_CPP_MIN_LOG_LEVEL: "2"
```

### Using Poetry

```yaml
docker:
  use_poetry: true
  base_image: "python:3.11-slim"
  env_vars:
    PYTHONUNBUFFERED: "1"
```

UniFlow will automatically:
- Read `pyproject.toml`
- Extract dependencies
- Build Docker image with Poetry

### Using Requirements File

```yaml
docker:
  requirements_file: requirements.txt
  base_image: "python:3.11-slim"
  system_packages:  # Optional
    - git
    - build-essential
  env_vars:
    PYTHONUNBUFFERED: "1"
```

### Pre-built Image

```yaml
docker:
  image: "gcr.io/my-project/ml-pipeline:v1.0"
  env_vars:
    MODEL_PATH: "/models"
    DATA_PATH: "/data"
```

### Dynamic Configuration

```yaml
docker:
  base_image: "python:3.11-slim"
  requirements:
    - tensorflow>=2.12.0
    - pandas>=2.0.0
    - scikit-learn>=1.0.0
  env_vars:
    PYTHONUNBUFFERED: "1"
    CUDA_VISIBLE_DEVICES: "0,1"
```

## Component Loading

### From Modules

```yaml
components:
  - module: my_uniflow_components
  - module: company_ml_plugins.orchestrators
```

### From Files

```yaml
components:
  - file: /path/to/custom_orchestrator.py:AirflowOrchestrator
  - file: ./plugins/minio_store.py:MinIOStore
```

### From ZenML

```yaml
components:
  - zenml: zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator
    name: k8s

  - zenml: zenml.integrations.aws.artifact_stores.S3ArtifactStore
    name: s3
```

## Environment Variables

### Variable Expansion

Use `${VAR}` or `$VAR` syntax:

```yaml
stacks:
  production:
    project_id: ${GCP_PROJECT_ID}
    bucket: ${GCP_BUCKET}
    service_account: ${GCP_SA}
```

### .env File

Create `.env` file:

```bash
# GCP Configuration
GCP_PROJECT_ID=my-ml-project
GCP_BUCKET=ml-artifacts-prod
GCP_SA=ml-pipeline@my-project.iam.gserviceaccount.com

# MinIO Configuration
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Secrets
API_KEY=secret-key-123
DATABASE_URL=postgresql://user:pass@host:5432/db
```

Reference in config:

```yaml
stacks:
  prod:
    api_key: ${API_KEY}
    database: ${DATABASE_URL}
```

### Environment-Specific Configs

```yaml
# dev.yaml
stacks:
  dev:
    type: local

# staging.yaml
stacks:
  staging:
    type: gcp
    project_id: ${STAGING_PROJECT_ID}

# prod.yaml
stacks:
  prod:
    type: gcp
    project_id: ${PROD_PROJECT_ID}
```

Use with:

```bash
# Development
uniflow run pipeline.py --config dev.yaml

# Staging
uniflow run pipeline.py --config staging.yaml

# Production
uniflow run pipeline.py --config prod.yaml
```

## Complete Example

```yaml
# uniflow.yaml - Complete configuration example

# ============================================================================
# STACKS
# ============================================================================
stacks:
  # Local development stack
  local:
    type: local
    artifact_store:
      path: .uniflow/artifacts
    metadata_store:
      path: .uniflow/metadata.db

  # Staging GCP stack
  staging:
    type: gcp
    project_id: ${GCP_PROJECT_ID_STAGING}
    region: us-central1
    artifact_store:
      type: gcs
      bucket: ${GCP_BUCKET_STAGING}
    container_registry:
      type: gcr
      uri: gcr.io/${GCP_PROJECT_ID_STAGING}
    orchestrator:
      type: vertex_ai

  # Production GCP stack
  production:
    type: gcp
    project_id: ${GCP_PROJECT_ID_PROD}
    region: us-central1
    artifact_store:
      type: gcs
      bucket: ${GCP_BUCKET_PROD}
    container_registry:
      type: gcr
      uri: gcr.io/${GCP_PROJECT_ID_PROD}
    orchestrator:
      type: vertex_ai
      service_account: ${GCP_SERVICE_ACCOUNT}
      network: projects/${GCP_PROJECT_ID_PROD}/global/networks/prod-vpc

  # Custom Airflow stack
  airflow:
    type: local
    orchestrator:
      type: airflow
      dag_folder: ~/airflow/dags
    artifact_store:
      type: minio
      endpoint: ${MINIO_ENDPOINT}
      bucket: airflow-artifacts

# ============================================================================
# RESOURCES
# ============================================================================
resources:
  # Default for most steps
  default:
    cpu: "2"
    memory: "8Gi"
    disk_size: "50Gi"

  # Data preprocessing
  preprocessing:
    cpu: "8"
    memory: "32Gi"
    disk_size: "100Gi"

  # Model training
  training:
    cpu: "16"
    memory: "64Gi"
    gpu: "nvidia-tesla-v100"
    gpu_count: 2
    disk_size: "200Gi"

  # Large-scale training
  training_large:
    cpu: "96"
    memory: "360Gi"
    gpu: "nvidia-tesla-a100"
    gpu_count: 8
    disk_size: "1000Gi"
    machine_type: "a2-highgpu-8g"

  # Inference
  inference:
    cpu: "4"
    memory: "16Gi"
    disk_size: "50Gi"

# ============================================================================
# DOCKER
# ============================================================================
docker:
  # Use existing Dockerfile
  dockerfile: ./Dockerfile
  build_context: .

  # Or use Poetry (comment out dockerfile above)
  # use_poetry: true
  # base_image: python:3.11-slim

  # Build arguments
  build_args:
    PYTHON_VERSION: "3.11"

  # Environment variables
  env_vars:
    PYTHONUNBUFFERED: "1"
    TF_CPP_MIN_LOG_LEVEL: "2"
    CUDA_VISIBLE_DEVICES: "0,1,2,3"

# ============================================================================
# COMPONENTS
# ============================================================================
components:
  # Load custom components
  - module: company_ml.uniflow_plugins

  # Load ZenML components
  - zenml: zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator
    name: k8s

# ============================================================================
# DEFAULTS
# ============================================================================
default_stack: local
```

## Best Practices

### 1. Use Environment Variables for Secrets

```yaml
# ✅ Good
database_url: ${DATABASE_URL}
api_key: ${API_KEY}

# ❌ Bad
database_url: postgresql://user:password@host/db
api_key: sk-abc123
```

### 2. Organize by Environment

```
configs/
├── dev.yaml
├── staging.yaml
└── prod.yaml
```

### 3. Define Resource Presets

```yaml
resources:
  small: {...}
  medium: {...}
  large: {...}
  gpu_training: {...}
```

### 4. Document Custom Components

```yaml
stacks:
  custom:
    orchestrator:
      type: airflow
      # dag_folder: Path to Airflow DAGs
      # default_args: Default DAG arguments
```

### 5. Version Control

- ✅ **DO** commit `uniflow.yaml`
- ✅ **DO** commit `uniflow.yaml.example`
- ❌ **DON'T** commit `.env`
- ❌ **DON'T** commit secrets

### 6. Validate Configuration

```bash
# Dry run to validate
uniflow run pipeline.py --dry-run

# Show stack configuration
uniflow stack show production
```

## Troubleshooting

### Configuration Not Found

```bash
# Specify custom path
uniflow run pipeline.py --config /path/to/uniflow.yaml
```

### Environment Variables Not Expanding

```bash
# Check .env file is in current directory
ls -la .env

# Or export manually
export GCP_PROJECT_ID=my-project
```

### Invalid YAML Syntax

```bash
# Validate YAML
python -c "import yaml; yaml.safe_load(open('uniflow.yaml'))"
```

### Stack Validation Errors

```bash
# Test stack configuration
python -c "
from uniflow.utils.stack_config import load_config, create_stack_from_config
loader = load_config()
config = loader.get_stack_config('production')
stack = create_stack_from_config(config, 'production')
stack.validate()
"
```

## See Also

- [Stack Architecture](../architecture/stacks.md)
- [CLI Reference](../reference/cli.md)
- [Custom Components](./components.md)
- [Quick Reference](../QUICK_REFERENCE.md)

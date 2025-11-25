# Improved UX Guide - Configuration-Driven Infrastructure

## Overview

UniFlow now supports **complete separation** between pipeline logic and infrastructure configuration. Your pipeline code remains clean and infrastructure-agnostic.

## Key Improvements

### ✨ Configuration-Driven

All infrastructure is defined in `uniflow.yaml`:

```yaml
stacks:
  local:
    type: local
  
  production:
    type: gcp
    project_id: ${GCP_PROJECT_ID}
    bucket_name: ${GCP_BUCKET}

resources:
  gpu_training:
    cpu: "8"
    memory: "32Gi"
    gpu: "nvidia-tesla-v100"
```

### 🎯 CLI-Based Execution

Run the same pipeline on different stacks without code changes:

```bash
# Development
uniflow run pipeline.py

# Production
uniflow run pipeline.py --stack production

# With GPU resources
uniflow run pipeline.py --stack production --resources gpu_training
```

### 📦 Auto-Detection

UniFlow automatically detects:
- ✅ Existing `Dockerfile`
- ✅ `pyproject.toml` for Poetry
- ✅ `requirements.txt`
- ✅ Environment variables from `.env`

### 🔒 Clean Separation

**Before (Tightly Coupled):**
```python
from uniflow.stacks.gcp import GCPStack
from uniflow.stacks.components import ResourceConfig, DockerConfig

# Infrastructure hardcoded in pipeline!
stack = GCPStack(project_id="...", bucket_name="...")
resources = ResourceConfig(cpu="8", memory="32Gi")
docker = DockerConfig(image="...")

pipeline = Pipeline("my_pipeline", stack=stack)
result = pipeline.run(resources=resources, docker=docker)
```

**After (Decoupled):**
```python
# Pure pipeline logic - NO infrastructure!
pipeline = Pipeline("my_pipeline")
result = pipeline.run()

# Infrastructure configured externally via:
# - uniflow.yaml
# - CLI flags
# - Environment variables
```

## Quick Start

### 1. Initialize Configuration

```bash
uniflow init
```

Creates `uniflow.yaml` with sensible defaults.

### 2. Configure Stacks

Edit `uniflow.yaml`:

```yaml
stacks:
  local:
    type: local
  
  staging:
    type: gcp
    project_id: my-project-staging
    region: us-central1
  
  production:
    type: gcp
    project_id: my-project-prod
    region: us-central1
```

### 3. Write Clean Pipelines

```python
# pipeline.py
from uniflow import Pipeline, step

@step
def process_data(input_path: str):
    # Your logic here
    return {"result": "processed"}

pipeline = Pipeline("data_processing")
pipeline.add_step(process_data)
```

### 4. Run Anywhere

```bash
# Development
uniflow run pipeline.py --context input_path=local/data.csv

# Staging
uniflow run pipeline.py --stack staging --context input_path=gs://staging/data.csv

# Production
uniflow run pipeline.py --stack production --context input_path=gs://prod/data.csv
```

## Environment Variables

Use `.env` file for secrets:

```bash
# .env
GCP_PROJECT_ID=my-project
GCP_BUCKET=my-artifacts
GCP_SERVICE_ACCOUNT=my-sa@project.iam.gserviceaccount.com
```

Reference in `uniflow.yaml`:

```yaml
stacks:
  production:
    project_id: ${GCP_PROJECT_ID}
    bucket_name: ${GCP_BUCKET}
```

## Docker Integration

### Option 1: Existing Dockerfile

UniFlow automatically uses it:

```yaml
docker:
  dockerfile: ./Dockerfile
  build_context: .
```

### Option 2: Poetry

Uses `pyproject.toml`:

```yaml
docker:
  use_poetry: true
  base_image: python:3.11-slim
```

### Option 3: Requirements File

```yaml
docker:
  requirements_file: requirements.txt
  base_image: python:3.11-slim
```

## CLI Commands

### Stack Management

```bash
# List configured stacks
uniflow stack list

# Show stack details
uniflow stack show production

# Set default stack
uniflow stack set-default production
```

### Running Pipelines

```bash
# Basic run
uniflow run pipeline.py

# Specify stack
uniflow run pipeline.py --stack production

# Specify resources
uniflow run pipeline.py --resources gpu_training

# Pass context
uniflow run pipeline.py --context key1=value1 --context key2=value2

# Dry run (show configuration)
uniflow run pipeline.py --stack production --dry-run

# Custom config file
uniflow run pipeline.py --config custom.yaml
```

## Benefits

### 🎯 For Data Scientists
- Write pure pipeline logic
- No infrastructure code
- Same code, multiple environments
- Easy testing locally

### 🏗️ For MLOps Engineers
- Centralized infrastructure config
- Version control for infra
- Easy environment management
- Security via environment variables

### 👥 For Teams
- Consistent deployment
- Easy collaboration
- Clear separation of concerns
- Reduced merge conflicts

## Migration Guide

### Old Style (Coupled)

```python
from uniflow import Pipeline
from uniflow.stacks.gcp import GCPStack

stack = GCPStack(
    project_id="my-project",
    bucket_name="my-bucket"
)

pipeline = Pipeline("my_pipeline", stack=stack)
```

### New Style (Decoupled)

1. Create `uniflow.yaml`:
```yaml
stacks:
  production:
    type: gcp
    project_id: my-project
    bucket_name: my-bucket
```

2. Simplify pipeline:
```python
from uniflow import Pipeline

pipeline = Pipeline("my_pipeline")
# Stack loaded from uniflow.yaml
```

3. Run with CLI:
```bash
uniflow run pipeline.py --stack production
```

## Advanced Patterns

### Per-Step Resources

```yaml
resources:
  preprocessing:
    cpu: "2"
    memory: "8Gi"
  
  training:
    cpu: "16"
    memory: "64Gi"
    gpu: "nvidia-tesla-v100"
  
  inference:
    cpu: "4"
    memory: "16Gi"
```

### Multi-Region Deployment

```yaml
stacks:
  us-prod:
    type: gcp
    region: us-central1
    bucket_name: us-artifacts
  
  eu-prod:
    type: gcp
    region: europe-west1
    bucket_name: eu-artifacts
```

### Environment-Specific Configs

```yaml
# dev.yaml
stacks:
  dev:
    type: local

# prod.yaml  
stacks:
  prod:
    type: gcp
```

```bash
# Development
uniflow run pipeline.py --config dev.yaml

# Production
uniflow run pipeline.py --config prod.yaml
```

## Best Practices

1. ✅ **Never hardcode infrastructure in pipeline code**
2. ✅ **Use uniflow.yaml for all stack configuration**
3. ✅ **Use environment variables for secrets**
4. ✅ **Define resource presets for common workloads**
5. ✅ **Version control uniflow.yaml (without secrets)**
6. ✅ **Use .env for local development secrets**
7. ✅ **Document required environment variables**

## Next Steps

- See [examples/clean_pipeline.py](../examples/clean_pipeline.py) for a complete example
- Read [Stack Architecture](./stacks.md) for deep dive
- Check [GCP Stack Guide](../examples/gcp_stack/README.md) for cloud deployment

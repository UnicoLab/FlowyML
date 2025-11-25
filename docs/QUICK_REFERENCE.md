# 🚀 UniFlow Quick Reference

## CLI Commands

### Initialize Project
```bash
uniflow init                    # Create uniflow.yaml
```

### Stack Management
```bash
uniflow stack list             # List all stacks
uniflow stack show STACK_NAME  # Show stack details
uniflow stack set-default NAME # Set default stack
```

### Run Pipelines
```bash
# Basic run (uses default stack from uniflow.yaml)
uniflow run pipeline.py

# Specify stack
uniflow run pipeline.py --stack production
uniflow run pipeline.py -s production

# Specify resources
uniflow run pipeline.py --resources gpu_training
uniflow run pipeline.py -r gpu_training

# Pass context variables
uniflow run pipeline.py --context data_path=/path/to/data
uniflow run pipeline.py --context key1=val1 --context key2=val2
uniflow run pipeline.py -ctx data_path=/path -ctx model_id=123

# Custom config file
uniflow run pipeline.py --config custom.yaml
uniflow run pipeline.py -c custom.yaml

# Dry run (show what would be executed)
uniflow run pipeline.py --stack production --dry-run

# Combined
uniflow run pipeline.py --stack production --resources gpu_training --context data_path=gs://bucket/data.csv
```

## Configuration File (uniflow.yaml)

### Minimal Configuration
```yaml
stacks:
  local:
    type: local

default_stack: local
```

### Full Configuration
```yaml
# Stack definitions
stacks:
  local:
    type: local
    artifact_store:
      path: .uniflow/artifacts
    metadata_store:
      path: .uniflow/metadata.db
  
  production:
    type: gcp
    project_id: ${GCP_PROJECT_ID}
    region: us-central1
    artifact_store:
      type: gcs
      bucket: ${GCP_BUCKET}
    container_registry:
      type: gcr
      uri: gcr.io/${GCP_PROJECT_ID}
    orchestrator:
      type: vertex_ai

# Default stack
default_stack: local

# Resource presets
resources:
  default:
    cpu: "2"
    memory: "8Gi"
  
  gpu_training:
    cpu: "8"
    memory: "32Gi"
    gpu: "nvidia-tesla-v100"
    gpu_count: 2

# Docker configuration
docker:
  dockerfile: ./Dockerfile     # Auto-detect existing Dockerfile
  use_poetry: true            # Or use Poetry from pyproject.toml
  # requirements_file: requirements.txt  # Or use requirements.txt
  base_image: python:3.11-slim
  env_vars:
    PYTHONUNBUFFERED: "1"
```

## Environment Variables

Create `.env` file:
```bash
GCP_PROJECT_ID=my-project
GCP_BUCKET=my-artifacts
GCP_SERVICE_ACCOUNT=my-sa@project.iam.gserviceaccount.com
```

Reference in `uniflow.yaml`:
```yaml
stacks:
  production:
    project_id: ${GCP_PROJECT_ID}
```

## Pipeline Code (Clean & Simple)

```python
from uniflow import Pipeline, step

@step
def my_step(input_data: str):
    # Your logic
    return {"output": input_data.upper()}

# NO infrastructure code needed!
pipeline = Pipeline("my_pipeline")
pipeline.add_step(my_step)

if __name__ == "__main__":
    result = pipeline.run(context={"input_data": "hello"})
```

## Common Workflows

### Development → Production

```bash
# 1. Develop locally
uniflow run train.py

# 2. Test on staging
uniflow run train.py --stack staging

# 3. Deploy to production
uniflow run train.py --stack production --resources gpu_training
```

### Different Regions

```yaml
# uniflow.yaml
stacks:
  us-prod:
    type: gcp
    region: us-central1
  
  eu-prod:
    type: gcp
    region: europe-west1
```

```bash
# Deploy to US
uniflow run pipeline.py --stack us-prod

# Deploy to EU
uniflow run pipeline.py --stack eu-prod
```

### GPU vs CPU Workloads

```yaml
# uniflow.yaml
resources:
  cpu_only:
    cpu: "4"
    memory: "16Gi"
  
  gpu_large:
    cpu: "16"
    memory: "64Gi"
    gpu: "nvidia-tesla-v100"
    gpu_count: 4
```

```bash
# CPU workload
uniflow run preprocess.py --resources cpu_only

# GPU training
uniflow run train.py --resources gpu_large
```

## Docker Patterns

### Use Existing Dockerfile
```yaml
docker:
  dockerfile: ./Dockerfile
  build_context: .
```

### Use Poetry
```yaml
docker:
  use_poetry: true
```

### Use Requirements.txt
```yaml
docker:
  requirements_file: requirements.txt
```

### Dynamic Build
```yaml
docker:
  base_image: python:3.11-slim
  requirements:
    - tensorflow>=2.12.0
    - pandas>=2.0.0
  env_vars:
    PYTHONUNBUFFERED: "1"
```

## Installation

```bash
# Basic
pip install uniflow

# With GCP support
pip install uniflow[gcp]

# With ML frameworks
pip install uniflow[tensorflow]
pip install uniflow[pytorch]

# Everything
pip install uniflow[all]
```

## Troubleshooting

### "Stack not found"
```bash
# Check available stacks
uniflow stack list

# Verify config file
cat uniflow.yaml
```

### "Missing dependencies"
```bash
# Install required extras
pip install uniflow[gcp]
```

### "Permission denied" on GCP
```bash
# Authenticate
gcloud auth login
gcloud auth application-default login
```

## Quick Tips

1. ✅ Use `uniflow init` to start new projects
2. ✅ Store `uniflow.yaml` in version control
3. ✅ Use `.env` for secrets (don't commit!)
4. ✅ Define resource presets for common workloads
5. ✅ Use `--dry-run` to verify configuration
6. ✅ Keep pipeline code infrastructure-free
7. ✅ Use environment variables for dynamic values

## Examples

See `examples/clean_pipeline.py` for a complete example of infrastructure-agnostic pipelines.

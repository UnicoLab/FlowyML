# 🚀 UniFlow Quick Reference

> [!NOTE]
> **What this page is**: A cheat sheet for common UniFlow commands and patterns. Perfect for bookmarking.
>
> **When to use it**: You know what you want to do, you just need the syntax.

## 📝 Decision Guide: Which Command Do I Need?

| I want to...  | Use this command |
|---------------|------------------|
| Create a new project | `uniflow init` |
| Run a pipeline locally | `python pipeline.py` or `uniflow run pipeline.py` |
| Run with different config | `uniflow run pipeline.py --context key=value` |
| Deploy to production | `uniflow run pipeline.py --stack production` |
| Use GPUs | `uniflow run pipeline.py --resources gpu_training` |
| See what would run | `uniflow run pipeline.py --dry-run` |
| List available stacks | `uniflow stack list` |
| Start the web UI | `uniflow ui start` |

---

## CLI Commands

### Initialize Project

```bash
uniflow init                    # Create uniflow.yaml in current directory
```

**When to use**: Starting a new UniFlow project. Creates configuration scaffolding.

### Stack Management

```bash
uniflow stack list             # List all configured stacks
uniflow stack show STACK_NAME  # Show detailed stack configuration
uniflow stack set-default NAME # Set which stack runs by default
```

**When to use**: Managing multiple deployment targets (local, staging, production).

> [!TIP]
> **Pro tip**: Run `uniflow stack list` to verify your configuration before deploying to production.

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

# Combined example
uniflow run pipeline.py --stack production --resources gpu_training --context data_path=gs://bucket/data.csv
```

**Decision guide**:
- Use `--stack` when deploying to different environments (local/staging/prod)
- Use `--resources` when you need specific compute (CPU vs GPU)
- Use `--context` to override parameters without changing code
- Use `--dry-run` to verify configuration before expensive runs

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
from uniflow import Pipeline, step, context

@step(outputs=["result"])
def my_step(input_data: str):
    # Your logic
    return input_data.upper()

# NO infrastructure code needed!
ctx = context(input_data="hello")
pipeline = Pipeline("my_pipeline", context=ctx)
pipeline.add_step(my_step)

if __name__ == "__main__":
    result = pipeline.run()
    print(f"Result: {result.outputs['result']}")  # "HELLO"
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

---

## 🎯 Real-World Workflow Examples

### Scenario 1: Development → Production

**Goal**: Test locally, then deploy to production with GPUs.

```bash
# 1. Develop and test locally
uniflow run train.py

# 2. Verify on staging with production-like resources
uniflow run train.py --stack staging --resources gpu_small

# 3. Deploy to production with full resources
uniflow run train.py --stack production --resources gpu_large
```

**Why this pattern works**: Same code, different infrastructure. Zero rewrites.

### Scenario 2: Multi-Region Deployment

**Goal**: Deploy the same pipeline to different cloud regions.

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
# Deploy to US region
uniflow run pipeline.py --stack us-prod

# Deploy to EU region
uniflow run pipeline.py --stack eu-prod
```

**Why this pattern works**: Data residency compliance, latency optimization, disaster recovery.

### Scenario 3: Different Workload Types

**Goal**: Run preprocessing on CPU, training on GPU.

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
# Step 1: Preprocess data (CPU only)
uniflow run preprocess.py --resources cpu_only

# Step 2: Train model (GPU required)
uniflow run train.py --resources gpu_large
```

**Why this pattern works**: Optimize costs — only pay for GPUs when you actually need them.

---

## 📜 Configuration Patterns

### When to Use Each Docker Pattern

| Pattern | Use When | Example |
|---------|----------|----------|
| Existing Dockerfile | You have custom setup needs | `dockerfile: ./Dockerfile` |
| Poetry | You use Poetry for dependency management | `use_poetry: true` |
| requirements.txt | Simple dependencies, widely compatible | `requirements_file: requirements.txt` |
| Dynamic build | Quick prototypes, minimal config | `base_image: python:3.11-slim` |

### Docker: Use Existing Dockerfile

```yaml
docker:
  dockerfile: ./Dockerfile
  build_context: .
```

**Use when**: You have specialized dependencies, custom binary installs, or complex build steps.

### Docker: Use Poetry

```yaml
docker:
  use_poetry: true
```

**Use when**: Managing dependencies with Poetry and want deterministic builds.

### Docker: Use Requirements.txt

```yaml
docker:
  requirements_file: requirements.txt
```

**Use when**: Simple, traditional Python projects with pip.

### Docker: Dynamic Build

```yaml
docker:
  base_image: python:3.11-slim
  requirements:
    - tensorflow>=2.12.0
    - pandas>=2.0.0
  env_vars:
    PYTHONUNBUFFERED: "1"
```

**Use when**: Rapid prototyping or simple dependencies that don't need a Dockerfile.

---

## 🛠️ Troubleshooting Quick Fixes

### "Stack not found"

```bash
# Check what stacks you have
uniflow stack list

# Verify config file exists and is valid
cat uniflow.yaml

# Set a default stack if none is set
uniflow stack set-default local
```

### "Missing dependencies"

```bash
# Install required extras for GCP
pip install "uniflow[gcp]"

# Or install everything
pip install "uniflow[all]"
```

### "Permission denied" on GCP

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR-PROJECT-ID

# Verify authentication
gcloud auth list
```

### "Pipeline runs locally but fails on cloud"

**Common causes**:
1. Missing dependencies in Docker image
2. Incorrect file paths (use cloud URIs like `gs://` not local paths)
3. Authentication not configured

**Solution pattern**:
```bash
# Test with dry-run first
uniflow run pipeline.py --stack production --dry-run

# Check the generated Docker image
docker images | grep uniflow

# Test the Docker image locally
docker run -it <image-id> /bin/bash
```

---

## ✅ Pro Tips

1. **Use `uniflow init` to start new projects** — Creates proper structure
2. **Store `uniflow.yaml` in version control** — Reproducible deployments
3. **Use `.env` for secrets** — Never commit credentials!
4. **Define resource presets for common workloads** — Consistency across team
5. **Use `--dry-run` to verify configuration** — Catch errors before expensive runs
6. **Keep pipeline code infrastructure-free** — Business logic separate from deployment
7. **Use environment variables for dynamic values** — One config, many environments
8. **Pin dependencies in production** — Avoid surprise breakages
9. **Test stack configs locally first** — Use local stack with production patterns
10. **Name stacks by purpose, not just environment** — `us-prod-gpu` > `prod2`

---

## 📚 Learn More

- **Full CLI reference**: [CLI Documentation](user-guide/cli.md)
- **Stack configuration guide**: [Architecture: Stacks](architecture/stacks.md)
- **Production deployment**: [Deployment Guide](deployment.md)
- **Complete examples**: [Examples](examples.md)

---

> [!TIP]
> **Bookmark this page!** Use it as your go-to reference when you need quick command syntax.

# 🚀 FlowyML Quick Reference

> [!NOTE]
> **What this page is**: A cheat sheet for common FlowyML commands and patterns. Perfect for bookmarking.
>
> **When to use it**: You know what you want to do, you just need the syntax.

## 📝 Decision Guide: Which Command Do I Need?

| I want to...  | Use this command |
|---------------|------------------|
| Create a new project | `flowyml init` |
| Run a pipeline locally | `python pipeline.py` or `flowyml run pipeline.py` |
| Run with different config | `flowyml run pipeline.py --context key=value` |
| Deploy to production | `flowyml run pipeline.py --stack production` |
| Use GPUs | `flowyml run pipeline.py --resources gpu_training` |
| See what would run | `flowyml run pipeline.py --dry-run` |
| List available stacks | `flowyml stack list` |
| Start the web UI | `flowyml ui start` |

---

## CLI Commands

### Initialize Project

```bash
flowyml init                    # Create flowyml.yaml in current directory
```

**When to use**: Starting a new FlowyML project. Creates configuration scaffolding.

### Stack Management

```bash
flowyml stack list             # List all configured stacks
flowyml stack show STACK_NAME  # Show detailed stack configuration
flowyml stack set-default NAME # Set which stack runs by default
```

**When to use**: Managing multiple deployment targets (local, staging, production).

> [!TIP]
> **Pro tip**: Run `flowyml stack list` to verify your configuration before deploying to production.

### Run Pipelines

```bash
# Basic run (uses default stack from flowyml.yaml)
flowyml run pipeline.py

# Specify stack
flowyml run pipeline.py --stack production
flowyml run pipeline.py -s production

# Specify resources
flowyml run pipeline.py --resources gpu_training
flowyml run pipeline.py -r gpu_training

# Pass context variables
flowyml run pipeline.py --context data_path=/path/to/data
flowyml run pipeline.py --context key1=val1 --context key2=val2
flowyml run pipeline.py -ctx data_path=/path -ctx model_id=123

# Custom config file
flowyml run pipeline.py --config custom.yaml
flowyml run pipeline.py -c custom.yaml

# Dry run (show what would be executed)
flowyml run pipeline.py --stack production --dry-run

# Combined example
flowyml run pipeline.py --stack production --resources gpu_training --context data_path=gs://bucket/data.csv
```

**Decision guide**:
- Use `--stack` when deploying to different environments (local/staging/prod)
- Use `--resources` when you need specific compute (CPU vs GPU)
- Use `--context` to override parameters without changing code
- Use `--dry-run` to verify configuration before expensive runs

## Configuration File (flowyml.yaml)

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
      path: .flowyml/artifacts
    metadata_store:
      path: .flowyml/metadata.db

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

Reference in `flowyml.yaml`:
```yaml
stacks:
  production:
    project_id: ${GCP_PROJECT_ID}
```

## Pipeline Code (Clean & Simple)

```python
from flowyml import Pipeline, step, context

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
flowyml run train.py

# 2. Test on staging
flowyml run train.py --stack staging

# 3. Deploy to production
flowyml run train.py --stack production --resources gpu_training
```

### Different Regions

```yaml
# flowyml.yaml
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
flowyml run pipeline.py --stack us-prod

# Deploy to EU
flowyml run pipeline.py --stack eu-prod
```

### GPU vs CPU Workloads

```yaml
# flowyml.yaml
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
flowyml run preprocess.py --resources cpu_only

# GPU training
flowyml run train.py --resources gpu_large
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
pip install flowyml

# With GCP support
pip install flowyml[gcp]

# With ML frameworks
pip install flowyml[tensorflow]
pip install flowyml[pytorch]

# Everything
pip install flowyml[all]
```

## Troubleshooting

### "Stack not found"
```bash
# Check available stacks
flowyml stack list

# Verify config file
cat flowyml.yaml
```

### "Missing dependencies"
```bash
# Install required extras
pip install flowyml[gcp]
```

---

## 🎯 Real-World Workflow Examples

### Scenario 1: Development → Production

**Goal**: Test locally, then deploy to production with GPUs.

```bash
# 1. Develop and test locally
flowyml run train.py

# 2. Verify on staging with production-like resources
flowyml run train.py --stack staging --resources gpu_small

# 3. Deploy to production with full resources
flowyml run train.py --stack production --resources gpu_large
```

**Why this pattern works**: Same code, different infrastructure. Zero rewrites.

### Scenario 2: Multi-Region Deployment

**Goal**: Deploy the same pipeline to different cloud regions.

```yaml
# flowyml.yaml
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
flowyml run pipeline.py --stack us-prod

# Deploy to EU region
flowyml run pipeline.py --stack eu-prod
```

**Why this pattern works**: Data residency compliance, latency optimization, disaster recovery.

### Scenario 3: Different Workload Types

**Goal**: Run preprocessing on CPU, training on GPU.

```yaml
# flowyml.yaml
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
flowyml run preprocess.py --resources cpu_only

# Step 2: Train model (GPU required)
flowyml run train.py --resources gpu_large
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

## ☁️ Cloud Stack Presets

FlowyML ships with ready-to-use stacks for Google Cloud, AWS, and Azure. Install the matching optional dependency and instantiate the stack directly from Python.

### Google Cloud (Vertex AI pipelines + endpoints)

```bash
pip install "flowyml[gcp]"
```

```python
from flowyml import Pipeline, step
from flowyml.stacks.gcp import GCPStack

stack = GCPStack(
    name="vertex-prod",
    project_id="my-gcp-project",
    region="us-central1",
    bucket_name="flowyml-artifacts",
    registry_uri="gcr.io/my-gcp-project",
)

@step
def train():
    ...

pipeline = Pipeline("trainer", stack=stack)
pipeline.add_step(train)
pipeline.run()

# Deploy a model artifact later
stack.vertex_endpoints.deploy_model(
    model_display_name="fraud-detector",
    artifact_uri="gs://flowyml-artifacts/runs/run-123/model",
    serving_image="gcr.io/my-gcp-project/fraud:prod",
    endpoint_display_name="fraud-prod",
)
```

### AWS (SageMaker or Batch)

```bash
pip install "flowyml[aws]"
```

```python
from flowyml import Pipeline
from flowyml.stacks.aws import AWSStack

stack = AWSStack(
    name="aws-prod",
    region="us-east-1",
    bucket_name="flowyml-artifacts",
    account_id="123456789012",
    orchestrator_type="sagemaker",  # or "batch"
    role_arn="arn:aws:iam::123456789012:role/SageMakerExecutionRole",
)

pipeline = Pipeline("trainer-aws", stack=stack)
pipeline.run()
```

### Azure (Azure ML + Blob + ACR + Cloud Run alternative)

```bash
pip install "flowyml[azure]"
```

```python
from flowyml import Pipeline
from flowyml.stacks.azure import AzureMLStack

stack = AzureMLStack(
    name="azure-prod",
    subscription_id="00000000-0000-0000-0000-000000000000",
    resource_group="flowyml-rg",
    workspace_name="flowyml-ws",
    compute="cpu-cluster",
    account_url="https://flowymlstorage.blob.core.windows.net",
    container_name="artifacts",
    registry_name="flowymlacr",
)

pipeline = Pipeline("trainer-azure", stack=stack)
pipeline.run()
```

> [!TIP]
> Authenticate with each cloud provider (gcloud, aws configure, az login) before running remote stacks. The optional extras install the required SDKs (`google-cloud-aiplatform`, `boto3`, `azure-ai-ml`, etc.).

## 📈 Production Metrics API

Enable digital teams to push real-time model health data straight into flowyml.

### Log metrics

```bash
curl -X POST https://your-flowyml/api/metrics/log \
  -H "Authorization: Bearer <WRITE_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
        "project": "fraud-monitoring",
        "model_name": "fraud-detector-v3",
        "environment": "prod",
        "metrics": {"precision": 0.92, "recall": 0.87},
        "tags": {"region": "eu-west-1"}
      }'
```

### Query latest metrics

```bash
curl -H "Authorization: Bearer <READ_TOKEN>" \
  "https://your-flowyml/api/metrics?project=fraud-monitoring&model_name=fraud-detector-v3&limit=20"
```

Tokens scoped to a project can only write/read metrics for that project.

> [!TIP]
> The UI and CLI also surface the same data via `/api/projects/<project>/metrics?model_name=...`, which is perfect for dashboards scoped to a single project.

---

## 🛠️ Troubleshooting Quick Fixes

### "Stack not found"

```bash
# Check what stacks you have
flowyml stack list

# Verify config file exists and is valid
cat flowyml.yaml

# Set a default stack if none is set
flowyml stack set-default local
```

### "Missing dependencies"

```bash
# Install required extras for GCP
pip install "flowyml[gcp]"

# Or install everything
pip install "flowyml[all]"
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
flowyml run pipeline.py --stack production --dry-run

# Check the generated Docker image
docker images | grep flowyml

# Test the Docker image locally
docker run -it <image-id> /bin/bash
```

---

## ✅ Pro Tips

1. **Use `flowyml init` to start new projects** — Creates proper structure
2. **Store `flowyml.yaml` in version control** — Reproducible deployments
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

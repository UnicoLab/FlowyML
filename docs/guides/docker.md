---
title: Docker Image Management — FlowyML
description: "Auto-build, push, and manage Docker images for remote pipeline execution."
---

## 🐳 Docker Image Management

FlowyML automatically builds and pushes Docker images for remote execution,
supporting **7 dependency managers**, **GPU/CUDA**, **multi-stage builds**, and
**4 container registries**.

<span class="feature-badge">🐳 Docker</span>
<span class="feature-badge">📦 Build</span>
<span class="feature-badge">🚀 Push</span>
<span class="feature-badge">🔒 Policies</span>

---

## Overview

When you run a pipeline on a remote stack (GCP, AWS, Azure), FlowyML needs a
Docker image containing your code and dependencies.  FlowyML handles this
**automatically**:

1. **Detects** your dependency manager (pip, uv, poetry, conda, pipenv, setup.py)
2. **Generates** an optimised, multi-stage Dockerfile
3. **Builds** the image with BuildKit and content-hash tagging
4. **Pushes** to your container registry
5. **Submits** the job to the remote orchestrator

Data scientists never touch Docker.  Platform teams control base images and
policies via enterprise stacks.

---

## Quick Start

```bash
# Auto-build (detects deps, creates Dockerfile, builds image)
flowyml docker build

# Build with GPU and push to registry
flowyml docker build --gpu --push --registry myregistry.azurecr.io

# Preview the generated Dockerfile
flowyml docker generate

# Inspect what FlowyML detected
flowyml docker inspect
```

Or entirely zero-config — just run on a remote stack:

```bash
# FlowyML auto-builds, pushes, and submits
flowyml run train.py --stack production
```

---

## Dependency Manager Auto-Detection

FlowyML scans your project and detects the dependency manager in this priority
order:

| Priority | Manager | Detected By | Explicit Flag |
|----------|---------|-------------|---------------|
| 1 | **conda** | `environment.yml` or `conda.yaml` | `--deps conda` |
| 2 | **uv** | `uv.lock` | `--deps uv` |
| 3 | **poetry** | `poetry.lock` + `pyproject.toml` | `--deps poetry` |
| 4 | **pipenv** | `Pipfile` or `Pipfile.lock` | `--deps pipenv` |
| 5 | **setup.py** | `setup.py` or `setup.cfg` | — |
| 6 | **pip** | `requirements.txt` | `--deps pip` |
| 7 | **freeze** | Auto-freeze from current env | — |

Override with `--deps`:

```bash
flowyml docker build --deps poetry
flowyml docker build --deps uv
```

---

## DockerConfig Reference

The `DockerConfig` dataclass controls all aspects of image building.

### Python API

```python
from flowyml.stacks.components import DockerConfig

config = DockerConfig(
    base_image="python:3.11-slim",
    requirements=["torch", "transformers"],
    gpu_enabled=True,
    cuda_version="12.4",
    multi_stage=True,
    auto_build=True,
    auto_push=True,
    health_check="python -c 'import flowyml'",
    labels={"team": "ml-platform", "env": "prod"},
    registry_uri="myregistry.azurecr.io",
)
```

### Full Field Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `image` | `str \| None` | `None` | Pre-built image URI (skips build) |
| `base_image` | `str` | `python:3.11-slim` | Base Docker image |
| `dockerfile` | `str \| None` | `None` | Custom Dockerfile path |
| `build_context` | `str` | `.` | Docker build context directory |
| `requirements` | `list[str]` | `[]` | Inline pip packages |
| `requirements_file` | `str \| None` | `None` | Path to requirements file |
| `apt_packages` | `list[str]` | `[]` | System packages (apt-get) |
| `env_vars` | `dict` | `{}` | Environment variables |
| `entrypoint` | `str \| None` | `None` | Custom ENTRYPOINT |
| `command` | `str \| None` | `None` | Custom CMD |
| `gpu_enabled` | `bool` | `False` | Enable GPU/CUDA support |
| `cuda_version` | `str \| None` | `None` | CUDA version (e.g. `12.4`) |
| `multi_stage` | `bool` | `True` | Use multi-stage builds |
| `cache_pip` | `bool` | `True` | Enable BuildKit pip cache |
| `platform` | `str` | `linux/amd64` | Target platform |
| `tag_strategy` | `str` | `content-hash` | Tag strategy |
| `use_uv` | `bool` | `False` | Force uv installer |
| `use_poetry` | `bool` | `False` | Force Poetry |
| `use_conda` | `bool` | `False` | Force conda |
| `use_pipenv` | `bool` | `False` | Force Pipenv |
| `conda_file` | `str \| None` | `None` | Conda environment file |
| `setup_file` | `str \| None` | `None` | setup.py/setup.cfg path |
| `auto_build` | `bool` | `True` | Auto-build for remote execution |
| `auto_push` | `bool` | `True` | Auto-push after build |
| `registry_uri` | `str \| None` | `None` | Target container registry |
| `health_check` | `str \| None` | `None` | Docker HEALTHCHECK CMD |
| `labels` | `dict` | `{}` | OCI image labels |
| `exclude_patterns` | `list[str]` | `[]` | .dockerignore patterns |

---

## CLI Commands

### `flowyml docker build`

Build a Docker image from the current project.

```bash
flowyml docker build [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--tag, -t` | content-hash | Image tag |
| `--stack, -s` | — | Use Docker config from enterprise stack |
| `--push` | `false` | Push to registry after build |
| `--registry` | — | Target container registry URI |
| `--platform` | `linux/amd64` | Target platform |
| `--gpu / --no-gpu` | `false` | Enable GPU/CUDA support |
| `--cuda` | — | CUDA version |
| `--deps` | `auto` | Dependency manager |
| `--base-image` | — | Base Docker image |
| `--dry-run` | `false` | Generate Dockerfile only |
| `--no-cache` | `false` | Disable BuildKit cache |
| `--context` | `.` | Build context directory |

**Examples:**

```bash
# Zero-config build
flowyml docker build

# GPU build with push
flowyml docker build --gpu --push --registry myregistry.azurecr.io

# Build from enterprise stack config
flowyml docker build --stack aml_gpu_large --push

# Dry-run to preview Dockerfile
flowyml docker build --deps poetry --dry-run
```

### `flowyml docker push`

Push a Docker image to a container registry.

```bash
flowyml docker push IMAGE_TAG [--registry URI]
```

### `flowyml docker generate`

Generate a Dockerfile without building.

```bash
flowyml docker generate [--gpu] [--deps M] [-o FILE] [--stack S]
```

### `flowyml docker inspect`

Inspect auto-detected Docker configuration.

```bash
flowyml docker inspect [--context .] [--stack S]
```

### `flowyml docker login`

Login to a container registry.

```bash
flowyml docker login REGISTRY [-u USER] [--password-stdin]
```

---

## Enterprise Stack Docker Config

Define Docker settings in enterprise stack YAMLs:

```yaml
apiVersion: flowyml.io/v1
kind: Stack
metadata:
  name: aml-gpu-large
  version: 2.0.0
spec:
  backend: azureml
  runtime:
    pythonVersion: "3.11"
    baseImage: "nvidia/cuda:12.4.1-runtime-ubuntu22.04"
    dependencyManager: uv
    gpuEnabled: true
    cudaVersion: "12.4"
    autoBuild: true
    autoPush: true
    multiStage: true
    healthCheck: "python -c 'import torch'"
    labels:
      team: ml-platform
      environment: production
    aptPackages:
      - libgomp1
      - libgl1
```

The stack's `runtime` section is automatically converted to a `DockerConfig`
via `StackDefinition.to_docker_config()`.

---

## Project Docker Defaults (`flowyml.yaml`)

Set project-wide Docker defaults in `flowyml.yaml`:

```yaml
docker:
  baseImage: "python:3.11-slim"
  dependencyManager: auto
  gpu: false
  multiStage: true
  autoBuild: true
  autoPush: true
  registryUri: "myregistry.azurecr.io"
  healthCheck: "python -c 'import flowyml'"
  labels:
    team: "ml-platform"
  excludePatterns:
    - ".git"
    - "__pycache__"
    - ".venv"
```

---

## Container Registries

FlowyML supports 4 container registries:

### Docker Hub

```python
from flowyml.stacks.dockerhub import DockerHubContainerRegistry

registry = DockerHubContainerRegistry(
    username="myuser",
    token="dckr_pat_...",
)
```

### Azure Container Registry (ACR)

```python
from flowyml.stacks.azure import ACRContainerRegistry

registry = ACRContainerRegistry(
    registry_name="myregistry",
    resource_group="ml-rg",
    subscription_id="...",
)
```

### AWS Elastic Container Registry (ECR)

```python
from flowyml.stacks.aws import ECRContainerRegistry

registry = ECRContainerRegistry(
    region="us-east-1",
    account_id="123456789",
)
```

### Google Container Registry (GCR / Artifact Registry)

```python
from flowyml.stacks.gcp import GCRContainerRegistry

registry = GCRContainerRegistry(
    project_id="my-project",
    region="us-central1",
)
```

---

## GPU/CUDA Support

```bash
# Default CUDA 12.4
flowyml docker build --gpu

# Specific CUDA version
flowyml docker build --gpu --cuda 11.8
```

Or in `flowyml.yaml`:

```yaml
docker:
  gpu: true
  cudaVersion: "12.4"
```

When GPU is enabled, FlowyML uses `nvidia/cuda:XX.X-runtime-ubuntu22.04` as the
base image.

---

## Multi-Stage Builds

By default, FlowyML generates **multi-stage** Dockerfiles:

- **Builder stage**: Installs dependencies in a temporary image
- **Runtime stage**: Copies only the installed packages, resulting in smaller images

Additional hardening:

- **Non-root user** (`appuser:1000`) for security
- **HEALTHCHECK** directive for container orchestrators
- **OCI labels** for image metadata

Disable with `--no-multi-stage` or `multi_stage: false`.

---

## Image Tag Strategies

| Strategy | Example | Description |
|----------|---------|-------------|
| `content-hash` (default) | `flowyml:ab3f8c21` | SHA-256 of config, deterministic |
| `git-sha` | `flowyml:e4f2a1b` | Git commit SHA |
| `latest` | `flowyml:latest` | Always latest |
| `semver` | `flowyml:1.2.3` | Semantic version (planned) |

---

## Image Policies

Enforce standards across teams:

```python
from flowyml.core.image_policy import ImagePolicy, ImagePolicyValidator

policy = ImagePolicy(
    allowed_registries=["myregistry.azurecr.io"],
    denied_base_images=["python:latest"],
    require_labels=["team", "environment"],
)

validator = ImagePolicyValidator(policy=policy)
results = validator.validate_config(docker_config)
for r in results:
    print(f"{r.rule_name}: {r.status} — {r.message}")
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: ML Pipeline
on:
  push:
    branches: [main]

jobs:
  build-and-run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install FlowyML
        run: pip install flowyml[all]

      - name: Build and push Docker image
        run: |
          flowyml docker login ${{ secrets.REGISTRY_URI }} \
            -u ${{ secrets.REGISTRY_USER }} \
            --password-stdin <<< "${{ secrets.REGISTRY_PASSWORD }}"
          flowyml docker build \
            --push \
            --registry ${{ secrets.REGISTRY_URI }}

      - name: Run pipeline
        run: |
          flowyml run train.py --stack production
```

---

## Troubleshooting

### Docker not installed

```
✗ Docker CLI not found. Install Docker first.
```

Install Docker Desktop or Docker Engine.

### No registry configured

```
Remote execution requires a container registry.
Set 'registry_uri' on DockerConfig, or configure a
'container_registry' on the Stack.

  Tip: flowyml docker build --registry <uri> --push
```

### Build fails on Apple Silicon

GCP/AWS require `linux/amd64` images.  FlowyML sets this automatically, but
you can override:

```bash
flowyml docker build --platform linux/amd64
```

### Inspect your configuration

```bash
flowyml docker inspect
```

Shows detected dependency manager, base image, and all build options.

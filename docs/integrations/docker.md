---
title: Docker Integration — FlowyML
description: "Containerize FlowyML pipelines with optimized Docker images, multi-stage builds, and registry management."
---

<div class="hero-section" markdown>

## 🐳 Docker Integration

Containerize FlowyML pipelines with optimized Docker images, multi-stage builds, and registry management.

<span class="feature-badge">📦 Multi-Stage Builds</span>
<span class="feature-badge">🏷️ Registry Push</span>
<span class="feature-badge">⚡ Optimized Images</span>

</div>

# 🐳 Docker Integration

!!! info "What you'll learn"
    How to run pipelines in isolated Docker containers — eliminate "it works on my machine" bugs forever.

Containerize your pipelines for reproducible execution anywhere — from a laptop to a Kubernetes cluster.

---

## Why Docker?

| Feature | Benefit |
|---|---|
| **Isolation** | Each step runs in a clean environment |
| **Reproducibility** | Identical code and dependencies in dev, staging, prod |
| **Portability** | Move from local Docker to K8s or cloud without code changes |
| **Dependency Control** | No conflicts between different step requirements |

---

## 🐳 Running on Docker

FlowyML can automatically build and run your steps in Docker containers:

```python
from flowyml.integrations.docker import DockerOrchestrator

pipeline.run(
    orchestrator=DockerOrchestrator(
        image="python:3.11-slim",    # Base image
        install_deps=True,            # Auto-install requirements.txt
    )
)
```

### Configuration

| Parameter | Type | Default | Description |
|---|---|---|---|
| `image` | `str` | `python:3.11-slim` | Base Docker image |
| `install_deps` | `bool` | `True` | Auto-install `requirements.txt` |
| `dockerfile` | `str` | `None` | Path to custom Dockerfile |
| `build_context` | `str` | `"."` | Docker build context |
| `volumes` | `dict` | `{}` | Volume mounts (host:container) |
| `env_vars` | `dict` | `{}` | Environment variables |

---

## 🛠 Custom Dockerfiles

For complex dependencies, provide your own Dockerfile:

```python
orchestrator = DockerOrchestrator(
    dockerfile="./Dockerfile",
    build_context=".",
)
```

### Example Dockerfile

```dockerfile
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y gcc libgomp1 && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . /app
WORKDIR /app
```

---

## 🔗 Volume Mounts

Mount local directories into the container for data access:

```python
orchestrator = DockerOrchestrator(
    image="python:3.11-slim",
    volumes={
        "/data/training": "/app/data",       # Host → Container
        "/models/registry": "/app/models",
    },
)
```

---

## Best Practices

!!! tip "Pin image versions"
    Use `python:3.11.7-slim` instead of `python:3.11-slim` for reproducible builds.

!!! tip "Multi-stage builds"
    Use multi-stage Dockerfiles to keep images small — build dependencies in one stage, copy only artifacts to the final stage.

!!! warning "GPU support"
    For GPU steps, use NVIDIA base images (e.g., `nvidia/cuda:12.0-runtime`) and install `nvidia-docker2`.

---

## 🚀 Docker Build & Push CLI

FlowyML provides a full CLI for building and pushing Docker images, with
**auto-detection** of your dependency manager and **zero-config** defaults.

### Quick Start

```bash
# Auto-build: detects deps, generates Dockerfile, builds image
flowyml docker build

# Build with GPU and push to registry
flowyml docker build --gpu --push --registry myregistry.azurecr.io

# Preview the generated Dockerfile
flowyml docker generate

# Inspect what FlowyML auto-detected
flowyml docker inspect
```

### Dependency Manager Auto-Detection

FlowyML scans your project and selects the right installer automatically:

| Priority | Manager | Detected By |
|----------|---------|-------------|
| 1 | **conda** | `environment.yml` or `conda.yaml` |
| 2 | **uv** | `uv.lock` |
| 3 | **poetry** | `poetry.lock` + `pyproject.toml` |
| 4 | **pipenv** | `Pipfile` |
| 5 | **setup.py** | `setup.py` or `setup.cfg` |
| 6 | **pip** | `requirements.txt` |

Override with `--deps`:

```bash
flowyml docker build --deps poetry
flowyml docker build --deps uv
```

### Container Registries

FlowyML supports 4 container registries out of the box:

- **Docker Hub** — `DockerHubContainerRegistry`
- **Azure ACR** — `ACRContainerRegistry`
- **AWS ECR** — `ECRContainerRegistry`
- **Google GCR** — `GCRContainerRegistry`

```bash
# Login
flowyml docker login myregistry.azurecr.io -u admin

# Build and push
flowyml docker build --push --registry myregistry.azurecr.io
```

### GPU/CUDA Support

```bash
# Build with GPU support (CUDA 12.4 default)
flowyml docker build --gpu

# Specific CUDA version
flowyml docker build --gpu --cuda 11.8
```

### Image Policies

Enforce enterprise standards with `ImagePolicy`:

```python
from flowyml.core.image_policy import ImagePolicy, ImagePolicyValidator

policy = ImagePolicy(
    allowed_registries=["myregistry.azurecr.io"],
    denied_base_images=["python:latest"],
    require_labels=["team", "environment"],
)

validator = ImagePolicyValidator(policy=policy)
results = validator.validate_config(docker_config)
```

!!! tip "Full Docker Reference"
    See the [Docker Image Management Guide](../guides/docker.md) for the complete
    `DockerConfig` field reference, enterprise stack integration, CI/CD examples,
    and troubleshooting.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### ☸️ Kubernetes Integration
Orchestrate pipelines on Kubernetes with auto-scaling, GPU scheduling, and distributed execution.

[Explore →](kubernetes.md)

</div>

<div class="header-card" markdown>

### 🚀 Deployment
Learn about production deployment strategies and CI/CD integration.

[Learn more →](../deployment.md)

</div>

<div class="header-card" markdown>

### 🏭 Production Deployment
Scale your containerized pipelines to production-grade infrastructure.

[View Guide →](../production_deployment.md)

</div>

</div>

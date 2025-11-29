# Installation Guide 📦

> [!TIP]
> **Quick start**: If you're just exploring FlowyML, run `pip install "flowyml[all]"` and you're ready to go. Come back to this page when you need production-grade deployment.

## System Requirements

- **Python**: 3.8 or higher (3.10+ recommended for best performance)
- **Operating System**: Linux, macOS, Windows (WSL2 recommended for Windows)
- **Memory**: Minimum 4GB RAM (8GB+ for larger pipelines)
- **Disk Space**: 500MB for full installation

**Why these requirements**: FlowyML is designed to run anywhere Python runs. The minimum specs support local development; production workloads scale based on your pipeline needs.

## Installation Options

Choose the installation that matches your use case:

### Basic Installation — Local Development Only

Install FlowyML core package:

```bash
pip install flowyml
```

**What you get**: Core pipeline orchestration, local artifact storage, metadata tracking.

**Use this when**: You're prototyping locally and don't need cloud deployment or the web UI yet.

### Full Installation — Everything Included (Recommended)

```bash
pip install "flowyml[all]"
```

**What you get**: Web UI, cloud integrations, ML framework support, everything.

**Use this when**: You want to try all FlowyML features without reinstalling. This is the recommended approach for new users.

---

## Optional Dependencies — Pick What You Need

For minimal installations or specific production setups, install only what you need:

### ML Framework Support

```bash
# TensorFlow/Keras automatic tracking
pip install "flowyml[tensorflow]"

# PyTorch integration
pip install "flowyml[pytorch]"

# Scikit-learn utilities
pip install "flowyml[sklearn]"
```

**Use this when**: You're building Docker images and want to minimize size, or you only use specific frameworks.

### Cloud Platform Support

```bash
# Google Cloud Platform (Vertex AI, GCS, Container Registry)
pip install "flowyml[gcp]"

# AWS support (coming soon)
pip install "flowyml[aws]"

# Azure support (coming soon)
pip install "flowyml[azure]"
```

**Use this when**: You're deploying to cloud and want cloud-specific features like managed orchestration (Vertex AI), cloud storage (GCS/S3), and container registries.

### Web UI & API Server

```bash
pip install "flowyml[ui]"
```

**What you get**: The visualization dashboard, REST API,real-time monitoring.

**Use this when**: You need the visual interface for debugging or monitoring, or building tools that integrate with FlowyML's API.

### Development

Install development dependencies:

```bash
pip install flowyml[dev]
```

## Combining Extras

You can combine multiple extras:

```bash
# TensorFlow + GCP
pip install flowyml[tensorflow,gcp]

# All ML frameworks + GCP
pip install flowyml[tensorflow,pytorch,sklearn,gcp]

# Everything including UI
pip install flowyml[all]
```

## From Source

```bash
git clone https://github.com/UnicoLab/FlowyML.git
cd FlowyML
pip install -e ".[all]"
```

## Docker

```bash
# Basic image
docker pull flowyml/flowyml:latest

# With TensorFlow
docker pull flowyml/flowyml:latest-tf

# With PyTorch
docker pull flowyml/flowyml:latest-torch

# Full image
docker pull flowyml/flowyml:latest-full
```

## Verification

Verify installation:

```python
import flowyml
print(flowyml.__version__)

# Check available features
from flowyml import check_features
check_features()
```

## Requirements by Use Case

### Local Development
```bash
pip install flowyml
```

### ML Training (TensorFlow)
```bash
pip install flowyml[tensorflow]
```

### ML Training (PyTorch)
```bash
pip install flowyml[pytorch]
```

### Production on GCP
```bash
pip install flowyml[gcp,tensorflow]  # or pytorch
```

### Full Development Setup
```bash
pip install flowyml[all,dev]
```

## Installation Best Practices 💡

### Use Virtual Environments

**Always** use virtual environments to avoid dependency conflicts:

```bash
# Using venv (built-in)
python -m venv flowyml-env
source flowyml-env/bin/activate  # Windows: flowyml-env\Scripts\activate
pip install "flowyml[all]"

# Using conda
conda create -n flowyml python=3.10
conda activate flowyml
pip install "flowyml[all]"
```

**Why this matters**: Prevents conflicts with other Python projects and makes it easy to reproduce your environment.

### Pin Versions in Production

For production deployments, pin exact versions:

```bash
# Generate requirements file
pip freeze > requirements.txt

# Or use Poetry (recommended)
pip install flowyml[all]
poetry lock
```

**Why this matters**: Ensures reproducible deployments and prevents surprise breakages from dependency updates.

---

## Troubleshooting Common Issues

### "Module not found" errors for optional features

**Problem**: You see `ImportError` or `ModuleNotFoundError` when using specific features.

**Solution**: Install the corresponding extra:

```bash
# For TensorFlow features
pip install "flowyml[tensorflow]"

# For GCP features
pip install "flowyml[gcp]"

# Or just install everything
pip install "flowyml[all]"
```

### Dependency version conflicts

**Problem**: pip reports conflicts between FlowyML's dependencies and existing packages.

**Solution**: Create a fresh virtual environment:

```bash
# Deactivate current environment if active
deactivate

# Create new environment
python -m venv new-flowyml-env
source new-flowyml-env/bin/activate
pip install "flowyml[all]"
```

### Python version too old

**Problem**: Installation fails with Python version errors.

**Solution**: Upgrade Python to 3.8 or higher:

```bash
# Check current version
python --version

# Using conda (recommended)
conda create -n flowyml python=3.10
conda activate flowyml

# Or use pyenv
pyenv install 3.10.0
pyenv local 3.10.0
```

### GCP authentication issues

**Problem**: Can't access GCS or Vertex AI.

**Solution**: Authenticate with gcloud:

```bash
# Install gcloud CLI first: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR-PROJECT-ID
```

### Installation is slow

**Problem**: `pip install` takes a very long time.

**Solution**: Clear pip cache or use a faster mirror:

```bash
# Clear cache
pip cache purge

# Or upgrade pip/setuptools
pip install --upgrade pip setuptools wheel

# Then retry
pip install "flowyml[all]"
```

---

## Next Steps

Once installed:

1. **Verify installation**: Run `flowyml --version` to confirm
2. **Build your first pipeline**: Follow the [Getting Started](getting-started.md) guide
3. **Explore examples**: Check out the [Examples](examples.md) page for real-world patterns

**Need help?** Visit the [Resources](resources.md) page for community support and troubleshooting guides.

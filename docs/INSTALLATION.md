# Installation Guide

## Basic Installation

Install UniFlow core package:

```bash
pip install uniflow
```

## Optional Dependencies

UniFlow supports various optional dependencies based on your use case:

### Machine Learning Frameworks

Install support for specific ML frameworks:

```bash
# TensorFlow/Keras support
pip install uniflow[tensorflow]

# PyTorch support  
pip install uniflow[pytorch]

# Scikit-learn support
pip install uniflow[sklearn]
```

### Cloud Platforms

Install support for cloud platforms:

```bash
# Google Cloud Platform (Vertex AI, GCS, GCR)
pip install uniflow[gcp]

# AWS (coming soon)
pip install uniflow[aws]

# Azure (coming soon)
pip install uniflow[azure]
```

### UI and API

Install web UI and API server:

```bash
pip install uniflow[ui]
```

### All Features

Install everything:

```bash
pip install uniflow[all]
```

### Development

Install development dependencies:

```bash
pip install uniflow[dev]
```

## Combining Extras

You can combine multiple extras:

```bash
# TensorFlow + GCP
pip install uniflow[tensorflow,gcp]

# All ML frameworks + GCP
pip install uniflow[tensorflow,pytorch,sklearn,gcp]

# Everything including UI
pip install uniflow[all]
```

## From Source

```bash
git clone https://github.com/uniflow/uniflow.git
cd uniflow
pip install -e ".[all]"
```

## Docker

```bash
# Basic image
docker pull uniflow/uniflow:latest

# With TensorFlow
docker pull uniflow/uniflow:latest-tf

# With PyTorch
docker pull uniflow/uniflow:latest-torch

# Full image
docker pull uniflow/uniflow:latest-full
```

## Verification

Verify installation:

```python
import uniflow
print(uniflow.__version__)

# Check available features
from uniflow import check_features
check_features()
```

## Requirements by Use Case

### Local Development
```bash
pip install uniflow
```

### ML Training (TensorFlow)
```bash
pip install uniflow[tensorflow]
```

### ML Training (PyTorch)
```bash
pip install uniflow[pytorch]
```

### Production on GCP
```bash
pip install uniflow[gcp,tensorflow]  # or pytorch
```

### Full Development Setup
```bash
pip install uniflow[all,dev]
```

## Troubleshooting

### Import Errors

If you get import errors for optional components:

```python
# TensorFlow
pip install uniflow[tensorflow]

# GCP
pip install uniflow[gcp]
```

### Version Conflicts

Create a fresh virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install uniflow[your-extras]
```

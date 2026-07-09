---
title: "Plugin System — FlowyML"
description: "FlowyML's plugin architecture: artifact stores, metadata stores, orchestrators, and experiment trackers. Build custom plugins or use built-in ones for GCP, AWS, Azure."
---

FlowyML features a **powerful native plugin system** that allows you to integrate with ANY ML tool — MLflow, Kubernetes, AWS S3, and more — **without external framework dependencies**.

<div class="hero-section" markdown>

## 🧩 One Framework, Any Infrastructure

Install only what you need. Write infrastructure-agnostic code. Deploy anywhere — from your laptop to Vertex AI.

</div>

---

## 🚀 Quick Start

### Via CLI

```bash
# Initialize your stack
flowyml stack init --tracker mlflow --store gcs --orchestrator vertex_ai

# Install configured plugins
flowyml stack install

# Verify everything is ready
flowyml stack validate
```

### Via Python

```python linenums="1"
# Your code stays infrastructure-agnostic
from flowyml.plugins import start_run, log_metrics, save_model

start_run("training")
log_metrics({"accuracy": 0.95})
save_model(model, "classifier")  # Goes wherever config says
```

### Via YAML (`flowyml.yaml`)

```yaml linenums="1"
plugins:
  experiment_tracker:
    type: mlflow
    tracking_uri: http://localhost:5000
  artifact_store:
    type: gcs
    bucket: my-ml-artifacts
  orchestrator:
    type: vertex_ai
    project: my-gcp-project
    region: us-central1
```

---

## ⚖️ Which Plugin Do I Need?

| I want to... | Plugin Type | Recommended Plugin |
|---|---|---|
| Track experiments & metrics | Experiment Tracker | `mlflow` or `wandb` |
| Store artifacts in the cloud | Artifact Store | `gcs` (GCP) or `s3` (AWS) |
| Run pipelines on cloud | Orchestrator | `vertex_ai` (GCP) or `sagemaker` (AWS) |
| Push Docker images | Container Registry | `gcr` (GCP) or `ecr` (AWS) |
| Register models | Model Registry | `mlflow_registry`, `azureml_registry`, `vertex_model_registry`, `sagemaker_model_registry` |
| Deploy / serve models | Model Deployer | `openshift`, `kubernetes`, `local_docker`, `vertex_endpoint`, `sagemaker_endpoint`, `gcp_cloud_run` |

---

## 🎯 Key Benefits

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 📦 No Framework Overhead
Install only what you need. Each plugin brings only its direct dependencies (e.g., `mlflow`, `boto3`).
</div>

<div class="header-card" markdown>
### 🔧 Three Ways to Configure
Use CLI commands, Python code, or YAML config files — whatever fits your workflow.
</div>

<div class="header-card" markdown>
### 🔌 Auto-Discovery
Publish plugins as PyPI packages with entry points — FlowyML discovers and registers them automatically.
</div>

</div>

---

## 📦 Available Plugins

### 🔬 Experiment Trackers

| Plugin | Description | Packages |
|--------|-------------|----------|
| `mlflow` | MLflow tracking & model registry | `mlflow` |
| `wandb` | Weights & Biases tracking | `wandb` |
| `neptune` | Neptune.ai tracking | `neptune` |
| `tensorboard` | TensorBoard visualization | `tensorboard` |

### 💾 Artifact Stores

| Plugin | Description | Packages |
|--------|-------------|----------|
| `gcs` | Google Cloud Storage ✅ | `google-cloud-storage`, `gcsfs` |
| `s3` | AWS S3 ✅ | `boto3`, `s3fs` |
| `azure_blob` | Azure Blob Storage | `azure-storage-blob`, `adlfs` |

### 🐳 Container Registries

| Plugin | Description | Packages |
|--------|-------------|----------|
| `gcr` | Google Artifact Registry ✅ | `google-cloud-artifact-registry` |
| `ecr` | AWS ECR ✅ | `boto3` |
| `acr` | Azure Container Registry | `azure-containerregistry` |

### ☁️ Orchestrators

| Plugin | Description | Packages |
|--------|-------------|----------|
| `vertex_ai` | Google Vertex AI Pipelines ✅ | `google-cloud-aiplatform` |
| `sagemaker` | AWS SageMaker Pipelines ✅ | `sagemaker` |
| `kubernetes` | Kubernetes | `kubernetes` |
| `airflow` | Apache Airflow | `apache-airflow` |

### 🏷️ Model Registries

| Plugin | Description |
|--------|-------------|
| `mlflow_registry` | MLflow Model Registry ✅ |
| `azureml_registry` | Azure ML Model Registry ✅ |
| `vertex_model_registry` | Vertex AI Model Registry ✅ |
| `sagemaker_model_registry` | SageMaker Model Registry ✅ |

### 🚢 Model Deployers

| Plugin | Description |
|--------|-------------|
| `local_docker` | Serve via `docker run` on the local machine ✅ |
| `kubernetes` | `Deployment` + `Service` + `Ingress` ✅ |
| `openshift` | `Deployment` + `Service` + `Route` ✅ |
| `vertex_endpoint` | Vertex AI Endpoints ✅ |
| `sagemaker_endpoint` | SageMaker Endpoints ✅ |
| `gcp_cloud_run` | Google Cloud Run ✅ |

!!! tip "Serving the models you register"
    Model registries and deployers power the transparent
    `train → register → promote → deploy → serve` path. See the
    **[Model Serving & Deployment guide](../guides/model-serving-deployment.md)**.

---

## 🏗️ Architecture

The plugin system is built on three core components:

### 1️⃣ Plugin Registry

The central hub that manages all available plugins:

```python linenums="1"
from flowyml.plugins import list_plugins, get_plugin

# List all available plugins
plugins = list_plugins()

# Get a specific plugin instance
tracker = get_plugin("mlflow", tracking_uri="http://localhost:5000")
```

### 2️⃣ Base Plugin Classes

Consistent interfaces for each plugin type:

```python linenums="1"
from flowyml.plugins.base import (
    ExperimentTracker,
    ArtifactStorePlugin,
    OrchestratorPlugin,
    ContainerRegistryPlugin,
)
```

### 3️⃣ Stack Configuration

YAML-based infrastructure definitions with environment variable support:

```yaml linenums="1"
plugins:
  artifact_store:
    type: s3
    bucket: ${AWS_BUCKET}
    region: ${AWS_REGION}
```

---

## 🎯 Entry Point Discovery

Plugins can register themselves automatically via Python entry points:

```toml linenums="1"
# In your plugin's pyproject.toml
[project.entry-points."flowyml.plugins"]
my_tracker = "my_package.plugins:MyCustomTracker"
```

FlowyML will auto-discover and register your component!

### 📦 Unified Plugin Management

```bash
# List available plugins
flowyml plugin list

# Install a plugin
flowyml plugin install mlflow

# Show plugin info
flowyml plugin info mlflow

# Search for plugins
flowyml plugin search kubernetes
```

---

## 📚 Deep Dive Guides

<div class="header-grid" markdown>

<div class="header-card" markdown>
### ⚙️ Stack Configuration
Configure infrastructure in YAML. Multi-stack for dev/staging/prod.

→ **[Stack Configuration Guide](stack-configuration.md)**
</div>

<div class="header-card" markdown>
### 📦 Native Plugins
Complete guide to every built-in plugin with setup instructions.

→ **[Native Plugins Guide](native-plugins.md)**
</div>

<div class="header-card" markdown>
### 🔧 Custom Plugins
Build your own plugins with the extensible base classes.

→ **[Creating Plugins Guide](creating-plugins.md)**
</div>

</div>

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🎯 Practical Examples
Copy-paste recipes for K8s, GCP, AWS, and hybrid stacks.

→ **[Practical Examples](practical-examples.md)**
</div>

<div class="header-card" markdown>
### 🔀 Type-Based Routing
Auto-route Models, Datasets, and Metrics to the right stores.

→ **[Type Routing Guide](type_routing.md)**
</div>

<div class="header-card" markdown>
### 🏭 Production Tutorial
End-to-end: Docker, resources, stacks, and remote execution.

→ **[Production Pipeline Tutorial](../tutorials/production-pipeline-tutorial.md)**
</div>

</div>

---

## 🆘 Need Help?

- 💬 Join our [Discord community](https://discord.gg/flowyml)
- 📖 Read the [API Reference](../api/plugins.md)
- 🐛 Report issues on [GitHub](https://github.com/UnicoLab/FlowyML/issues)

# 🔌 FlowyML Plugin System

FlowyML features a **powerful native plugin system** that allows you to integrate with ANY ML tool - MLflow, Kubernetes, AWS S3, and more - **without external framework dependencies**.

## Quick Start

```bash
# Initialize your stack
flowyml stack init --tracker mlflow --store gcs --orchestrator vertex_ai

# Install configured plugins
flowyml stack install
```

```python
# Your code - infrastructure-agnostic
from flowyml.plugins import start_run, log_metrics, save_model

start_run("training")
log_metrics({"accuracy": 0.95})
save_model(model, "classifier")  # Goes wherever config says
```

## Key Benefits

| Feature | FlowyML Plugins |
|---------|-----------------|
| **No framework overhead** | Install only what you need |
| **Direct integration** | Uses underlying tools directly (mlflow, boto3, etc.) |
| **Full control** | FlowyML's own clean interfaces |
| **Easy to extend** | Create your own plugins |
| **Community support** | Install plugins from git |

## Documentation

- **[Stack Configuration](stack-configuration.md)** - Configure your ML stack with `flowyml.yaml`
- **[Native Plugins Guide](native-plugins.md)** - Complete guide to native plugins
- **[Creating Plugins](creating-plugins.md)** - Build custom plugins
- **[Practical Examples](practical-examples.md)** - Real-world usage examples

## Available Plugins

### Experiment Trackers
- `mlflow` - MLflow tracking and model registry
- `wandb` - Weights & Biases
- `neptune` - Neptune.ai
- `tensorboard` - TensorBoard

### Artifact Stores
- `gcs` - Google Cloud Storage ✅
- `s3` - AWS S3 ✅
- `azure_blob` - Azure Blob Storage

### Container Registries
- `gcr` - Google Container/Artifact Registry ✅
- `ecr` - AWS ECR ✅
- `acr` - Azure Container Registry

### Orchestrators
- `vertex_ai` - Google Vertex AI Pipelines ✅
- `sagemaker` - AWS SageMaker Pipelines ✅
- `kubernetes` - Kubernetes
- `airflow` - Apache Airflow

### Model Registries
- `vertex_model_registry` - Vertex AI Model Registry ✅
- `sagemaker_model_registry` - SageMaker Model Registry ✅

### Model Deployers
- `vertex_endpoint` - Vertex AI Endpoints ✅
- `sagemaker_endpoint` - SageMaker Endpoints ✅

### Related Features
- Training Jobs & Batch Prediction
- Feature Stores

## Key Features

### 🎯 Entry Point Discovery

Plugins can register themselves automatically via Python entry points:

```python
# In your plugin's setup.py or pyproject.toml
[project.entry-points."flowyml.plugins"]
my_tracker = "my_package.plugins:MyCustomTracker"
```

FlowyML will auto-discover and register your component!

### 📦 Unified Plugin Management

Discover, install, and manage plugins through a consistent CLI:

```bash
# List available plugins
flowyml plugin list

# Install a plugin
flowyml plugin install mlflow

# Show plugin info
flowyml plugin info mlflow
```

### 🔧 Stack-Based Configuration

Define your infrastructure in YAML:

```yaml
# flowyml.yaml
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

## Architecture

The plugin system is built on three core components:

### 1. Plugin Registry

The central hub that manages all available plugins:

```python
from flowyml.plugins import list_plugins, get_plugin

# List all available plugins
plugins = list_plugins()

# Get a specific plugin instance
tracker = get_plugin("mlflow", tracking_uri="http://localhost:5000")
```

### 2. Base Plugin Classes

Consistent interfaces for each plugin type:

```python
from flowyml.plugins.base import (
    ExperimentTracker,
    ArtifactStorePlugin,
    OrchestratorPlugin,
    ContainerRegistryPlugin,
)
```

### 3. Stack Configuration

YAML-based infrastructure definitions with environment variable support:

```yaml
plugins:
  artifact_store:
    type: s3
    bucket: ${AWS_BUCKET}
    region: ${AWS_REGION}
```

## Quick Example

```python
from flowyml.plugins import (
    start_run, log_params, log_metrics, save_model
)

# Start tracking an experiment
start_run("training_v1")

# Log parameters
log_params({
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100
})

# Training loop
for epoch in range(100):
    # ... training code ...
    log_metrics({"loss": loss, "accuracy": acc}, step=epoch)

# Save the model
save_model(model, "classifier")
```

## Benefits

| Traditional Approach | FlowyML Plugin System |
|---------------------|----------------------|
| ❌ Vendor lock-in | ✅ Framework agnostic |
| ❌ Rewrite components | ✅ Reuse existing components |
| ❌ Manual integration | ✅ Auto-discovery |
| ❌ Choose one framework | ✅ Use multiple tools |
| ❌ Limited ecosystem | ✅ Unlimited ecosystem |

## Next Steps

- [📚 Native Plugins Guide](./native-plugins.md) - Detailed plugin documentation
- [🔧 Creating Custom Plugins](./creating-plugins.md) - Build your own plugins
- [🎯 Practical Examples](./practical-examples.md) - Real-world usage patterns
- [⚙️ Stack Configuration](./stack-configuration.md) - Configure your infrastructure

## Need Help?

- 💬 Join our [Discord community](https://discord.gg/flowyml)
- 📖 Read the [API Reference](../api/plugins.md)
- 🐛 Report issues on [GitHub](https://github.com/UnicoLab/FlowyML/issues)

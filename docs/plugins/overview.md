# 🔌 FlowyML Plugin System

FlowyML features a **powerful native plugin system** that allows you to integrate with ANY ML tool - MLflow, Kubernetes, AWS S3, and more - **without external framework dependencies**.

# FlowyML Plugin System

FlowyML provides a **native plugin system** that integrates seamlessly with cloud ML services without requiring external framework dependencies.

> **Native plugins are the default and recommended approach.** ZenML integration is available as a legacy/optional feature for existing users.

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

## Native Plugins vs ZenML

| Feature | Native Plugins (Default) | ZenML (Legacy) |
|---------|-------------------------|----------------|
| **Dependencies** | Only the tools you use | Full ZenML framework |
| **Configuration** | `flowyml.yaml` | ZenML config system |
| **Overhead** | Minimal | Framework overhead |
| **Flexibility** | Direct access to all features | ZenML abstractions |
| **Recommended** | ✅ Yes | For existing ZenML users |

## Documentation

### Native Plugins (Recommended)

- **[Stack Configuration](stack-configuration.md)** - Configure your ML stack with `flowyml.yaml`
- **[Native Plugins Guide](native-plugins.md)** - Complete guide to native plugins
- **[Implementation Roadmap](plugins_todo_implementation.md)** - Upcoming GCP and AWS plugins

### Legacy Integration

- **[ZenML Integration](zenml-integration.md)** - For existing ZenML users (optional)

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

### Coming Soon
- Vertex Model Registry & Endpoints
- SageMaker Model Registry & Endpoints
- Training Jobs & Batch Prediction
- Feature Stores

## ⚡ Automatic Dependency Management

FlowyML handles all dependencies for you. Just specify what you want:

```bash
# FlowyML installs ZenML and the Kubernetes integration automatically
flowyml zenml install kubernetes

# Import the components and start using them
flowyml zenml import kubernetes
```

**How it works:** When you request a plugin, FlowyML:
1. Installs the external framework if needed (ZenML, etc.)
2. Installs the specific integration and all dependencies
3. Wraps components to work seamlessly with FlowyML's API

> [!TIP]
> **Zero Manual Setup**: You don't need to install ZenML or run separate commands.
> FlowyML manages the entire stack for you.

```bash
# Install your package
pip install my-custom-flowyml-plugin
```

**How it works:** FlowyML's bridge system wraps these components at runtime, adapting their interfaces to work seamlessly with FlowyML's API. No code copying, no manual wrappers needed!

## Key Features

### 🌉 Generic Integration Bridge

A universal adapter that automatically wraps external components to work seamlessly with FlowyML:

```python
from flowyml.stacks.plugins import load_component

# Load ZenML's Kubernetes orchestrator
load_component("zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator")

# Now use it in your FlowyML pipeline!
```

No wrapper code needed. No manual adaptation. It just works.

### 📦 Unified Plugin Management

Discover, install, and manage plugins through a consistent CLI:

```bash
# ZenML integration commands
flowyml zenml list            # List available integrations
flowyml zenml install aws     # Install an integration
flowyml zenml import-all      # Import all components

# General plugin commands
flowyml component list        # List all available components
```

### 🎯 Entry Point Discovery

Plugins can register themselves automatically via Python entry points:

```python
# In your plugin's setup.py or pyproject.toml
[project.entry-points."flowyml.stack_components"]
my_orchestrator = "my_package.components:CustomOrchestrator"
```

FlowyML will auto-discover and register your component!

## Architecture

The plugin system is built on three core components:

### 1. Component Registry

The central hub that manages all available components:

```python
from flowyml.stacks.plugins import get_component_registry

registry = get_component_registry()

# List all orchestrators
print(registry.list_orchestrators())

# Get a specific component
orch_class = registry.get_orchestrator("kubernetes")
```

### 2. Generic Bridge

A smart adapter that uses introspection and rules to translate between frameworks:

```python
from flowyml.stacks.bridge import GenericBridge, AdaptationRule
from flowyml.stacks.components import ComponentType

# Define adaptation rules
rules = [
    AdaptationRule(
        source_type="zenml.orchestrators.base.BaseOrchestrator",
        target_type=ComponentType.ORCHESTRATOR,
        method_mapping={"run_pipeline": "run"}
    )
]

# Create bridge
bridge = GenericBridge(rules=rules)

# Wrap external component
flowyml_component = bridge.wrap_component(ZenMLOrchestrator, "my_orch")
```

### 3. Plugin Configuration

YAML-based definitions for loading external components:

```yaml
# plugins.yaml
plugins:
  - name: kubeflow_orchestrator
    source: zenml.integrations.kubeflow.orchestrators.KubeflowOrchestrator
    component_type: orchestrator
    adaptation:
      method_mapping:
        run_pipeline: run
      attribute_mapping:
        config: settings
```

## Quick Start

### 1. List Available Components

```bash
flowyml component list
```

Output:
```
📦 Registered Components:

Orchestrators:
  • local
  • kubernetes (via zenml)
  • kubeflow (via zenml)

Artifact Stores:
  • local
  • s3 (via zenml)
  • gcs (via zenml)
```

### 2. Load a Component

**From a Module:**
```bash
flowyml component load my_package.components
```

**From ZenML:**
```bash
flowyml component load zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator --name k8s
```

**From a File:**
```bash
flowyml component load /path/to/component.py:MyOrchestrator
```

### 3. Use in Your Pipeline

```python
from flowyml import Pipeline
from flowyml.stacks import Stack
from flowyml.stacks.plugins import get_component_registry

registry = get_component_registry()

# Get the Kubernetes orchestrator we loaded
k8s_orch = registry.get_orchestrator("k8s")

# Create a hybrid stack
stack = Stack(
    name="hybrid",
    orchestrator=k8s_orch(),  # ZenML component
    artifact_store=LocalArtifactStore(),  # FlowyML component
)

# Run your pipeline
pipeline = Pipeline("my_pipeline", stack=stack)
result = pipeline.run()
```

## Supported Integrations

FlowyML's plugin system supports components from:

- **ZenML** - Orchestrators, Artifact Stores, Model Registries, Experiment Trackers
- **Airflow** - Operators, Sensors, Hooks (coming soon)
- **Prefect** - Tasks, Flows (coming soon)
- **MLflow** - Experiment Tracking, Model Registry (coming soon)
- **Custom** - Any Python class following stack component protocols

## Benefits

| Traditional Approach | FlowyML Plugin System |
|---------------------|----------------------|
| ❌ Vendor lock-in | ✅ Framework agnostic |
| ❌ Rewrite components | ✅ Reuse existing components |
| ❌ Manual integration | ✅ Auto-discovery |
| ❌ Choose one framework | ✅ Use multiple frameworks |
| ❌ Limited ecosystem | ✅ Unlimited ecosystem |

## Next Steps

- [📚 Complete Plugin Guide](./complete-guide.md) - Detailed examples and use cases
- [🔧 Creating Custom Plugins](./creating-plugins.md) - Build your own plugins
- [🔄 ZenML Integration](./zenml-examples.md) - Practical ZenML examples
- [🏗️ Plugin Development](./advanced.md) - Advanced bridge configuration

## Need Help?

- 💬 Join our [Discord community](https://discord.gg/flowyml)
- 📖 Read the [API Reference](../api/plugins.md)
- 🐛 Report issues on [GitHub](https://github.com/UnicoLab/FlowyML/issues)

# 🔌 FlowyML Plugin System

FlowyML features a **revolutionary plugin architecture** that allows you to use components from ANY ML framework - ZenML, Airflow, Prefect, MLflow, and more - without modifying their code or creating hard dependencies.

## 🌟 Why This Matters

**Stop choosing between frameworks.** With FlowyML's plugin system, you can:

- ✅ Use ZenML's Kubernetes orchestrator with FlowyML's modern UI
- ✅ Mix Airflow operators with FlowyML pipelines
- ✅ Leverage MLflow tracking with FlowyML's project management
- ✅ Create hybrid stacks combining components from multiple frameworks
- ✅ Access the entire ML ecosystem without vendor lock-in

## ⚠️ Important: Dependency Requirements

**You MUST install the external framework to use its components.**

The plugin system dynamically imports components from installed packages - it does NOT copy or bundle code.

### To Use ZenML Components:

```bash
# Install ZenML
pip install zenml

# Install specific ZenML integrations
zenml integration install kubernetes  # For K8s orchestrator
zenml integration install mlflow      # For MLflow tracking
zenml integration install s3          # For S3 artifact store
```

### To Use Airflow Components (coming soon):

```bash
pip install apache-airflow
```

### To Use Custom Components:

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
# Search for plugins
flowyml plugin search kubernetes

# Install a plugin
flowyml plugin install zenml-kubeflow

# List all available components
flowyml component list
```

### 🔄 Stack Migration

Automatically migrate existing stacks from other frameworks:

```bash
# Import a ZenML stack
flowyml plugin import-zenml-stack production

# Generates flowyml.yaml with all mappings
flowyml run pipeline.py --stack production
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

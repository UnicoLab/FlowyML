# ZenML Integration

FlowyML provides **seamless, automatic integration** with the entire ZenML ecosystem.
With a single command or one line of Python, you can import all ZenML components
(orchestrators, artifact stores, experiment trackers, etc.) and use them as first-class
FlowyML stack components.

> [!TIP]
> **Zero Configuration Required**: FlowyML automatically discovers installed ZenML integrations
> and wraps them for you. No YAML, no manual mapping—just tell FlowyML to import and go.

## Quick Start

### Option 1: Python API (One-Liner)

```python
from flowyml.stacks import import_all_zenml

# Import all installed ZenML components at once
components = import_all_zenml()
# That's it! All ZenML components are now available in FlowyML
```

### Option 2: CLI

```bash
# Check ZenML availability and status
flowyml zenml status

# Import all installed integrations
flowyml zenml import-all
```

### Option 3: Selective Import

```python
from flowyml.stacks import get_component_registry

registry = get_component_registry()

# Import only the integrations you need
registry.import_zenml_integration("mlflow")
registry.import_zenml_integration("kubernetes")
registry.import_zenml_integration("aws")
```

## How It Works

FlowyML's **ZenML Bridge** automatically:

1. **Discovers** all installed ZenML integrations via ZenML's registry
2. **Identifies** the flavors (component implementations) each integration provides
3. **Wraps** each flavor in a FlowyML-compatible component class
4. **Registers** the wrapped components for use in your pipelines

This means you get immediate access to ZenML's rich ecosystem without any manual configuration.

## CLI Commands

FlowyML provides a complete CLI for managing ZenML integrations:

| Command | Description |
|---------|-------------|
| `flowyml zenml status` | Check if ZenML is installed and show integration summary |
| `flowyml zenml list` | List all available ZenML integrations |
| `flowyml zenml list --installed` | Show only installed integrations |
| `flowyml zenml install <name>` | Install a ZenML integration |
| `flowyml zenml import <name>` | Import components from an integration |
| `flowyml zenml import-all` | Import all components from all installed integrations |

### Example Workflow

```bash
# Step 1: Check what's available
flowyml zenml status

# Step 2: Install integrations you need
flowyml zenml install mlflow
flowyml zenml install kubernetes
flowyml zenml install aws

# Step 3: Import all at once
flowyml zenml import-all
```

## Python API

### ComponentRegistry Methods

```python
from flowyml.stacks import get_component_registry

registry = get_component_registry()

# List available integrations
available = registry.list_zenml_integrations()
print(f"Available: {available}")  # ['mlflow', 'kubernetes', 'aws', ...]

# List installed integrations
installed = registry.list_installed_zenml_integrations()
print(f"Installed: {installed}")  # ['mlflow', 'kubernetes']

# Install an integration (calls zenml integration install)
registry.install_zenml_integration("aws")

# Import components from a specific integration
components = registry.import_zenml_integration("mlflow")
for comp in components:
    print(f"Imported: {comp.__name__}")

# Import all components from all installed integrations
all_components = registry.import_all_zenml()
for integration, comps in all_components.items():
    print(f"{integration}: {len(comps)} components")
```

### Direct Bridge Access

For more control, you can use the ZenML Bridge directly:

```python
from flowyml.stacks import get_zenml_bridge

bridge = get_zenml_bridge()

# Check if ZenML is available
if bridge.is_available():
    # Discover integrations
    integrations = bridge.discover_integrations()

    # Wrap a specific ZenML class
    from zenml.integrations.mlflow.experiment_trackers import MLFlowExperimentTracker
    wrapper = bridge.wrap_component(MLFlowExperimentTracker, "mlflow_tracker")
```

## Supported Component Types

FlowyML automatically maps ZenML component types to FlowyML equivalents:

| ZenML Type | FlowyML Type |
|------------|--------------|
| `orchestrator` | `ComponentType.ORCHESTRATOR` |
| `artifact_store` | `ComponentType.ARTIFACT_STORE` |
| `container_registry` | `ComponentType.CONTAINER_REGISTRY` |
| `experiment_tracker` | `ComponentType.EXECUTOR` |
| `model_deployer` | `ComponentType.EXECUTOR` |
| `feature_store` | `ComponentType.EXECUTOR` |
| `step_operator` | `ComponentType.EXECUTOR` |
| `data_validator` | `ComponentType.EXECUTOR` |

## Popular ZenML Integrations

Here are some commonly used ZenML integrations you can use with FlowyML:

### Cloud Providers
- **aws** - S3 artifact store, SageMaker step operator, ECR container registry
- **gcp** - GCS artifact store, Vertex AI step operator, GCR container registry
- **azure** - Azure Blob artifact store, AzureML step operator, ACR container registry

### Experiment Tracking
- **mlflow** - MLflow experiment tracker
- **wandb** - Weights & Biases experiment tracker
- **neptune** - Neptune experiment tracker

### Orchestration
- **kubernetes** - Kubernetes orchestrator
- **airflow** - Apache Airflow orchestrator
- **kubeflow** - Kubeflow Pipelines orchestrator

### ML Frameworks
- **sklearn** - Scikit-learn model deployer
- **pytorch** - PyTorch materializers
- **tensorflow** - TensorFlow materializers
- **huggingface** - Hugging Face model deployer

## Using Wrapped Components

Once imported, ZenML components can be used like any other FlowyML component:

```python
from flowyml.stacks import import_all_zenml, get_component_registry

# Import all ZenML components
import_all_zenml()

# Get a specific component
registry = get_component_registry()
k8s_orch = registry.get_component("ZenMLKubernetesOrchestratorWrapper")

# Use it in a pipeline
if k8s_orch:
    orchestrator = k8s_orch(kubernetes_namespace="ml-pipelines")
    result = orchestrator.run_pipeline(my_pipeline)
```

## Migration from ZenML

If you have existing ZenML stacks, FlowyML makes migration easy:

```python
# Your existing ZenML stack components work seamlessly
from flowyml.stacks import import_all_zenml

# One line imports everything
components = import_all_zenml()

# Now use them in FlowyML pipelines
from flowyml import Pipeline, step

@step(outputs=["model"])
def train():
    return train_model()

pipeline = Pipeline("training")
pipeline.add_step(train)

# Run with your imported ZenML orchestrator
pipeline.run(orchestrator="ZenMLKubernetesOrchestratorWrapper")
```

## Advanced: Manual Component Loading

For specific use cases, you can still load components directly:

```python
from flowyml.stacks.plugins import load_component

# Load a specific ZenML class
mlflow_tracker = load_component(
    "zenml:zenml.integrations.mlflow.experiment_trackers.MLFlowExperimentTracker"
)
```

## Automatic Installation

FlowyML handles everything for you. Just tell it what you want:

```bash
# FlowyML will install ZenML and the MLflow integration automatically
flowyml zenml install mlflow
```

That's it! FlowyML:
1. Installs ZenML if not already present
2. Installs the requested integration and all its dependencies
3. Makes the components immediately available in FlowyML

> [!TIP]
> **No Manual Setup Required**: You don't need to install ZenML separately or run `zenml integration install`.
> FlowyML manages the entire dependency chain for you.

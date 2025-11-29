# Creating Custom Stack Components for flowyml

This guide shows you how to create custom stack components and integrate them seamlessly into flowyml.

## Quick Start

### 1. Create a Custom Component

```python
# my_components.py
from flowyml.stacks.components import Orchestrator
from flowyml.stacks.plugins import register_component

@register_component
class MyOrchestrator(Orchestrator):
    """My custom orchestrator."""

    def __init__(self, name: str = "my_orchestrator", **kwargs):
        super().__init__(name)
        # Your initialization

    def validate(self) -> bool:
        # Validation logic
        return True

    def run_pipeline(self, pipeline, **kwargs):
        # Execution logic
        pass

    def get_run_status(self, run_id: str) -> str:
        # Status checking
        return "SUCCESS"

    def to_dict(self):
        return {"name": self.name, "type": "my_orchestrator"}
```

### 2. Use in Configuration

```yaml
# flowyml.yaml
stacks:
  my_stack:
    type: local
    orchestrator:
      type: my_orchestrator
      # Your custom config
```

### 3. Load Component

```bash
# Auto-loads from my_components.py if in PYTHONPATH
flowyml run pipeline.py --stack my_stack

# Or explicitly load
flowyml component load my_components
```

## Creating Components

### Base Classes

flowyml provides these base classes:

```python
from flowyml.stacks.components import (
    Orchestrator,          # For pipeline orchestration
    ArtifactStore,        # For artifact storage
    ContainerRegistry,    # For Docker images
    StackComponent,       # Generic component
)
```

### Orchestrator Example

```python
from flowyml.stacks.components import Orchestrator
from flowyml.stacks.plugins import register_component

@register_component
class AirflowOrchestrator(Orchestrator):
    def __init__(self, name="airflow", dag_folder="~/airflow/dags"):
        super().__init__(name)
        self.dag_folder = dag_folder

    def validate(self) -> bool:
        try:
            import airflow
            return True
        except ImportError:
            raise ImportError("pip install apache-airflow")

    def run_pipeline(self, pipeline, **kwargs):
        # Convert to Airflow DAG
        from airflow import DAG
        # ... implementation
        return "dag_run_id"

    def get_run_status(self, run_id: str) -> str:
        # Check Airflow DAG run status
        return "RUNNING"

    def to_dict(self):
        return {
            "type": "airflow",
            "dag_folder": self.dag_folder
        }
```

### Artifact Store Example

```python
from flowyml.stacks.components import ArtifactStore
from flowyml.stacks.plugins import register_component

@register_component
class MinIOArtifactStore(ArtifactStore):
    def __init__(
        self,
        name="minio",
        endpoint="localhost:9000",
        bucket="flowyml"
    ):
        super().__init__(name)
        self.endpoint = endpoint
        self.bucket = bucket

    def validate(self) -> bool:
        from minio import Minio
        client = Minio(self.endpoint)
        return client.bucket_exists(self.bucket)

    def save(self, artifact, path: str) -> str:
        # Save to MinIO
        return f"s3://{self.bucket}/{path}"

    def load(self, path: str):
        # Load from MinIO
        pass

    def exists(self, path: str) -> bool:
        # Check existence
        return True

    def to_dict(self):
        return {
            "type": "minio",
            "endpoint": self.endpoint,
            "bucket": self.bucket
        }
```

## Registration Methods

### Method 1: Decorator (Recommended)

```python
from flowyml.stacks.plugins import register_component

@register_component
class MyComponent(Orchestrator):
    pass

# Or with custom name
@register_component(name="custom_name")
class MyComponent(Orchestrator):
    pass
```

### Method 2: Manual Registration

```python
from flowyml.stacks.plugins import get_component_registry

class MyComponent(Orchestrator):
    pass

registry = get_component_registry()
registry.register(MyComponent, "my_component")
```

### Method 3: Entry Points (for packages)

In your `pyproject.toml`:

```toml
[project.entry-points."flowyml.stack_components"]
my_orchestrator = "my_package.components:MyOrchestrator"
my_artifact_store = "my_package.components:MyArtifactStore"
```

Then components auto-load when package is installed!

## Loading Components

### From Module

```python
from flowyml.stacks.plugins import load_component

# Load all components from module
load_component("my_package.components")
```

### From File

```python
# Load specific class from file
load_component("/path/to/component.py:MyOrchestrator")
```

### From Configuration

```yaml
# flowyml.yaml
components:
  - module: my_package.components
  - file: /path/to/custom.py:CustomComponent
```

## Using ZenML Components

### Wrap ZenML Component

```python
from flowyml.stacks.plugins import get_component_registry

# Load ZenML component
registry = get_component_registry()
registry.wrap_zenml_component(
    zenml_component_class=KubernetesOrchestrator,
    name="k8s"
)
```

### Via Configuration

```yaml
# flowyml.yaml
components:
  - zenml: zenml.orchestrators.kubernetes.KubernetesOrchestrator
    name: k8s

stacks:
  k8s_stack:
    orchestrator:
      type: k8s
      # ZenML config
```

### Using the CLI

```bash
# Load ZenML component
flowyml component load zenml:zenml.orchestrators.kubernetes.KubernetesOrchestrator

# List available components
flowyml component list
```

## Component Discovery

flowyml automatically discovers components from:

1. **Installed packages** with entry points
2. **`PYTHONPATH`** - any module in path
3. **Current directory** - `./components/` folder
4. **Configuration** - `flowyml.yaml` components section

## Publishing Components

### As Python Package

```python
# setup.py or pyproject.toml
[project.entry-points."flowyml.stack_components"]
my_orchestrator = "my_flowyml_plugin:MyOrchestrator"
```

```bash
pip install my-flowyml-plugin

# Auto-available in flowyml!
flowyml component list
```

### As Module

```bash
# Add to PYTHONPATH
export PYTHONPATH=/path/to/components:$PYTHONPATH

# Or install in development mode
pip install -e /path/to/my-components
```

## Community Components

### Using Existing Components

```bash
# Install from PyPI
pip install flowyml-airflow-orchestrator
pip install flowyml-minio-store

# Automatically available!
```

### Creating Shareable Components

```
my-flowyml-components/
├── pyproject.toml
├── README.md
└── my_flowyml_components/
    ├── __init__.py
    ├── airflow_orchestrator.py
    └── minio_store.py
```

```toml
# pyproject.toml
[project]
name = "my-flowyml-components"
version = "0.1.0"

[project.entry-points."flowyml.stack_components"]
airflow = "my_flowyml_components.airflow_orchestrator:AirflowOrchestrator"
minio = "my_flowyml_components.minio_store:MinIOArtifactStore"
```

## Advanced: ZenML Integration

### Complete ZenML Compatibility

```python
from zenml.stack import Stack as ZenMLStack
from flowyml.stacks.plugins import get_component_registry

# Import all ZenML components
def import_zenml_stack(zenml_stack: ZenMLStack):
    registry = get_component_registry()

    # Wrap each component
    registry.wrap_zenml_component(
        zenml_stack.orchestrator,
        "zenml_orchestrator"
    )

    registry.wrap_zenml_component(
        zenml_stack.artifact_store,
        "zenml_artifact_store"
    )

    # Now use in flowyml!
```

### Gradual Migration from ZenML

```python
# Keep using ZenML components
from zenml.integrations.kubernetes import KubernetesOrchestrator

# Use in flowyml
from flowyml.stacks import Stack
from flowyml.stacks.plugins import get_component_registry

registry = get_component_registry()
registry.wrap_zenml_component(KubernetesOrchestrator, "k8s")

# Create flowyml stack with ZenML component
stack = Stack(
    name="hybrid",
    orchestrator=registry.get_orchestrator("k8s"),
    # ... other components
)
```

## Examples

See:
- `examples/custom_components/my_components.py` - Complete examples
- `examples/custom_components/airflow_integration.py` - Airflow integration
- `examples/custom_components/minio_integration.py` - MinIO integration

## Best Practices

1. ✅ **Use `@register_component` decorator**
2. ✅ **Implement all required methods**
3. ✅ **Add comprehensive validation**
4. ✅ **Include good documentation**
5. ✅ **Provide configuration examples**
6. ✅ **Test thoroughly**
7. ✅ **Publish as package for reuse**

## Testing Custom Components

```python
import unittest
from my_components import MyOrchestrator

class TestMyOrchestrator(unittest.TestCase):
    def test_validation(self):
        orch = MyOrchestrator()
        self.assertTrue(orch.validate())

    def test_run_pipeline(self):
        # Test pipeline execution
        pass
```

## Next Steps

- Create your custom component
- Test locally
- Publish to PyPI
- Share with community!

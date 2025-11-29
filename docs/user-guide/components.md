# Stack Components and Extensibility

## Overview

flowyml's stack system is built on a powerful plugin architecture that makes it easy to extend with custom components, integrate with existing tools, and even reuse components from the ZenML ecosystem.

## 📚 Table of Contents

- [Core Concepts](#core-concepts)
- [Built-in Components](#built-in-components)
- [Creating Custom Components](#creating-custom-components)
- [Component Registration](#component-registration)
- [Using Custom Components](#using-custom-components)
- [Publishing Components](#publishing-components)
- [ZenML Integration](#zenml-integration)
- [API Reference](#api-reference)

## Core Concepts

### What is a Stack Component?

A **stack component** is a modular piece of infrastructure that performs a specific function in your ML pipeline:

- **Orchestrator**: Manages pipeline execution and scheduling
- **Artifact Store**: Stores pipeline artifacts and outputs
- **Container Registry**: Manages Docker images
- **Metadata Store**: Tracks pipeline runs and lineage

### Component Hierarchy

```
StackComponent (Base Class)
├── Orchestrator
│   ├── VertexAIOrchestrator
│   ├── AirflowOrchestrator (custom)
│   └── KubernetesOrchestrator (custom)
│
├── ArtifactStore
│   ├── LocalArtifactStore
│   ├── GCSArtifactStore
│   ├── S3ArtifactStore (custom)
│   └── MinIOArtifactStore (custom)
│
└── ContainerRegistry
    ├── GCRContainerRegistry
    ├── ECRContainerRegistry (custom)
    └── DockerHubRegistry (custom)
```

## Built-in Components

### Local Stack Components

**LocalExecutor**
- Runs steps in the current process
- Perfect for development and testing
- No external dependencies

**LocalArtifactStore**
- Stores artifacts on local filesystem
- Fast and simple
- Good for prototyping

**SQLiteMetadataStore**
- Tracks runs in SQLite database
- Lightweight and portable
- No server required

### GCP Stack Components

**VertexAIOrchestrator**
- Managed ML platform on Google Cloud
- Scalable and reliable
- Integrated with GCP services

**GCSArtifactStore**
- Google Cloud Storage integration
- Durable and scalable
- Global availability

**GCRContainerRegistry**
- Google Container Registry
- Integrated with GCP
- Automated builds

## Creating Custom Components

### Basic Component Structure

Every component must:
1. Inherit from the appropriate base class
2. Implement required methods
3. Register itself (optionally via decorator)

### Example: Custom Orchestrator

```python
from flowyml.stacks.components import Orchestrator, ResourceConfig, DockerConfig
from flowyml.stacks.plugins import register_component
from typing import Any

@register_component
class AirflowOrchestrator(Orchestrator):
    """
    Apache Airflow orchestrator for flowyml.

    Converts flowyml pipelines to Airflow DAGs and manages execution.
    """

    def __init__(
        self,
        name: str = "airflow",
        airflow_home: str = "~/airflow",
        dag_folder: str = "~/airflow/dags",
    ):
        """Initialize Airflow orchestrator."""
        super().__init__(name)
        self.airflow_home = airflow_home
        self.dag_folder = dag_folder

    def validate(self) -> bool:
        """Validate Airflow is installed and configured."""
        try:
            import airflow
            from pathlib import Path

            # Check DAG folder exists
            dag_path = Path(self.dag_folder).expanduser()
            if not dag_path.exists():
                dag_path.mkdir(parents=True)

            return True
        except ImportError:
            raise ImportError(
                "Apache Airflow not installed. "
                "Install with: pip install apache-airflow"
            )

    def run_pipeline(
        self,
        pipeline: Any,
        resources: ResourceConfig = None,
        docker_config: DockerConfig = None,
        **kwargs
    ) -> str:
        """
        Convert pipeline to Airflow DAG and execute.

        Args:
            pipeline: flowyml pipeline to execute
            resources: Resource configuration (optional)
            docker_config: Docker configuration (optional)
            **kwargs: Additional arguments

        Returns:
            DAG run ID
        """
        from airflow import DAG
        from airflow.operators.python import PythonOperator
        from datetime import datetime

        # Create Airflow DAG
        dag = DAG(
            dag_id=pipeline.name,
            default_args={'owner': 'flowyml'},
            start_date=datetime.now(),
            schedule_interval=None,
        )

        # Convert steps to tasks
        tasks = {}
        for step in pipeline.steps:
            task = PythonOperator(
                task_id=step.name,
                python_callable=step.func,
                dag=dag,
            )
            tasks[step.name] = task

        # Set dependencies
        for i in range(len(pipeline.steps) - 1):
            tasks[pipeline.steps[i].name] >> tasks[pipeline.steps[i+1].name]

        # Trigger DAG run
        run_id = f"flowyml_{pipeline.run_id}"
        dag.create_dagrun(run_id=run_id, state='running')

        return run_id

    def get_run_status(self, run_id: str) -> str:
        """Get DAG run status."""
        from airflow.models import DagRun

        dagrun = DagRun.find(run_id=run_id)
        return dagrun[0].state if dagrun else "UNKNOWN"

    def to_dict(self):
        """Serialize configuration."""
        return {
            "type": "airflow",
            "airflow_home": self.airflow_home,
            "dag_folder": self.dag_folder,
        }
```

### Example: Custom Artifact Store

```python
from flowyml.stacks.components import ArtifactStore
from flowyml.stacks.plugins import register_component
from typing import Any

@register_component
class MinIOArtifactStore(ArtifactStore):
    """
    MinIO object storage integration.

    MinIO is an S3-compatible object storage system that can run
    on-premises or in the cloud.
    """

    def __init__(
        self,
        name: str = "minio",
        endpoint: str = "localhost:9000",
        bucket: str = "flowyml",
        access_key: str = "",
        secret_key: str = "",
        secure: bool = False,
    ):
        """Initialize MinIO artifact store."""
        super().__init__(name)
        self.endpoint = endpoint
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self._client = None

    @property
    def client(self):
        """Lazy-load MinIO client."""
        if self._client is None:
            from minio import Minio

            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )

            # Ensure bucket exists
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)

        return self._client

    def validate(self) -> bool:
        """Validate MinIO connection."""
        try:
            from minio import Minio
            # Try to connect
            _ = self.client
            return True
        except ImportError:
            raise ImportError(
                "MinIO client not installed. "
                "Install with: pip install minio"
            )
        except Exception as e:
            raise ConnectionError(f"Cannot connect to MinIO: {e}")

    def save(self, artifact: Any, path: str) -> str:
        """Save artifact to MinIO."""
        import pickle
        import io

        # Serialize artifact
        data = pickle.dumps(artifact)
        data_stream = io.BytesIO(data)

        # Upload
        self.client.put_object(
            self.bucket,
            path,
            data_stream,
            length=len(data),
        )

        return f"s3://{self.bucket}/{path}"

    def load(self, path: str) -> Any:
        """Load artifact from MinIO."""
        import pickle

        # Handle s3:// URIs
        if path.startswith("s3://"):
            path = path.replace(f"s3://{self.bucket}/", "")

        # Download
        response = self.client.get_object(self.bucket, path)
        data = response.read()

        return pickle.loads(data)

    def exists(self, path: str) -> bool:
        """Check if artifact exists."""
        try:
            self.client.stat_object(self.bucket, path)
            return True
        except:
            return False

    def to_dict(self):
        """Serialize configuration."""
        return {
            "type": "minio",
            "endpoint": self.endpoint,
            "bucket": self.bucket,
            "secure": self.secure,
        }
```

### Required Methods

All components must implement:

**`validate() -> bool`**
- Verify component is properly configured
- Check dependencies are installed
- Test connections if applicable
- Raise descriptive errors if validation fails

**`to_dict() -> Dict[str, Any]`**
- Serialize component configuration
- Used for persistence and display
- Should include all important settings

**Component-specific methods:**

For **Orchestrator**:
- `run_pipeline(pipeline, **kwargs) -> str`: Execute pipeline, return run ID
- `get_run_status(run_id: str) -> str`: Get execution status

For **ArtifactStore**:
- `save(artifact: Any, path: str) -> str`: Save artifact, return URI
- `load(path: str) -> Any`: Load and return artifact
- `exists(path: str) -> bool`: Check if artifact exists

For **ContainerRegistry**:
- `push_image(image_name: str, tag: str) -> str`: Push image, return URI
- `pull_image(image_name: str, tag: str)`: Pull image
- `get_image_uri(image_name: str, tag: str) -> str`: Get full image URI

## Component Registration

### Method 1: Decorator (Recommended)

```python
from flowyml.stacks.plugins import register_component

@register_component
class MyComponent(Orchestrator):
    pass

# Or with custom name
@register_component(name="my_custom_name")
class MyComponent(Orchestrator):
    pass
```

**Advantages:**
- Clean and declarative
- Auto-registration on import
- No additional code needed

### Method 2: Manual Registration

```python
from flowyml.stacks.plugins import get_component_registry

class MyComponent(Orchestrator):
    pass

# Register manually
registry = get_component_registry()
registry.register(MyComponent, "my_component")
```

**Advantages:**
- More control over registration
- Can register at runtime
- Useful for dynamic components

### Method 3: Entry Points (Best for Packages)

```toml
# pyproject.toml
[project.entry-points."flowyml.stack_components"]
my_orchestrator = "my_package.components:MyOrchestrator"
my_store = "my_package.stores:MyArtifactStore"
```

**Advantages:**
- Auto-discovery on package installation
- No import needed
- Standard Python packaging mechanism
- Discoverable by tools

### Method 4: Dynamic Loading

```python
from flowyml.stacks.plugins import load_component

# From module
load_component("my_package.components")

# From file
load_component("/path/to/component.py:MyClass")

# From ZenML
load_component("zenml:zenml.orchestrators.kubernetes.KubernetesOrchestrator")
```

**Advantages:**
- Load components on demand
- No code changes
- Support for external sources
- CLI-friendly

## Using Custom Components

### In Configuration Files

```yaml
# flowyml.yaml
stacks:
  custom_stack:
    type: local
    orchestrator:
      type: airflow  # Your custom orchestrator
      dag_folder: ~/airflow/dags

    artifact_store:
      type: minio  # Your custom artifact store
      endpoint: localhost:9000
      bucket: ml-artifacts
      access_key: ${MINIO_ACCESS_KEY}
      secret_key: ${MINIO_SECRET_KEY}

resources:
  default:
    cpu: "2"
    memory: "8Gi"
```

### Programmatically

```python
from my_components import AirflowOrchestrator, MinIOArtifactStore
from flowyml.stacks import Stack
from flowyml.storage.metadata import SQLiteMetadataStore

# Create components
orchestrator = AirflowOrchestrator(dag_folder="~/airflow/dags")
artifact_store = MinIOArtifactStore(
    endpoint="localhost:9000",
    bucket="ml-artifacts"
)
metadata_store = SQLiteMetadataStore()

# Create stack
stack = Stack(
    name="custom",
    executor=None,  # Airflow handles execution
    artifact_store=artifact_store,
    metadata_store=metadata_store,
    orchestrator=orchestrator,
)

# Use with pipeline
from flowyml import Pipeline

pipeline = Pipeline("my_pipeline", stack=stack)
result = pipeline.run()
```

### Via CLI

```bash
# Load custom component
flowyml component load my_components

# List available
flowyml component list

# Run with custom stack
flowyml run pipeline.py --stack custom_stack
```

## Publishing Components

### Package Structure

```
flowyml-airflow/
├── pyproject.toml
├── README.md
├── LICENSE
├── tests/
│   └── test_orchestrator.py
└── flowyml_airflow/
    ├── __init__.py
    └── orchestrator.py
```

### pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "flowyml-airflow"
version = "0.1.0"
description = "Apache Airflow orchestrator for flowyml"
authors = [{name = "Your Name", email = "you@example.com"}]
readme = "README.md"
license = {text = "Apache-2.0"}
requires-python = ">=3.8"
dependencies = [
    "flowyml>=0.1.0",
    "apache-airflow>=2.5.0",
]

keywords = ["flowyml", "airflow", "ml", "orchestration", "plugin"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries",
]

[project.urls]
Homepage = "https://github.com/yourusername/flowyml-airflow"
Documentation = "https://flowyml-airflow.readthedocs.io"

# Entry point registration
[project.entry-points."flowyml.stack_components"]
airflow = "flowyml_airflow.orchestrator:AirflowOrchestrator"

[tool.hatch.build.targets.wheel]
packages = ["flowyml_airflow"]
```

### Publishing Workflow

1. **Build package:**
```bash
python -m build
```

2. **Test locally:**
```bash
pip install -e .
flowyml component list  # Should show your component
```

3. **Upload to PyPI:**
```bash
python -m twine upload dist/*
```

4. **Users install:**
```bash
pip install flowyml-airflow
# Component auto-available!
```

### README Template

```markdown
# flowyml Airflow Orchestrator

Apache Airflow orchestrator plugin for flowyml.

## Installation

```bash
pip install flowyml-airflow
```

## Usage

```yaml
# flowyml.yaml
stacks:
  airflow_stack:
    orchestrator:
      type: air flow
      dag_folder: ~/airflow/dags
```

```bash
flowyml run pipeline.py --stack airflow_stack
```

## Configuration

- `dag_folder`: Path to Airflow DAGs folder
- `airflow_home`: Airflow home directory (optional)

## License

Apache-2.0
```

## ZenML Integration

### Wrapping ZenML Components

```python
from flowyml.stacks.plugins import get_component_registry

# Import ZenML component
from zenml.integrations.kubernetes.orchestrators import KubernetesOrchestrator

# Wrap it
registry = get_component_registry()
registry.wrap_zenml_component(
    KubernetesOrchestrator,
    name="k8s"
)

# Use immediately!
```

### Via Configuration

```yaml
# flowyml.yaml
components:
  - zenml: zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator
    name: k8s

  - zenml: zenml.integrations.aws.artifact_stores.S3ArtifactStore
    name: s3

stacks:
  zenml_stack:
    orchestrator:
      type: k8s
    artifact_store:
      type: s3
```

### Complete Stack Migration

```python
from zenml.client import Client
from flowyml.stacks.plugins import get_component_registry
from flowyml.stacks import Stack

# Get ZenML stack
zenml_client = Client()
zenml_stack = zenml_client.active_stack

# Wrap all components
registry = get_component_registry()
registry.wrap_zenml_component(zenml_stack.orchestrator, "orch")
registry.wrap_zenml_component(zenml_stack.artifact_store, "store")

# Create flowyml stack
flowyml_stack = Stack(
    name=f"migrated_{zenml_stack.name}",
    orchestrator=registry.get_orchestrator("orch"),
    artifact_store=registry.get_artifact_store("store"),
    metadata_store=None,  # Use local
)

# Use with flowyml pipelines!
```

## API Reference

### ComponentRegistry

**`register(component_class, name=None)`**
Register a component class.

**`get_orchestrator(name) -> Type[Orchestrator]`**
Get orchestrator class by name.

**`get_artifact_store(name) -> Type[ArtifactStore]`**
Get artifact store class by name.

**`list_all() -> Dict[str, List[str]]`**
List all registered components.

**`load_from_module(module_path)`**
Load all components from a module.

**`wrap_zenml_component(zenml_class, name)`**
Wrap a ZenML component for flowyml.

### Decorators

**`@register_component`**
Auto-register a component class.

**`@register_component(name="custom")`**
Register with custom name.

### Functions

**`get_component_registry() -> ComponentRegistry`**
Get global registry instance.

**`load_component(source, name=None)`**
Load component from various sources.

## Best Practices

1. ✅ **Use type hints** for better IDE support
2. ✅ **Add comprehensive docstrings**
3. ✅ **Implement proper validation**
4. ✅ **Handle errors gracefully**
5. ✅ **Write tests** for your components
6. ✅ **Document configuration options**
7. ✅ **Follow naming conventions**
8. ✅ **Use semantic versioning**
9. ✅ **Publish to PyPI** for easy sharing
10. ✅ **Add examples** to README

## Troubleshooting

### Component Not Found

```bash
# List registered components
flowyml component list

# Load explicitly
flowyml component load my_package.components
```

### Import Errors

```python
# Check if component module is importable
python -c "import my_package.components"

# Check entry points
python -c "from importlib.metadata import entry_points; print(entry_points(group='flowyml.stack_components'))"
```

### Validation Failures

```python
# Test component validation
from my_components import MyOrchestrator

orch = MyOrchestrator()
try:
    orch.validate()
    print("✅ Validation passed")
except Exception as e:
    print(f"❌ Validation failed: {e}")
```

## Examples

See:
- [`examples/custom_components/my_components.py`](https://github.com/UnicoLab/FlowyML/blob/main/examples/custom_components/my_components.py)
- [`examples/custom_components/zenml_integration.py`](https://github.com/UnicoLab/FlowyML/blob/main/examples/custom_components/zenml_integration.py)
- [`examples/custom_components/PACKAGE_TEMPLATE.md`](https://github.com/UnicoLab/FlowyML/blob/main/examples/custom_components/PACKAGE_TEMPLATE.md)

## Next Steps

- [Configuration Guide](./configuration.md)
- [CLI Reference](../reference/cli.md)

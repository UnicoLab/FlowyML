# 🔧 Creating Custom Plugins

FlowyML is designed to be fully extensible. While the native plugin system supports many popular tools out of the box, you can easily create your own plugins to integrate with any tool or service.

## Plugin Architecture

All plugins in FlowyML inherit from `BasePlugin` and potentially a more specific subclass depending on their role (e.g., `ExperimentTracker`, `ArtifactStorePlugin`).

### Base Classes

| Class | Purpose | Import Path |
|-------|---------|-------------|
| `BasePlugin` | All plugins inherit from this | `flowyml.plugins.base` |
| `ExperimentTracker` | For tracking metrics/params | `flowyml.plugins.base` |
| `ArtifactStorePlugin` | For saving/loading files | `flowyml.plugins.base` |
| `OrchestratorPlugin` | For running pipelines | `flowyml.plugins.base` |
| `ContainerRegistryPlugin` | For docker images | `flowyml.plugins.base` |

## Step-by-Step Guide

Let's build a custom **Experiment Tracker** for a hypothetical tool called "MyLogger".

### 1. Create the Plugin Class

Create a new file `my_logger_plugin.py`:

```python
from typing import Optional, Dict, Any
from flowyml.plugins.base import ExperimentTracker, PluginMetadata, PluginType

class MyLoggerTracker(ExperimentTracker):
    """Custom experiment tracker for MyLogger service."""

    # Define metadata for discovery
    METADATA = PluginMetadata(
        name="mylogger",
        description="Integration with MyLogger service",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        packages=["mylogger-sdk>=1.0.0"],  # Required pip packages
    )

    def __init__(self, api_key: str, project_name: str, **kwargs):
        """Initialize the plugin with configuration."""
        super().__init__(**kwargs)
        self.api_key = api_key
        self.project_name = project_name
        self._client = None

    def initialize(self):
        """Called once before usage. Great for connecting to APIs."""
        import mylogger
        self._client = mylogger.Client(self.api_key)
        self._client.set_project(self.project_name)

    def validate(self) -> bool:
        """Check if plugin is correctly configured."""
        if not self.api_key:
            raise ValueError("api_key is required for MyLogger")
        return True

    # Implement abstract methods from ExperimentTracker

    def start_run(self, run_name: str, **kwargs) -> str:
        run = self._client.create_run(name=run_name)
        return run.id

    def end_run(self, status: str = "FINISHED") -> None:
        self._client.finish_run(status=status)

    def log_params(self, params: Dict[str, Any]) -> None:
        self._client.log_parameters(params)

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        self._client.log_metrics(metrics, step=step)
```

### 2. Register the Plugin

You have two main ways to register your plugin so FlowyML can find it.

#### Option A: Entry Points (Recommended for Packages)

If you are packaging your plugin as a library, use Python's entry point mechanism. Add this to your `pyproject.toml`:

```toml
[project.entry-points."flowyml.plugins"]
mylogger = "my_package.my_logger_plugin:MyLoggerTracker"
```

When users install your package, FlowyML automatically discovers `mylogger`.

#### Option B: Runtime Registration (For Local Scripts)

If you just have a local script, you can register it manually:

```python
from flowyml.plugins import register_plugin
from my_logger_plugin import MyLoggerTracker

# Register the class
register_plugin(MyLoggerTracker)
```

### 3. Use Your Plugin

Now you can configure and use it just like a native plugin!

```yaml
# flowyml.yaml
plugins:
  experiment_tracker:
    type: mylogger
    api_key: ${MYLOGGER_API_KEY}
    project_name: "my-awesome-project"
```

```python
from flowyml.plugins import get_tracker, start_run, log_metrics

# Get instance
tracker = get_tracker()

# Use standardized API
start_run("experiment-1")
log_metrics({"accuracy": 0.98})
```

## Best Practices

### 1. Lazy Imports

Do not import heavy dependencies at the top level of your module. Import them inside `initialize()` or specific methods. This keeps the CLI fast.

**Bad:**
```python
import tensorflow as tf  # Slow!
class MyPlugin(BasePlugin): ...
```

**Good:**
```python
class MyPlugin(BasePlugin):
    def initialize(self):
        import tensorflow as tf  # Only imported when needed
```

### 2. Error Handling

Wrap external tool errors in friendly messages:

```python
try:
    self._client.connect()
except ConnectionError as e:
    # Re-raise with context
    raise ConnectionError(
        f"Could not connect to MyLogger. Check your API key. Details: {e}"
    )
```

### 3. Configuration Validation

Use the `validate()` method to ensure all required config is present before the pipeline starts running.

### 4. Metadata

Always fill out `METADATA`. It helps users understand what your plugin does and what packages it requires.

```python
METADATA = PluginMetadata(
    name="my_plugin",
    description="...",
    packages=["required-lib"]
)
```

## Testing Your Plugin

FlowyML makes testing easy.

```python
import pytest
from my_logger_plugin import MyLoggerTracker

def test_tracker_validation():
    # Should fail without api_key
    with pytest.raises(ValueError):
        tracker = MyLoggerTracker(api_key=None, project_name="test")
        tracker.validate()

def test_tracker_logging(mocker):
    # Mock external lib
    mocker.patch("mylogger.Client")

    tracker = MyLoggerTracker(api_key="secret", project_name="test")
    tracker.initialize()

    tracker.log_metrics({"acc": 0.9})
    # Verify mock was called ...
```

## Next Steps

- Check out the **[Practical Examples](practical-examples.md)** to see more code.
- Read the **[Base Plugin API](../api/plugins.md)** for detailed method signatures.

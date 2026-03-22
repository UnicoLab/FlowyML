# FlowyML Native Plugin System

FlowyML provides a powerful, extensible plugin system that allows you to integrate with external tools **without requiring any framework dependencies**. Simply install the plugin you need, and FlowyML handles the rest.

## Quick Start 🚀

```bash
# List available plugins
flowyml plugin list

# Install a plugin (installs underlying packages directly)
flowyml plugin install mlflow

# Show plugin info
flowyml plugin info mlflow
```

```python
# Use in Python
from flowyml.plugins import get_plugin

# Get a pre-configured tracker
tracker = get_plugin("mlflow", tracking_uri="http://localhost:5000")

# Start tracking
tracker.start_run("my_experiment")
tracker.log_params({"learning_rate": 0.001})
tracker.log_metrics({"accuracy": 0.95})
tracker.end_run()
```

## Key Benefits 🎯

| Feature | FlowyML Plugins |
|---------|-----------------|
| **No framework overhead** | Install only what you need |
| **Direct integration** | Uses underlying tools directly (mlflow, boto3, etc.) |
| **Full control** | FlowyML's own clean interfaces |
| **Easy to extend** | Create your own plugins |
| **Community support** | Install plugins from git |

## Available Plugins 📦

### Experiment Trackers

| Plugin | Description | Packages |
|--------|-------------|----------|
| `mlflow` | MLflow experiment tracking & model registry | mlflow |
| `wandb` | Weights & Biases tracking | wandb |
| `neptune` | Neptune.ai tracking | neptune |
| `tensorboard` | TensorBoard visualization | tensorboard |

### Artifact Stores

| Plugin | Description | Packages |
|--------|-------------|----------|
| `s3` | AWS S3 storage | boto3, s3fs |
| `gcs` | Google Cloud Storage | google-cloud-storage, gcsfs |
| `azure_blob` | Azure Blob Storage | azure-storage-blob, adlfs |

### Orchestrators

| Plugin | Description | Packages |
|--------|-------------|----------|
| `kubernetes` | Kubernetes orchestration | kubernetes |
| `airflow` | Apache Airflow DAGs | apache-airflow |
| `kubeflow` | Kubeflow Pipelines | kfp |
| `ray` | Ray distributed computing | ray |

### Container Registries

| Plugin | Description | Packages |
|--------|-------------|----------|
| `docker` | Local Docker registry | docker |
| `ecr` | AWS Elastic Container Registry | boto3 |
| `gcr` | Google Container Registry | google-cloud-artifact-registry |
| `acr` | Azure Container Registry | azure-mgmt-containerregistry |

### Feature Stores

| Plugin | Description | Packages |
|--------|-------------|----------|
| `feast` | Feast feature store | feast |

### Data Validators

| Plugin | Description | Packages |
|--------|-------------|----------|
| `great_expectations` | Great Expectations validation | great_expectations |
| `pandera` | Pandera DataFrame validation | pandera |

### Alerters

| Plugin | Description | Packages |
|--------|-------------|----------|
| `slack` | Slack notifications | slack-sdk |
| `discord` | Discord webhooks | discord-webhook |
| `pagerduty` | PagerDuty incidents | pdpyras |

### Model Registries

| Plugin | Description | Packages |
|--------|-------------|----------|
| `vertex_model_registry` | Vertex AI Model Registry | google-cloud-aiplatform |
| `sagemaker_model_registry` | SageMaker Model Registry | boto3, sagemaker |

### Model Deployers

| Plugin | Description | Packages |
|--------|-------------|----------|
| `vertex_endpoint` | Vertex AI Endpoints | google-cloud-aiplatform |
| `sagemaker_endpoint` | SageMaker Endpoints | boto3 |

## Plugin Usage Examples 💡

### MLflow Experiment Tracking

```python
from flowyml.plugins import install, get_plugin

# Install MLflow (one-time)
install("mlflow")

# Create tracker
tracker = get_plugin("mlflow",
    tracking_uri="http://localhost:5000",
    experiment_name="my_experiments"
)

# Track an experiment
tracker.start_run("training_v1")
tracker.log_params({
    "model_type": "random_forest",
    "n_estimators": 100,
    "max_depth": 10,
})

# Log metrics during training
for epoch in range(10):
    tracker.log_metrics({
        "train_loss": 0.5 - (epoch * 0.04),
        "val_accuracy": 0.7 + (epoch * 0.02),
    }, step=epoch)

# Log model
tracker.log_model(model, "models/classifier", model_type="sklearn")

tracker.end_run()
```

### S3 Artifact Storage

```python
from flowyml.plugins import install, get_plugin

# Install S3 plugin (one-time)
install("s3")

# Create store
store = get_plugin("s3",
    bucket="my-ml-artifacts",
    prefix="experiments/run_001/",
    region="us-east-1"
)

# Save artifacts
store.save({"accuracy": 0.95, "f1": 0.92}, "metrics.json")
store.save(model, "model.pkl")
store.save_file("./results/report.html", "reports/report.html")

# Load artifacts
metrics = store.load("metrics.json")
model = store.load("model.pkl")

# List artifacts
artifacts = store.list()  # Returns all artifacts in prefix
```

### Using Multiple Plugins Together

```python
from flowyml.plugins import get_plugin

# Get plugins
tracker = get_plugin("mlflow", tracking_uri="http://localhost:5000")
store = get_plugin("s3", bucket="my-artifacts")

# Run experiment with tracking and storage
tracker.start_run("experiment_001")

# Train model...
tracker.log_params(model_params)
tracker.log_metrics(evaluation_results)

# Save to S3
model_uri = store.save(model, "models/latest.pkl")
tracker.set_tag("model_uri", model_uri)

tracker.end_run()
```

## CLI Commands 🖥️

```bash
# List all available plugins
flowyml plugin list

# List only installed plugins
flowyml plugin list --installed

# Filter by type
flowyml plugin list --type experiment_tracker

# Install a plugin
flowyml plugin install mlflow
flowyml plugin install s3

# Upgrade a plugin
flowyml plugin install mlflow --upgrade

# Show plugin details
flowyml plugin info mlflow

# Uninstall a plugin
flowyml plugin uninstall mlflow

# Install from git (community plugins)
flowyml plugin install-git https://github.com/user/flowyml-custom-plugin.git
```

## Creating Custom Plugins 🔧

You can create your own plugins by extending the base classes:

```python
from flowyml.plugins.base import ExperimentTracker, PluginMetadata, PluginType

class MyCustomTracker(ExperimentTracker):
    """My custom experiment tracker."""

    METADATA = PluginMetadata(
        name="my_tracker",
        description="My custom tracking solution",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        packages=["my-tracking-lib>=1.0"],
    )

    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key

    def start_run(self, run_name: str, experiment_name: str = None, tags: dict = None) -> str:
        # Your implementation
        ...

    def end_run(self, status: str = "FINISHED") -> None:
        # Your implementation
        ...

    def log_params(self, params: dict) -> None:
        # Your implementation
        ...

    def log_metrics(self, metrics: dict, step: int = None) -> None:
        # Your implementation
        ...
```

### Publishing Community Plugins

To make your plugin discoverable, add an entry point in your `pyproject.toml`:

```toml
[project.entry-points."flowyml.plugins"]
my_tracker = "my_package.plugins:MyCustomTracker"
```

When users install your package, FlowyML will automatically discover it:

```bash
pip install my-flowyml-plugin
flowyml plugin list --installed  # Shows your plugin
```

## Need Help? 🆘

- 💬 Join our [Discord community](https://discord.gg/flowyml)
- 📖 Read the [API Reference](../api/plugins.md)
- 🐛 Report issues on [GitHub](https://github.com/UnicoLab/FlowyML/issues)

# 🔄 Using External Frameworks

FlowyML's plugin system allows you to use components from **any ML framework** without modification. This guide shows practical examples.

## Overview

FlowyML provides a bridge system that lets you integrate external tools and libraries seamlessly. Whether you're using MLflow for experiment tracking, Airflow for orchestration, or custom in-house tools, FlowyML can wrap them to work with its unified API.

## Supported Integrations

| Category | Integrations Available |
|----------|----------------------|
| **Experiment Tracking** | MLflow, Weights & Biases, Neptune, TensorBoard |
| **Orchestration** | Kubernetes, Airflow, Kubeflow, Ray |
| **Artifact Storage** | S3, GCS, Azure Blob, MinIO |
| **Container Registries** | ECR, GCR, ACR, Docker Hub |
| **Feature Stores** | Feast |
| **Data Validation** | Great Expectations, Pandera |

## MLflow Integration

### Quick Start

```bash
# Install MLflow plugin
flowyml plugin install mlflow
```

```python
from flowyml.plugins import get_plugin

# Create tracker instance
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

for epoch in range(10):
    tracker.log_metrics({
        "train_loss": 0.5 - (epoch * 0.04),
        "val_accuracy": 0.7 + (epoch * 0.02),
    }, step=epoch)

tracker.log_model(model, "models/classifier", model_type="sklearn")
tracker.end_run()
```

## Cloud Storage Integration

### S3 Artifact Store

```python
from flowyml.plugins import get_plugin

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
```

### GCS Artifact Store

```python
from flowyml.plugins import get_plugin

store = get_plugin("gcs",
    bucket="my-ml-bucket",
    prefix="experiments/"
)

store.save(model, "models/latest.pkl")
```

### Azure Blob Store

```python
from flowyml.plugins import get_plugin

store = get_plugin("azure_blob",
    container="ml-artifacts",
    connection_string="${AZURE_CONNECTION_STRING}"
)
```

## Orchestration Integration

### Vertex AI Pipelines

```yaml
# flowyml.yaml
plugins:
  orchestrator:
    type: vertex_ai
    project: my-gcp-project
    region: us-central1
    service_account: ml-sa@project.iam.gserviceaccount.com
```

```python
from flowyml import Pipeline, step

@step(resources={"cpu": "4", "memory": "16Gi"})
def train_model():
    # Training code
    return model

pipeline = Pipeline("training_pipeline")
pipeline.add_step(train_model)
pipeline.run()  # Runs on Vertex AI
```

### SageMaker Pipelines

```yaml
# flowyml.yaml
plugins:
  orchestrator:
    type: sagemaker
    region: us-east-1
    role_arn: arn:aws:iam::123456789:role/SageMakerRole
```

### Kubernetes

```yaml
# flowyml.yaml
plugins:
  orchestrator:
    type: kubernetes
    namespace: ml-pipelines
    service_account: flowyml-runner
```

## Airflow Integration

FlowyML can generate Airflow DAGs from your pipelines:

```python
from flowyml import Pipeline, step
from flowyml.plugins import get_plugin

@step
def extract_data():
    return load_data_from_source()

@step
def transform_data(data):
    return preprocess(data)

@step
def train_model(data):
    return fit_model(data)

# Create pipeline
pipeline = Pipeline("etl_training")
pipeline.add_step(extract_data)
pipeline.add_step(transform_data)
pipeline.add_step(train_model)

# Export as Airflow DAG
airflow_orch = get_plugin("airflow", dag_folder="~/airflow/dags")
airflow_orch.export_pipeline(pipeline, "ml_training_dag")
```

## Creating Custom Integrations

You can wrap any external tool using FlowyML's plugin base classes:

```python
from flowyml.plugins.base import ExperimentTracker, PluginMetadata, PluginType

class MyCustomTracker(ExperimentTracker):
    """Custom experiment tracker integration."""

    METADATA = PluginMetadata(
        name="my_tracker",
        description="My custom tracking solution",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        packages=["my-tracking-lib>=1.0"],
    )

    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self._client = MyTrackingClient(api_key)

    def start_run(self, run_name: str, **kwargs) -> str:
        return self._client.create_run(run_name)

    def end_run(self, status: str = "FINISHED") -> None:
        self._client.finish_run(status)

    def log_params(self, params: dict) -> None:
        self._client.log_parameters(params)

    def log_metrics(self, metrics: dict, step: int = None) -> None:
        self._client.log_metrics(metrics, step=step)
```

### Publishing Your Integration

Register your plugin via entry points:

```toml
# pyproject.toml
[project.entry-points."flowyml.plugins"]
my_tracker = "my_package.plugins:MyCustomTracker"
```

When users install your package, FlowyML automatically discovers it:

```bash
pip install my-flowyml-plugin
flowyml plugin list --installed  # Shows your plugin
```

## Configuration Examples

### Multi-Cloud Setup

```yaml
# flowyml.yaml
stacks:
  gcp_production:
    plugins:
      artifact_store:
        type: gcs
        bucket: ml-artifacts-prod
      orchestrator:
        type: vertex_ai
        project: prod-project

  aws_staging:
    plugins:
      artifact_store:
        type: s3
        bucket: ml-artifacts-staging
      orchestrator:
        type: sagemaker
        region: us-west-2
```

```python
from flowyml.plugins import use_stack

# Use GCP for production
with use_stack("gcp_production"):
    pipeline.run()

# Use AWS for staging
with use_stack("aws_staging"):
    pipeline.run()
```

## Best Practices

1. **Pin Versions** - Specify tool versions in requirements
   ```
   mlflow>=2.0.0
   boto3>=1.28.0
   ```

2. **Use YAML Config** - Define stacks in `flowyml.yaml` for reproducibility

3. **Test Locally** - Verify components before cloud deployment

4. **Secure Credentials** - Use environment variables for secrets:
   ```yaml
   plugins:
     artifact_store:
       type: s3
       bucket: ${AWS_BUCKET}
   ```

## Next Steps

- [Plugin System Overview](./overview.md)
- [Creating Custom Plugins](./creating-plugins.md)
- [Stack Configuration Guide](./stack-configuration.md)

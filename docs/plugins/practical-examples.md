# 🎯 Plugin System: Practical Examples

This guide provides **copy-paste ready examples** for common plugin use cases.

## Example 1: Run on Kubernetes in 5 Minutes

```python
# install.sh
pip install flowyml zenml
zenml integration install kubernetes

# pipeline.py
from flowyml import Pipeline, step
from flowyml.stacks.plugins import load_component

# Load Kubernetes orchestrator from ZenML
load_component(
    "zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator",
    name="k8s"
)

@step(resources={"cpu": "4", "memory": "16Gi"})
def train_model():
    """Runs on Kubernetes!"""
    import time
    print("Training on K8s...")
    time.sleep(5)
    return {"accuracy": 0.95}

# Create pipeline
pipeline = Pipeline("k8s_example")
pipeline.add_step(train_model)

# Run on Kubernetes
result = pipeline.run(stack="kubernetes")
print(f"Result: {result}")
```

```yaml
# flowyml.yaml
stacks:
  kubernetes:
    orchestrator:
      plugin: k8s
      config:
        kubernetes_context: my-cluster
        kubernetes_namespace: ml-pipelines
```

**Run it:**
```bash
python pipeline.py
```

## Example 2: MLflow + S3 Production Stack

```python
# setup.sh
pip install flowyml zenml mlflow boto3
zenml integration install mlflow s3

# production_pipeline.py
from flowyml import Pipeline, step
from flowyml.stacks.plugins import load_component

# Load components
load_component(
    "zenml:zenml.integrations.mlflow.experiment_trackers.MLflowExperimentTracker",
    name="mlflow"
)
load_component(
    "zenml:zenml.integrations.s3.artifact_stores.S3ArtifactStore",
    name="s3"
)

@step
def prepare_data():
    import pandas as pd
    df = pd.DataFrame({"feature": [1, 2, 3], "label": [0, 1, 0]})
    return df

@step
def train_with_mlflow(data):
    import mlflow
    from sklearn.ensemble import RandomForestClassifier

    with mlflow.start_run():
        # Log parameters
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("max_depth", 5)

        # Train
        model = RandomForestClassifier(n_estimators=100, max_depth=5)
        X = data[["feature"]]
        y = data["label"]
        model.fit(X, y)

        # Log metrics
        accuracy = model.score(X,y)
        mlflow.log_metric("accuracy", accuracy)

        # Log model
        mlflow.sklearn.log_model(model, "model")

    return model

pipeline = Pipeline("production")
pipeline.add_step(prepare_data)
pipeline.add_step(train_with_mlflow)
```

```yaml
# flowyml.yaml
stacks:
  production:
    artifact_store:
      plugin: s3
      config:
        bucket: my-ml-artifacts
        region: us-west-2

# Set AWS credentials
# export AWS_ACCESS_KEY_ID=xxx
# export AWS_SECRET_ACCESS_KEY=xxx
```

## Example 3: Vertex AI on GCP

```python
# gcp_pipeline.py
from flowyml import Pipeline, step
from flowyml.stacks.plugins import load_component

# Load GCP components
load_component(
    "zenml:zenml.integrations.gcp.orchestrators.VertexOrchestrator",
    name="vertex"
)
load_component(
    "zenml:zenml.integrations.gcp.artifact_stores.GCPArtifactStore",
    name="gcs"
)

@step(resources={"cpu": "8", "memory": "32Gi", "accelerator_type": "NVIDIA_TESLA_T4", "accelerator_count": 1})
def train_on_vertex():
    """Runs on Vertex AI with GPU"""
    import tensorflow as tf

    # Use GPU if available
    print(f"GPUs Available: {len(tf.config.list_physical_devices('GPU'))}")

    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax')
    ])

    return model

pipeline = Pipeline("vertex_training")
pipeline.add_step(train_on_vertex)
result = pipeline.run(stack="gcp_production")
```

```yaml
# flowyml.yaml
stacks:
  gcp_production:
    orchestrator:
      plugin: vertex
      config:
        project: my-gcp-project
        location: us-central1
        service_account: ml-pipeline@my-project.iam.gserviceaccount.com
    artifact_store:
      plugin: gcs
      config:
        bucket: gs://my-ml-bucket
```

## Example 4: Hybrid Stack (Multiple Frameworks)

Combine components from different sources:

```python
# hybrid_pipeline.py
from flowyml import Pipeline, step
from flowyml.stacks import Stack
from flowyml.stacks.plugins import get_component_registry, load_component
from flowyml.storage.artifacts import LocalArtifactStore
from flowyml.storage.metadata import SQLiteMetadataStore

# Load ZenML Kubernetes orchestrator
load_component(
    "zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator",
    name="k8s"
)

# Get components
registry = get_component_registry()
k8s_orch = registry.get_orchestrator("k8s")

# Create hybrid stack
hybrid_stack = Stack(
    name="hybrid",
    orchestrator=k8s_orch(),  # From ZenML
    artifact_store=LocalArtifactStore(),  # From FlowyML
    metadata_store=SQLiteMetadataStore()  # From FlowyML
)

@step
def process():
    return {"status": "processed"}

pipeline = Pipeline("hybrid_example", stack=hybrid_stack)
pipeline.add_step(process)
result = pipeline.run()
```

## Example 5: Import Existing ZenML Stack

```bash
# Step 1: List your ZenML stacks
zenml stack list

# Step 2: Import to FlowyML
flowyml plugin import-zenml-stack production

# Step 3: Verify
cat flowyml.yaml

# Step 4: Run with imported stack
flowyml run my_pipeline.py --stack production
```

## Example 6: Custom Component from Local File

```python
# my_components.py
from flowyml.stacks.components import Orchestrator

class MyCustomOrchestrator(Orchestrator):
    def run_pipeline(self, pipeline, **kwargs):
        print(f"Running {pipeline.name} with custom orchestrator")
        # Your orchestration logic
        return pipeline.execute_locally()

# Load from file
from flowyml.stacks.plugins import load_component
load_component("/path/to/my_components.py:MyCustomOrchestrator")
```

## Example 7: Load from PyPI Package

```python
# If you published a flowyml plugin to PyPI

# Install
# pip install flowyml-my-plugin

# Use (auto-discovered via entry points!)
from flowyml.stacks.plugins import get_component_registry

registry = get_component_registry()
my_component = registry.get_orchestrator("my_custom_orch")
```

## Example 8: Multi-Cloud Setup

```yaml
# flowyml.yaml
stacks:
  aws_production:
    orchestrator:
      plugin: sagemaker
      config:
        role_arn: arn:aws:iam::123456789:role/SageMakerRole
    artifact_store:
      plugin: s3
      config:
        bucket: ml-artifacts-aws
        region: us-east-1

  gcp_production:
    orchestrator:
      plugin: vertex
      config:
        project: my-gcp-project
        location: us-central1
    artifact_store:
      plugin: gcs
      config:
        bucket: gs://ml-artifacts-gcp

  azure_production:
    orchestrator:
      plugin: azureml
      config:
        subscription_id: xxx
        resource_group: ml-resources
    artifact_store:
      plugin: azure_blob
      config:
        container: ml-artifacts
```

```python
# Switch between clouds easily
pipeline.run(stack="aws_production")  # Run on AWS
pipeline.run(stack="gcp_production")  # Run on GCP
pipeline.run(stack="azure_production")  # Run on Azure
```

## Common Patterns

### Pattern 1: Development → Staging → Production

```yaml
stacks:
  dev:
    orchestrator: local
    artifact_store:
      type: local
      path: .flowyml/artifacts

  staging:
    orchestrator:
      plugin: k8s
      config:
        kubernetes_namespace: ml-staging
    artifact_store:
      plugin: s3
      config:
        bucket: ml-staging-artifacts

  production:
    orchestrator:
      plugin: k8s
      config:
        kubernetes_namespace: ml-production
    artifact_store:
      plugin: s3
      config:
        bucket: ml-production-artifacts
```

### Pattern 2: Experiment Tracking + Model Registry

```python
from flowyml.stacks.plugins import load_component

# Load experiment tracker
load_component(
    "zenml:zenml.integrations.mlflow.experiment_trackers.MLflowExperimentTracker",
    name="mlflow_tracker"
)

# Load model registry
load_component(
    "zenml:zenml.integrations.mlflow.model_registries.MLflowModelRegistry",
    name="mlflow_registry"
)

@step
def train_and_register():
    import mlflow

    # Track experiment
    with mlflow.start_run() as run:
        model = train_model()
        mlflow.sklearn.log_model(model, "model")

        # Register model
        model_uri = f"runs:/{run.info.run_id}/model"
        mlflow.register_model(model_uri, "MyModel")

    return model
```

## Quick Reference

```bash
# Plugin Management
flowyml plugin list                    # List installed plugins
flowyml plugin search kubernetes       # Search for plugins
flowyml plugin install zenml-k8s       # Install a plugin

# Component Management
flowyml component list                 # List all components
flowyml component load SOURCE         # Load a component

# Stack Management
flowyml stack list                    # List stacks
flowyml stack show STACK_NAME         # Show stack details
flowyml plugin import-zenml-stack NAME # Import ZenML stack

# Running Pipelines
flowyml run pipeline.py --stack production
flowyml run pipeline.py --stack kubernetes --resources gpu_training
```

## Next Steps

- [Plugin System Overview](./overview.md)
- [External Frameworks Guide](./external-frameworks.md)
- [Creating Custom Plugins](./creating-plugins.md)

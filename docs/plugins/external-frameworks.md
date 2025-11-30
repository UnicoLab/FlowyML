# 🔄 Using External Frameworks (ZenML, Airflow, etc.)

FlowyML's plugin system allows you to use components from **any ML framework** without modification. This guide shows practical examples.

## Supported Frameworks

| Framework | Components Available | Installation |
|-----------|---------------------|--------------|
| **ZenML** | Orchestrators, Artifact Stores, Model Registries, Experiment Trackers | `pip install zenml` |
| **Airflow** | Operators, Sensors (coming soon) | `pip install apache-airflow` |
| **MLflow** | Tracking, Model Registry | `pip install mlflow` |
| **Custom** | Any Python class | Your package |

## ZenML Integration

### Quick Start with ZenML

**1. Install ZenML and integrations:**
```bash
pip install zenml
zenml integration install kubernetes mlflow s3
```

**2. Load ZenML components:**

Via CLI:
```bash
flowyml component load zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator --name k8s
```

Via Python:
```python
from flowyml.stacks.plugins import load_component

load_component(
    "zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator",
    name="k8s"
)
```

**3. Use in your pipeline:**
```python
from flowyml import Pipeline, step
from flowyml.stacks.plugins import get_component_registry

registry = get_component_registry()
k8s_orch = registry.get_orchestrator("k8s")

@step(resources={"cpu": "4", "memory": "16Gi"})
def train():
    # This runs on Kubernetes via ZenML!
    return train_model()

pipeline = Pipeline("k8s_pipeline")
pipeline.stack.orchestrator = k8s_orch()
result = pipeline.run()
```

### Example 1: Kubernetes Orchestration with ZenML

```python
from flowyml.stacks.plugins import load_component
from flowyml import Pipeline, step

# Load ZenML's Kubernetes orchestrator
load_component(
    "zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator",
    name="k8s"
)

@step(resources={"cpu": "8", "memory": "32Gi", "gpu": "1"})
def train_on_k8s():
    """This step runs on Kubernetes cluster"""
    model = train_large_model()
    return model

pipeline = Pipeline("production_training")
pipeline.add_step(train_on_k8s)

# Runs on Kubernetes!
pipeline.run(stack="kubernetes")
```

### Example 2: MLflow Experiment Tracking

```python
from flowyml.stacks.plugins import load_component

# Load MLflow tracker from ZenML
load_component(
    "zenml:zenml.integrations.mlflow.experiment_trackers.MLflowExperimentTracker",
    name="mlflow"
)

@step
def train_with_tracking():
    import mlflow

    with mlflow.start_run():
        # Log parameters
        mlflow.log_param("learning_rate", 0.001)
        mlflow.log_param("batch_size", 32)

        # Training
        model, metrics = train_model()

        # Log metrics
        mlflow.log_metric("accuracy", metrics["accuracy"])
        mlflow.log_metric("f1_score", metrics["f1"])

        # Log model
        mlflow.sklearn.log_model(model, "model")

    return model
```

### Example 3: Cloud Artifact Storage (S3, GCS, Azure)

```python
from flowyml.stacks.plugins import load_component

# Load S3 artifact store from ZenML
load_component(
    "zenml:zenml.integrations.s3.artifact_stores.S3ArtifactStore",
    name="s3_store"
)

# Or GCS
load_component(
    "zenml:zenml.integrations.gcp.artifact_stores.GCPArtifactStore",
    name="gcs_store"
)

# Or Azure
load_component(
    "zenml:zenml.integrations.azure.artifact_stores.AzureBlobArtifactStore",
    name="azure_store"
)
```

Configure in `flowyml.yaml`:
```yaml
stacks:
  production:
    orchestrator: k8s
    artifact_store:
      plugin: s3_store
      config:
        bucket: my-ml-artifacts
        region: us-west-2
```

### Example 4: Vertex AI on GCP

```python
from flowyml.stacks.plugins import load_component

# Load Vertex AI orchestrator
load_component(
    "zenml:zenml.integrations.gcp.orchestrators.VertexOrchestrator",
    name="vertex"
)

# Load GCS artifact store
load_component(
    "zenml:zenml.integrations.gcp.artifact_stores.GCPArtifactStore",
    name="gcs"
)
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
    artifact_store:
      plugin: gcs
      config:
        bucket: gs://my-ml-bucket
```

## Migrating Existing ZenML Stacks

If you already use ZenML, you can import your stacks directly:

### Step 1: List ZenML Stacks

```bash
zenml stack list
```

Output:
```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Name         ┃ Orchestrator ┃ Artifact Store ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ default      │ local        │ local         │
│ production   │ kubernetes   │ s3            │
│ staging      │ kubeflow     │ gcs           │
└──────────────┴──────────────┴──────────────┘
```

### Step 2: Import Stack to FlowyML

```bash
flowyml plugin import-zenml-stack production
```

This generates `flowyml.yaml`:
```yaml
# Auto-generated from ZenML stack 'production'
plugins:
  - name: kubernetes_orchestrator
    source: zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator
    component_type: orchestrator

  - name: s3_artifact_store
    source: zenml.integrations.s3.artifact_stores.S3ArtifactStore
    component_type: artifact_store

stacks:
  production:
    orchestrator: kubernetes_orchestrator
    artifact_store: s3_artifact_store
```

### Step 3: Use Imported Stack

```bash
flowyml run my_pipeline.py --stack production
```

## Available ZenML Integrations

### Orchestrators
- **Kubernetes** - `zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator`
- **Kubeflow** - `zenml.integrations.kubeflow.orchestrators.KubeflowOrchestrator`
- **Vertex AI** - `zenml.integrations.gcp.orchestrators.VertexOrchestrator`
- **SageMaker** - `zenml.integrations.aws.orchestrators.SagemakerOrchestrator`
- **Airflow** - `zenml.integrations.airflow.orchestrators.AirflowOrchestrator`
- **Azure ML** - `zenml.integrations.azure.orchestrators.AzureMLOrchestrator`

### Artifact Stores
- **S3** - `zenml.integrations.s3.artifact_stores.S3ArtifactStore`
- **GCS** - `zenml.integrations.gcp.artifact_stores.GCPArtifactStore`
- **Azure Blob** - `zenml.integrations.azure.artifact_stores.AzureBlobArtifactStore`
- **MinIO** - `zenml.integrations.minio.artifact_stores.MinIOArtifactStore`

### Experiment Trackers
- **MLflow** - `zenml.integrations.mlflow.experiment_trackers.MLflowExperimentTracker`
- **Weights & Biases** - `zenml.integrations.wandb.experiment_trackers.WandbExperimentTracker`
- **Neptune** - `zenml.integrations.neptune.experiment_trackers.NeptuneExperimentTracker`

### Model Registries
- **MLflow** - `zenml.integrations.mlflow.model_registries.MLflowModelRegistry`
- **Vertex AI** - `zenml.integrations.gcp.model_registries.VertexModelRegistry`

## Advanced: Custom Bridge Rules

For fine control over component adaptation:

```python
from flowyml.stacks.bridge import GenericBridge, AdaptationRule
from flowyml.stacks.components import ComponentType

# Define custom adaptation rules
rules = [
    AdaptationRule(
        source_type="zenml.orchestrators.custom.MyOrchestrator",
        target_type=ComponentType.ORCHESTRATOR,
        method_mapping={
            "run_pipeline": "execute",
            "get_orchestrator_run_id": "get_run_id"
        },
        attribute_mapping={
            "config": "settings"
        }
    )
]

# Register custom bridge
from flowyml.stacks.plugins import get_component_registry
registry = get_component_registry()
registry.register_bridge("custom", GenericBridge(rules=rules))

# Use custom bridge
load_component("custom:path.to.MyOrchestrator")
```

## Comparison: Pure ZenML vs FlowyML + ZenML

| Feature | Pure ZenML | FlowyML + ZenML Plugin |
|---------|-----------|------------------------|
| **UI** | Basic CLI | ✅ Modern Web UI |
| **Orchestrators** | Many | ✅ Same + FlowyML's |
| **Project Management** | Basic | ✅ Rich structure |
| **Metrics Dashboard** | External | ✅ Built-in |
| **Pipeline Syntax** | Complex | ✅ Simpler |
| **Ecosystem** | ZenML only | ✅ ZenML + Airflow + more |

## Troubleshooting

### Component Not Loading

```bash
# Check ZenML integration
zenml integration list

# Install if needed
zenml integration install kubernetes

# Verify import
python -c "from zenml.integrations.kubernetes.orchestrators import KubernetesOrchestrator"
```

### Missing Dependencies

```bash
# Install ZenML with integrations
pip install "zenml[kubernetes,mlflow,s3]"
```

## Best Practices

1. **Pin Versions** - Specify ZenML version in requirements
   ```
   zenml==0.50.0
   ```

2. **Use YAML Config** - Define stacks in `flowyml.yaml` for reproducibility

3. **Test Locally** - Verify components before cloud deployment

4. **Secure Credentials** - Use environment variables for secrets

## Next Steps

- [Plugin System Overview](./overview.md)
- [Creating Custom Plugins](./creating-plugins.md)
- [Stack Configuration Guide](../user-guide/configuration.md)

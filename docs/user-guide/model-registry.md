# Model Registry 🏛️

The **Model Registry** is a centralized repository for managing the lifecycle of your machine learning models. It allows you to version, tag, and promote models through different stages (Development, Staging, Production).

## Key Concepts 🗝️

- **Model Version**: A specific iteration of a model, including its artifacts, metrics, and metadata.
- **Stage**: The lifecycle state of a model version (`Development`, `Staging`, `Production`, `Archived`).
- **Promotion**: Moving a model version from one stage to another.

## Using the Registry 🛠️

### Registering a Model

You can register a model directly from your pipeline or script.

```python
from flowyml import ModelRegistry, ModelStage

registry = ModelRegistry()

# Register a trained model
version = registry.register(
    model=my_model,
    name="sentiment_classifier",
    version="v1.0.0",
    framework="pytorch",
    metrics={"accuracy": 0.95, "f1": 0.94},
    tags={"language": "en", "architecture": "bert"}
)

print(f"Registered model: {version.name} version {version.version}")
```

### Loading a Model 📥

You can load a model by name and version, or by stage.

```python
# Load specific version
model = registry.load("sentiment_classifier", version="v1.0.0")

# Load latest production model
prod_model = registry.load("sentiment_classifier", stage=ModelStage.PRODUCTION)
```

### Promoting a Model 🚀

Move a model through its lifecycle stages.

```python
# Promote to Staging
registry.promote("sentiment_classifier", "v1.0.0", ModelStage.STAGING)

# Promote to Production
registry.promote("sentiment_classifier", "v1.0.0", ModelStage.PRODUCTION)
```

### Comparing Versions 📊

Compare metrics and metadata across different versions.

```python
comparison = registry.compare_versions(
    "sentiment_classifier",
    ["v1.0.0", "v1.1.0"]
)

print(comparison)
```

## CLI Commands 💻

You can also manage models via the CLI:

```bash
# List all models
flowyml models list

# List versions of a model
flowyml models list sentiment_classifier

# Promote a model
flowyml models promote sentiment_classifier v1.0.0 --to production
```

## Integration with Pipelines 🔌

The Model Registry integrates seamlessly with flowyml pipelines. You can use the `Model` asset type to automatically register models produced by steps.

```python
from flowyml import step, Model

@step
def train():
    # ... training logic ...
    return Model(
        data=trained_model,
        name="my_model",
        register=True  # Automatically register in Model Registry
    )
```

## Registry Backends (Plugins) 🔁

The examples above use the **built-in SQL registry**, which needs no setup. For
team and production use, FlowyML ships registry **plugins** that are wired in as a
[stack component](../architecture/stacks.md) (`stack.model_registry`) — your code
stays identical while the backing store changes:

| Flavor | Backend | Extra |
|--------|---------|-------|
| `mlflow_registry` | MLflow Model Registry | `pip install mlflow` |
| `azureml_registry` | Azure ML workspace / registry | `pip install "flowyml[azure]"` |
| `vertex_model_registry` | Vertex AI Model Registry (GCP) | `pip install "flowyml[gcp]"` |
| `sagemaker_model_registry` | SageMaker Model Registry (AWS) | `pip install "flowyml[aws]"` |

Select one per stack in `flowyml.yaml`:

```yaml
stacks:
  prod:
    orchestrator: { type: azure_ml, ... }
    artifact_store: { type: azure_blob, ... }
    model_registry:
      type: azureml_registry
      subscription_id: ${AZURE_SUBSCRIPTION_ID}
      resource_group: ml-rg
      workspace_name: ml-ws
```

Once attached, `register → promote → deploy` all target that backend
automatically. Platform teams can even **govern** which registries a team may use
via [Enterprise Stacks](../guides/enterprise-stacks.md) policy allow-lists.

## From Registry to Endpoint 🚀

A registered model is the input to serving. Reference it by **name + stage** and
FlowyML transparently fetches, packages, and deploys it:

```python
from flowyml.deployment import DeploymentSpec, ModelRef, DeploymentService

DeploymentService().deploy(DeploymentSpec(
    name="sentiment-api",
    model=ModelRef("sentiment_classifier", stage="production"),
    runtime="fastapi",
    target="kubernetes",
))
```

Use `promote_if_better(...)` to gate promotion+deploy on a champion/challenger
comparison. See the **[Model Serving & Deployment guide](../guides/model-serving-deployment.md)**
and the **[end-to-end tutorial](../tutorials/production-serving-openshift.md)**.

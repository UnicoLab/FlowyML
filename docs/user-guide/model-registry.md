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
from uniflow import ModelRegistry, ModelStage

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
uniflow models list

# List versions of a model
uniflow models list sentiment_classifier

# Promote a model
uniflow models promote sentiment_classifier v1.0.0 --to production
```

## Integration with Pipelines 🔌

The Model Registry integrates seamlessly with UniFlow pipelines. You can use the `Model` asset type to automatically register models produced by steps.

```python
from uniflow import step, Model

@step
def train():
    # ... training logic ...
    return Model(
        data=trained_model,
        name="my_model",
        register=True  # Automatically register in Model Registry
    )
```

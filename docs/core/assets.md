# Assets & Artifacts 💎

In flowyml, data lineage and artifact tracking are first-class features. Every piece of data flowing through your pipeline is tracked, versioned, and queryable.

> [!NOTE]
> **What you'll learn**: How to work with typed assets (Datasets, Models, Metrics) and track complete data lineage
>
> **Key insight**: **Reproducibility requires lineage**. flowyml tracks not just what models you trained, but what data created them, which code version, and all hyperparameters.

## Why Assets Matter

**Without structured assets**, teams face:
- **"Which data trained this model?"** — Unknown, guesswork
- **"Can we reproduce this result?"** — Maybe, if you kept notes
- **"Where did this artifact come from?"** — Lost in the pipeline
- **"What changed between runs?"** — Manual diffing, error-prone

**With flowyml assets**, you get:
- **Automatic lineage tracking**: Every asset knows its parents
- **Version control for data**: Not just code, but datasets and models
- **Audit trails**: Full provenance from raw data to predictions
- **Reproducibility**: Re-create any result on demand

> [!IMPORTANT]
> **For regulated industries** (finance, healthcare, legal): Asset lineage isn't optional. flowyml provides audit-ready traceability out of the box.

## The Asset Hierarchy 🏛️

flowyml provides specialized classes for different ML artifact types:

- **Asset**: The base class for all versioned objects.
- **Dataset**: Represents data (DataFrames, file paths, tensors).
- **Model**: Represents trained ML models.
- **Metrics**: Represents evaluation results (accuracy, loss).
- **FeatureSet**: Represents engineered features.

## Creating Assets 🔨

You can create assets explicitly using the `.create()` factory method. This automatically handles versioning, metadata generation, and lineage tracking.

> [!IMPORTANT]
> **Assets interface data field** is not about passing the data to the asset, but rather about the asset's interface on which data to register. This can be a model (Keras) or dataset (Pandas) etc ... Which data take into account when creating the asset.


### Datasets

FlowyML automatically extracts statistics and metadata from various data formats!

```python
from flowyml import Dataset
import pandas as pd

df = pd.DataFrame(...)

# 🎯 SIMPLIFIED: Just pass the data - stats are auto-extracted!
dataset = Dataset.create(
    data=df,
    name="training_data",
    source="s3://bucket/data.csv",  # Optional metadata
)

# Access auto-extracted properties
print(f"Samples: {dataset.num_samples}")
print(f"Features: {dataset.num_features}")
print(f"Columns: {dataset.feature_columns}")
print(f"Stats: {dataset.column_stats}")  # Per-column mean, std, min, max, etc.
```

**Convenience methods for common formats:**

```python
# Load from CSV with automatic stats extraction
dataset = Dataset.from_csv("data.csv", name="my_data")

# Load from Parquet
dataset = Dataset.from_parquet("data.parquet", name="my_data")
```

**Supported data types:**
- Pandas DataFrames
- NumPy arrays
- Python dictionaries
- TensorFlow `tf.data.Dataset`
- Lists of dictionaries

### Models

FlowyML automatically extracts model metadata from all major ML frameworks!

```python
from flowyml import Model

# 🎯 SIMPLIFIED: Just pass the model - everything is auto-extracted!
model_asset = Model.create(
    data=trained_model,
    name="resnet50_finetuned",
)

# Access auto-extracted properties
print(f"Framework: {model_asset.framework}")  # keras, pytorch, sklearn, etc.
print(f"Parameters: {model_asset.parameters}")
print(f"Layers: {model_asset.num_layers}")
print(f"Optimizer: {model_asset.optimizer}")  # For Keras
```

**Convenience methods for specific frameworks:**

```python
# Keras with training history
from flowyml.integrations.keras import FlowymlKerasCallback

callback = FlowymlKerasCallback(experiment_name="demo")
model.fit(X, y, callbacks=[callback])

model_asset = Model.from_keras(
    model,
    name="my_model",
    callback=callback,  # Auto-extracts training_history!
)

# PyTorch
model_asset = Model.from_pytorch(model, name="my_model")

# Scikit-learn
model_asset = Model.from_sklearn(model, name="my_model")
```

**Supported frameworks:**
- Keras/TensorFlow (full extraction: layers, optimizer, loss, metrics)
- PyTorch (parameters, layers, device, dtype)
- Scikit-learn (hyperparameters, feature importance, is_fitted)
- XGBoost/LightGBM/CatBoost
- Hugging Face Transformers

### Metrics

```python
from flowyml import Metrics

# Create a metrics object
metrics = Metrics.create(
    accuracy=0.95,
    f1_score=0.92,
    loss=0.15
)
```

## Lineage Tracking 🔗

flowyml automatically tracks the lineage of every asset.

- **Parents**: The assets that were used to create this asset.
- **Children**: The assets that were created using this asset.
- **Producer**: The pipeline step that generated this asset.

When you pass an asset from one step to another, flowyml records this relationship.

```python
@step
def preprocess(raw_data):
    # ...
    return clean_data  # clean_data's parent is raw_data

@step
def train(clean_data):
    # ...
    return model      # model's parent is clean_data
```

!!! success "Visualize It"
    You can visualize this lineage graph in the [flowyml UI](ui.md).

## Storage 💾

Assets are stored in the **Artifact Store**. By default, this is the `.flowyml/artifacts` directory in your project.

flowyml supports pluggable storage backends (S3, GCS, Azure) via `fsspec`. Configuration is handled in `flowyml.yaml`.

## Automatic Materialization 📦

When running a pipeline with a Stack that has an Artifact Store configured, flowyml automatically materializes step outputs.

The artifacts are stored in a structured path:
`{project_name}/{date}/{run_id}/data/{step_name}/{artifact_name}`

This ensures that every run is reproducible and all intermediate data is persisted. flowyml uses **Materializers** to handle serialization for different data types (Pandas, NumPy, Keras, PyTorch, etc.).

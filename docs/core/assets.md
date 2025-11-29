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

### Datasets

```python
from flowyml import Dataset
import pandas as pd

df = pd.DataFrame(...)

# Create a versioned dataset
dataset = Dataset.create(
    data=df,
    name="training_data",
    properties={
        "source": "s3://bucket/data.csv",
        "rows": len(df)
    }
)
```

### Models

```python
from flowyml import Model

# Create a versioned model
model_asset = Model.create(
    data=trained_model_object,
    name="resnet50_finetuned",
    framework="pytorch",
    parameters={"epochs": 10, "lr": 0.001}
)
```

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

# Artifact Upload Control

FlowyML provides fine-grained control over which artifacts are uploaded to remote storage. By default, **artifacts are NOT uploaded** to conserve bandwidth and storage. You can opt-in to upload specific artifacts.

## The `upload` Parameter

All FlowyML assets (`Dataset`, `Model`, `Metrics`, etc.) support an `upload` parameter:

```python
from flowyml import Dataset, Model, Metrics

# Default: upload=False - artifact is NOT uploaded
dataset = Dataset.create(
    data=my_data,
    name="training_data",
)

# Opt-in: upload=True - artifact WILL be uploaded
model = Model.create(
    data=trained_model,
    name="production_model",
    upload=True,  # <-- This model will be uploaded to remote storage
)
```

## When to Enable Upload

Consider enabling upload for:

- **Production models** you want to version and deploy
- **Important metrics** for experiment tracking
- **Datasets** that need to be shared across teams

Consider keeping upload disabled for:

- **Intermediate data** that won't be reused
- **Large datasets** during development
- **Debug artifacts** during troubleshooting

## Example: Selective Upload

```python
from flowyml import Pipeline, step, Dataset, Model, Metrics

@step
def load_data(data_path: str) -> tuple[Dataset, Dataset]:
    # Training/val data - don't upload during development
    train_data = Dataset.create(data=train_df, name="train", upload=False)
    val_data = Dataset.create(data=val_df, name="val", upload=False)
    return train_data, val_data

@step
def train_model(train_data: Dataset) -> Model:
    model = train_my_model(train_data)
    # Upload the final model for production use
    return Model.create(data=model, name="trained_model", upload=True)

@step
def evaluate(model: Model, val_data: Dataset) -> Metrics:
    metrics = evaluate_model(model, val_data)
    # Upload metrics for tracking
    return Metrics.create(data=metrics, name="evaluation", upload=True)
```

## Global Configuration

You can also control artifact upload behavior via environment variables:

```bash
# Enable all artifact uploads (overrides individual settings)
export FLOWYML_UPLOAD_ALL_ARTIFACTS=true

# Disable all artifact uploads (overrides individual settings)
export FLOWYML_UPLOAD_ALL_ARTIFACTS=false
```

## Remote Logging Mode

When using remote logging mode (`FLOWYML_EXECUTION_MODE=remote`):

1. Run **metadata** (status, duration, parameters) is always logged to the server
2. Artifact **files** are only uploaded if `upload=True` on the asset
3. This allows you to track runs without uploading large files

```python
import os

# Enable remote logging
os.environ["FLOWYML_EXECUTION_MODE"] = "remote"
os.environ["FLOWYML_REMOTE_SERVER_URL"] = "http://localhost:8080/api"

from flowyml.utils.config import reset_config
reset_config()  # Apply env vars

# Now artifacts with upload=True will be uploaded to the server
pipeline = create_pipeline()
result = pipeline.run()
```

## Summary

| Setting | Artifact Uploaded? |
|---------|-------------------|
| `upload=False` (default) | ❌ No |
| `upload=True` | ✅ Yes |
| Non-Asset return value | ❌ No |
| `FLOWYML_UPLOAD_ALL_ARTIFACTS=true` | ✅ Yes (all) |

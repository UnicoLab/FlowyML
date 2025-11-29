# Weights & Biases Integration 🐝

Visualize your training runs and track artifacts with W&B.

> [!NOTE]
> **What you'll learn**: How to integrate W&B for rich experiment visualization
>
> **Key insight**: Beautiful dashboards for your flowyml pipelines.

## Why Weights & Biases?

- **Visualization**: Interactive charts for loss, accuracy, and system metrics.
- **Collaboration**: Share results with your team instantly.
- **Artifacts**: Track dataset and model versioning.

## 🐝 Configuration

Enable W&B tracking for your pipeline run.

```python
from flowyml.integrations.wandb import WandBTracker

pipeline.run(
    tracker=WandBTracker(
        project="flowyml-demo",
        entity="my-team"
    )
)
```

## 📊 Logging Metrics

flowyml automatically captures step inputs/outputs, but you can add custom logs.

```python
import wandb
from flowyml import step

@step
def train(data):
    # Log custom metrics
    wandb.log({"loss": 0.1, "accuracy": 0.9})

    # Log images
    wandb.log({"chart": wandb.Image("plot.png")})

    return model
```

## 📦 W&B Artifacts

Use W&B Artifacts to track data lineage.

```python
@step
def load_data():
    run = wandb.init()
    artifact = run.use_artifact('mnist:v1')
    dir = artifact.download()
    return load_dataset(dir)
```

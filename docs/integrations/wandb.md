---
title: Weights & Biases Integration — FlowyML
description: "Log experiments, visualize training runs, and collaborate with your team using W&B integrated into FlowyML."
---

<div class="hero-section" markdown>

## 📉 Weights & Biases Integration

Log experiments, visualize training runs, and collaborate with your team using W&B integrated into FlowyML.

<span class="feature-badge">📊 Run Logging</span>
<span class="feature-badge">🎨 Visualizations</span>
<span class="feature-badge">👥 Collaboration</span>

</div>

# 🐝 Weights & Biases Integration

!!! info "What you'll learn"
    How to integrate W&B for rich experiment visualization — interactive dashboards for your FlowyML pipelines.

Visualize training runs, track artifacts, and collaborate with your team using Weights & Biases.

---

## Why Weights & Biases?

| Feature | Benefit |
|---|---|
| **Visualization** | Interactive charts for loss, accuracy, and system metrics |
| **Collaboration** | Share results with your team instantly |
| **Artifacts** | Track dataset and model versioning |
| **Sweeps** | Hyperparameter optimization with built-in sweep support |

---

## 🐝 Setup

```bash
pip install wandb
wandb login  # Authenticate with your API key
```

---

## Configuration

Enable W&B tracking for your pipeline run:

```python
from flowyml.integrations.wandb import WandBTracker

pipeline.run(
    tracker=WandBTracker(
        project="flowyml-demo",
        entity="my-team",
        tags=["training", "v2"],
    )
)
```

### WandBTracker Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `project` | `str` | *required* | W&B project name |
| `entity` | `str` | `None` | Team or user entity |
| `tags` | `list[str]` | `[]` | Run tags for filtering |
| `group` | `str` | `None` | Group related runs |
| `name` | `str` | `None` | Custom run name |

---

## 📊 Logging Custom Metrics

FlowyML auto-captures step inputs/outputs, but you can add custom logs:

```python
import wandb
from flowyml import step

@step
def train(data):
    for epoch in range(10):
        loss = train_epoch(data)
        wandb.log({"epoch": epoch, "loss": loss, "accuracy": 1 - loss})

    # Log rich media
    wandb.log({"confusion_matrix": wandb.plot.confusion_matrix(...)})
    wandb.log({"roc": wandb.plot.roc_curve(...)})

    return model
```

---

## 📦 W&B Artifacts

Use W&B Artifacts for dataset and model versioning:

```python
@step
def load_data():
    run = wandb.init()
    artifact = run.use_artifact("mnist:v1")
    data_dir = artifact.download()
    return load_dataset(data_dir)

@step
def save_model(model):
    artifact = wandb.Artifact("my-model", type="model")
    artifact.add_file("model.pt")
    wandb.log_artifact(artifact)
```

---

## Best Practices

!!! tip "Tag your runs"
    Use tags like `["training", "v2", "gpu"]` to filter runs in the W&B dashboard.

!!! tip "Use groups for experiments"
    Group related runs with `group="hyperparameter_search"` to compare them in a single view.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 📊 MLflow Integration
Track experiments and manage model lifecycles with the industry-standard MLflow platform.

[Explore →](mlflow.md)

</div>

<div class="header-card" markdown>

### 📈 Evaluations
Evaluate your models with built-in metrics, custom scorers, and comparison tools.

[Learn more →](../evaluations.md)

</div>

<div class="header-card" markdown>

### 🔌 Plugin System
Extend FlowyML with custom plugins for logging, tracking, and notifications.

[View Guide →](../plugins/overview.md)

</div>

</div>

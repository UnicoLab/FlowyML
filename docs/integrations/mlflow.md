---
title: MLflow Integration — FlowyML
description: "Track experiments, log metrics, and manage models with MLflow's ecosystem integrated directly into FlowyML pipelines."
---

<div class="hero-section" markdown>

## 📊 MLflow Integration

Track experiments, log metrics, and manage models with MLflow's ecosystem integrated directly into FlowyML pipelines.

<span class="feature-badge">📈 Experiment Tracking</span>
<span class="feature-badge">🏷️ Model Registry</span>
<span class="feature-badge">📊 Metric Logging</span>

</div>

# 🧪 MLflow Integration

!!! info "What you'll learn"
    How to auto-log metrics and models to MLflow — FlowyML + MLflow = automated experiment tracking with the industry-standard platform.

Track experiments, manage model versions, and deploy models using MLflow's open-source ecosystem.

---

## Why MLflow?

| Feature | Benefit |
|---|---|
| **Experiment Tracking** | Log parameters, metrics, and artifacts |
| **Model Registry** | Version and manage model lifecycles |
| **Universal** | Works with any ML library |
| **Open Source** | No vendor lock-in |

---

## 🧪 Setup

```bash
pip install mlflow
mlflow server --host 127.0.0.1 --port 5000  # Start tracking server
```

---

## Auto-Logging

Enable MLflow tracking for your pipeline:

```python
from flowyml.integrations.mlflow import MLflowTracker

pipeline.run(
    tracker=MLflowTracker(
        tracking_uri="http://localhost:5000",
        experiment_name="my_experiment",
    )
)
```

### MLflowTracker Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `tracking_uri` | `str` | *required* | MLflow tracking server URL |
| `experiment_name` | `str` | `"default"` | Experiment name |
| `run_name` | `str` | `None` | Custom run name |
| `auto_log` | `bool` | `True` | Auto-log step params/metrics |

---

## 📝 Custom Logging in Steps

Log custom metrics, parameters, and artifacts:

```python
import mlflow
from flowyml import step

@step
def train_model(data):
    # Log parameters
    mlflow.log_param("lr", 0.01)
    mlflow.log_param("optimizer", "adam")

    model = train(data, lr=0.01)

    # Log metrics
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_metric("f1_score", 0.93)

    # Log the model artifact
    mlflow.sklearn.log_model(model, "model")

    return model
```

---

## 📦 Model Registry

Register and promote models through lifecycle stages:

```python
@step
def register_best_model(model, metrics):
    # Log and register in one step
    mlflow.sklearn.log_model(model, "model", registered_model_name="ProductionModel")

    # Promote to staging
    client = mlflow.tracking.MlflowClient()
    client.transition_model_version_stage(
        name="ProductionModel",
        version="1",
        stage="Staging",
    )
```

---

## Best Practices

!!! tip "Use autolog for quick wins"
    `mlflow.autolog()` automatically captures sklearn, XGBoost, LightGBM, and PyTorch metrics — zero code changes needed.

!!! tip "Remote tracking server"
    In production, point `tracking_uri` to a shared MLflow server so your whole team can see experiment results.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 📉 Weights & Biases
Visualize training runs with interactive dashboards and team collaboration.

[Explore →](wandb.md)

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

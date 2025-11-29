# MLflow Integration 🧪

Track experiments and manage models with the industry-standard open source platform.

> [!NOTE]
> **What you'll learn**: How to auto-log metrics and models to MLflow
>
> **Key insight**: flowyml + MLflow = Automated Experiment Tracking.

## Why MLflow?

- **Experiment Tracking**: Log parameters, metrics, and artifacts.
- **Model Registry**: Version and manage model lifecycles.
- **Universal**: Works with almost any ML library.

## 🧪 Auto-Logging

flowyml can automatically configure MLflow tracking for your pipeline.

```python
from flowyml.integrations.mlflow import MLflowTracker

# Enable MLflow tracking
pipeline.run(
    tracker=MLflowTracker(
        tracking_uri="http://localhost:5000",
        experiment_name="my_experiment"
    )
)
```

## 📝 Logging in Steps

You can also log custom metrics inside your steps.

```python
import mlflow
from flowyml import step

@step
def train_model(data):
    mlflow.log_param("lr", 0.01)

    # ... training ...

    mlflow.log_metric("accuracy", 0.95)
    mlflow.sklearn.log_model(model, "model")

    return model
```

## 📦 Model Registry

Register models automatically after successful training.

```python
@step
def register_model(model):
    mlflow.register_model(
        "runs:/<run_id>/model",
        "ProductionModel"
    )
```

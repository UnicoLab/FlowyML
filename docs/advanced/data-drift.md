# Data Drift Detection 📉

flowyml ensures your models don't rot in production by detecting when live data diverges from training data.

> [!NOTE]
> **What you'll learn**: How to catch "silent failures" where models degrade because the world changed
>
> **Key insight**: A model is only as good as the data it sees. If data changes, predictions fail.

## Why Drift Detection Matters

**Without drift detection**:
- **Silent degradation**: Model accuracy drops, but no errors are thrown
- **Reactive debugging**: Users complain about bad predictions weeks later
- **Blind retraining**: Retraining on schedule regardless of need

**With flowyml drift detection**:
- **Proactive alerts**: Know immediately when data distribution shifts
- **Targeted retraining**: Retrain only when necessary
- **Root cause analysis**: See exactly which features drifted (e.g., "Age distribution shifted older")

## 📉 Concept

Data drift occurs when the statistical properties of the target variable or input features change over time. flowyml uses the **Population Stability Index (PSI)** to quantify this shift.

## 📉 Concept

Data drift occurs when the statistical properties of the target variable or input features change over time. flowyml uses the **Population Stability Index (PSI)** to quantify this shift.

## 🕵️ Detecting Drift

Use the `detect_drift` function to compare two datasets.

```python
from flowyml.monitoring.data import detect_drift
import numpy as np

# Reference data (e.g., training set)
train_data = np.random.normal(0, 1, 1000)

# Current data (e.g., production traffic)
prod_data = np.random.normal(0.5, 1, 1000)  # Shifted mean

# Check for drift
result = detect_drift(
    reference_data=train_data,
    current_data=prod_data,
    threshold=0.1  # PSI threshold (default: 0.1)
)

if result['drift_detected']:
    print(f"⚠️ Drift detected! PSI: {result['psi']:.4f}")
    print(f"Reference Mean: {result['reference_stats']['mean']:.2f}")
    print(f"Current Mean: {result['current_stats']['mean']:.2f}")
else:
    print("✅ Data is stable.")
```

## 📊 Computing Statistics

You can also compute basic statistics for any dataset using `compute_stats`.

```python
from flowyml.monitoring.data import compute_stats

stats = compute_stats(prod_data)
print(stats)
# Output: {'count': 1000.0, 'mean': 0.48, 'std': 1.01, ...}
```

## Real-World Pattern: Automated Quality Gate

Stop a pipeline if drift is detected, preventing bad models from being deployed or bad predictions from being served.

```python
from flowyml import step, get_notifier, If

@step(outputs=["drift_result"])
def check_drift(new_batch):
    reference = load_reference_data()
    result = detect_drift(reference, new_batch)
    return result

@step
def alert_team(result):
    get_notifier().send_slack(f"🚨 Drift detected! PSI: {result['psi']}")

@step
def process_data(data):
    # Continue processing
    pass

# Build pipeline with a quality gate
pipeline.add_step(check_drift)
pipeline.add_control_flow(
    If(condition=lambda ctx: ctx["drift_result"]["drift_detected"])
    .then(alert_team)
    .else_(process_data)
)
```

> [!TIP]
> **Thresholds**: A PSI < 0.1 is usually safe. PSI > 0.2 indicates significant drift requiring investigation.

# Data Drift Detection 📉

UniFlow provides built-in tools to detect data drift between training and inference datasets, ensuring your models remain reliable over time.

## 📉 Concept

Data drift occurs when the statistical properties of the target variable or input features change over time. UniFlow uses the **Population Stability Index (PSI)** to quantify this shift.

## 🕵️ Detecting Drift

Use the `detect_drift` function to compare two datasets.

```python
from uniflow.monitoring.data import detect_drift
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
from uniflow.monitoring.data import compute_stats

stats = compute_stats(prod_data)
print(stats)
# Output: {'count': 1000.0, 'mean': 0.48, 'std': 1.01, ...}
```

## 🔔 Automated Monitoring

Combine drift detection with notifications to get alerted automatically.

```python
from uniflow import step, get_notifier

@step
def validate_data(new_batch):
    reference = load_reference_data()
    result = detect_drift(reference, new_batch)

    if result['drift_detected']:
        get_notifier().on_drift_detected("input_features", result['psi'])

    return new_batch
```

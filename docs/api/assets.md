---
title: Assets API — FlowyML
description: "Full API reference for FlowyML Assets: Model, Dataset, and Metrics with auto-extraction, lineage tracking, and framework adapters."
---

<div class="hero-section" markdown>

## 📦 Assets API

First-class ML artifacts with automatic metadata extraction, lineage tracking, and type-based routing.

<span class="feature-badge">🤖 Model</span>
<span class="feature-badge">📊 Dataset</span>
<span class="feature-badge">📈 Metrics</span>

</div>

## Overview

Assets are FlowyML's typed wrappers around raw ML objects. When a step returns an `Asset`, FlowyML automatically extracts metadata, records lineage, and routes the artifact to the configured store.

| Asset | Purpose | Factory Methods |
|-------|---------|-----------------|
| `Model` | Wraps trained models with framework-specific metadata | `Model.create()`, `Model.from_keras()`, `Model.from_pytorch()`, `Model.from_sklearn()` |
| `Dataset` | Wraps data with statistics and schema info | `Dataset.create()`, `Dataset.from_csv()`, `Dataset.from_parquet()` |
| `Metrics` | Wraps evaluation results and scores | `Metrics.create()`, `Metrics.from_dict()` |

## `Model` Constructor

```python
from flowyml import Model

model = Model.create(data=keras_model, name="my_model")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `Any` | **required** | The raw model object (Keras, PyTorch, sklearn, etc.). |
| `name` | `str` | **required** | Unique artifact name. Used in lineage and the artifact store. |
| `version` | `str | None` | `None` | Explicit version. Auto-incremented if omitted. |
| `metadata` | `dict | None` | `None` | Additional custom metadata to attach. |
| `tags` | `list[str]` | `[]` | Tags for filtering in the UI and artifact store. |

### Framework Convenience Methods

```python linenums="1"
# Keras — includes callback for live metric logging
model = Model.from_keras(keras_model, name="classifier", callback=flowyml_callback)

# PyTorch — auto-extracts layers, device, dtype
model = Model.from_pytorch(pytorch_model, name="detector")

# Scikit-learn — auto-extracts hyperparameters, feature importance
model = Model.from_sklearn(sklearn_model, name="regressor")
```

### Auto-Extracted Model Properties

| Property | Description |
|----------|-------------|
| `framework` | Detected framework (`keras`, `pytorch`, `sklearn`, `xgboost`, etc.) |
| `parameters` | Total parameter count |
| `num_layers` | Number of layers |
| `optimizer` | Optimizer name (Keras) |
| `hyperparameters` | Full hyperparameter dict (sklearn, XGBoost, LightGBM) |

## `Dataset` Constructor

```python
from flowyml import Dataset

ds = Dataset.create(data=df, name="training_data")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `Any` | **required** | The raw data (DataFrame, ndarray, dict, list of dicts). |
| `name` | `str` | **required** | Unique artifact name. |
| `version` | `str | None` | `None` | Explicit version. Auto-incremented if omitted. |
| `metadata` | `dict | None` | `None` | Additional custom metadata. |

### Auto-Extracted Dataset Properties

| Property | Description |
|----------|-------------|
| `num_samples` | Number of rows / samples |
| `num_features` | Number of columns / features |
| `feature_columns` | Column names |
| `column_stats` | Per-column statistics (mean, std, min, max, nulls) |

## `Metrics` Constructor

```python
from flowyml import Metrics

metrics = Metrics.create(
    data={"accuracy": 0.95, "f1": 0.93},
    name="eval_results",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `dict` | **required** | Key-value pairs of metric names and scores. |
| `name` | `str` | **required** | Unique artifact name. |
| `version` | `str | None` | `None` | Explicit version. |
| `metadata` | `dict | None` | `None` | Additional custom metadata (e.g., dataset used, split info). |

## Supported Frameworks (Model)

| Framework | Detection | Auto-Extraction Level |
|-----------|-----------|----------------------|
| Keras/TensorFlow | ✅ | Full (layers, optimizer, loss, metrics) |
| PyTorch | ✅ | Full (layers, device, dtype, params) |
| Scikit-learn | ✅ | Full (hyperparams, feature importance) |
| XGBoost | ✅ | Full (trees, hyperparams) |
| LightGBM | ✅ | Full (trees, hyperparams) |
| CatBoost | ✅ | Good |
| Hugging Face | ✅ | Good (config, hidden_size) |
| Custom | ✅ | Basic (class name, has_fit/predict) |

## Supported Data Types (Dataset)

| Type | Auto-Extraction |
|------|-----------------|
| Pandas DataFrame | Full (columns, stats, dtypes) |
| NumPy array | Full (shape, dtype, stats) |
| Python dict | Full (keys as columns, stats) |
| TensorFlow Dataset | Good (element_spec, cardinality) |
| List of dicts | Full (columns from keys, stats) |

!!! tip "Lineage Tracking"
    Every asset automatically records which step produced it, which pipeline run it belongs to, and what upstream assets it depends on. View the full lineage graph in the FlowyML UI.

## Autodoc

### Class `Asset`

::: flowyml.assets.base.Asset
    options:
        show_root_heading: false

### Class `Dataset`

::: flowyml.assets.dataset.Dataset
    options:
        show_root_heading: false

### Class `Model`

::: flowyml.assets.model.Model
    options:
        show_root_heading: false

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🎢 Pipeline API
Orchestrate steps that produce and consume assets.

[View Pipeline API →](pipeline.md)

</div>

<div class="header-card" markdown>

### 👣 Step API
Define the steps that create and transform assets.

[View Step API →](step.md)

</div>

<div class="header-card" markdown>

### 🔌 Plugins API
Configure artifact stores to control where assets are persisted.

[View Plugins API →](plugins.md)

</div>

</div>

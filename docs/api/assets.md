# Assets API 📦

First-class citizens for data and models with automatic metadata extraction.

## Quick Start

### Dataset - Auto-Extracted Statistics

```python
from flowyml import Dataset
import pandas as pd

df = pd.DataFrame(...)

# Auto-extracts: samples, features, columns, column_stats
ds = Dataset.create(data=df, name="my_data")

# Access auto-extracted properties
print(ds.num_samples)      # Number of rows
print(ds.num_features)     # Number of columns
print(ds.feature_columns)  # Column names
print(ds.column_stats)     # Per-column statistics

# Convenience methods
ds = Dataset.from_csv("data.csv", name="my_data")
ds = Dataset.from_parquet("data.parquet", name="my_data")
```

### Model - Auto-Extracted Metadata

```python
from flowyml import Model

# Auto-extracts: framework, parameters, layers, optimizer, etc.
model = Model.create(data=keras_model, name="my_model")

# Access auto-extracted properties
print(model.framework)      # 'keras', 'pytorch', 'sklearn'
print(model.parameters)     # Total parameter count
print(model.num_layers)     # Number of layers
print(model.optimizer)      # Optimizer name (Keras)
print(model.hyperparameters)  # Hyperparameters (sklearn)

# Convenience methods
model = Model.from_keras(keras_model, name="my_model", callback=flowyml_callback)
model = Model.from_pytorch(pytorch_model, name="my_model")
model = Model.from_sklearn(sklearn_model, name="my_model")
```

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

## Class `Asset`

::: flowyml.assets.base.Asset
    options:
        show_root_heading: false

## Class `Dataset`

::: flowyml.assets.dataset.Dataset
    options:
        show_root_heading: false

## Class `Model`

::: flowyml.assets.model.Model
    options:
        show_root_heading: false

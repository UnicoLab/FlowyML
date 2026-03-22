# 📦 Materializers

!!! info "What you'll learn"
    How to teach FlowyML to serialize and deserialize your custom objects. If you can't save it, you can't cache it, version it, or inspect it in the UI.

Materializers control **how FlowyML persists and loads artifacts**. Built-in materializers handle common types automatically; custom materializers let you support any Python object.

---

## Why Custom Serialization Matters 🤔

| Without Materializers | With Materializers |
|---|---|
| Relying on `pickle` for everything (brittle, insecure) | Optimized format per type |
| Saving a model as bytes loses its metadata | Save with hyperparameters and metadata |
| The UI can't show a preview of custom objects | Rich visualization in the dashboard |
| Non-portable: only Python can read pickle | Standard formats (Parquet, ONNX, CSV) |

---

## Built-in Materializers 📦

FlowyML automatically selects the appropriate materializer based on type hints:

| Materializer | Types | Format | When Used |
|---|---|---|---|
| `PandasMaterializer` | `pd.DataFrame`, `pd.Series` | Parquet or CSV | DataFrames and Series |
| `NumpyMaterializer` | `np.ndarray` | `.npy` | NumPy arrays |
| `JsonMaterializer` | `dict`, `list`, `str`, `int`, `float` | JSON | Simple Python types |
| `PickleMaterializer` | Anything else | Pickle | Fallback for arbitrary objects |

Usage is automatic — just add type hints to your steps:

```python
import pandas as pd
from flowyml import step

@step(outputs=["features"])
def create_features(raw_data: pd.DataFrame) -> pd.DataFrame:
    """FlowyML auto-selects PandasMaterializer for both input and output."""
    return raw_data.drop(columns=["id"])
```

---

## 🛠 Creating Custom Materializers

Subclass `BaseMaterializer` to support your own types:

### Example: PyTorch Model Materializer

```python
import torch
from flowyml.io import BaseMaterializer

class PyTorchMaterializer(BaseMaterializer):
    """Save and load PyTorch models with metadata."""
    ASSOCIATED_TYPES = (torch.nn.Module,)

    def handle_input(self, data_type):
        """Load a model from the artifact store."""
        with open(self.artifact.uri, "rb") as f:
            return torch.load(f, weights_only=False)

    def handle_return(self, model):
        """Save a model to the artifact store."""
        with open(self.artifact.uri, "wb") as f:
            torch.save(model, f)
```

### Example: ONNX Model Materializer

```python
import onnx
from flowyml.io import BaseMaterializer

class ONNXMaterializer(BaseMaterializer):
    """Save models in cross-platform ONNX format."""
    ASSOCIATED_TYPES = (onnx.ModelProto,)

    def handle_input(self, data_type):
        return onnx.load(self.artifact.uri)

    def handle_return(self, model):
        onnx.save(model, self.artifact.uri)
```

---

## Registering Materializers 🔧

Register once at startup — FlowyML will auto-select it whenever the matching type appears:

```python
from flowyml import materializer_registry

# Register custom materializer
materializer_registry.register(PyTorchMaterializer)
materializer_registry.register(ONNXMaterializer)
```

---

## Using Custom Types in Steps 🧩

Once registered, FlowyML automatically uses your materializer when a step returns the associated type:

```python
import torch.nn as nn

@step(outputs=["model"])
def train_model(features) -> nn.Module:
    """FlowyML auto-uses PyTorchMaterializer for nn.Module."""
    model = nn.Sequential(nn.Linear(10, 5), nn.ReLU(), nn.Linear(5, 1))
    # ... train ...
    return model
```

---

## `BaseMaterializer` API

| Method | Description |
|---|---|
| `handle_input(data_type)` | Deserialize artifact from storage → Python object |
| `handle_return(obj)` | Serialize Python object → artifact in storage |

| Class Variable | Type | Description |
|---|---|---|
| `ASSOCIATED_TYPES` | `tuple[type, ...]` | Types this materializer handles |

---

## Best Practices 💡

!!! tip "Use type hints"
    FlowyML selects materializers based on type hints. Always annotate your step return types for automatic serialization.

!!! tip "Prefer standard formats"
    Save models as ONNX, datasets as Parquet, configs as JSON. This makes artifacts usable outside Python.

!!! warning "Avoid pickle in production"
    The `PickleMaterializer` is the fallback — it's insecure and non-portable. Register custom materializers for production types.

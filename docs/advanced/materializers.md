# Materializers 📦

Teach UniFlow how to save and load your custom objects.

> [!NOTE]
> **What you'll learn**: How to make any Python object persistable and trackable
>
> **Key insight**: If you can't save it, you can't cache it, version it, or inspect it. Materializers bridge the gap between memory and storage.

## Why Custom Serialization Matters

**Without materializers**:
- **Pickle hell**: Relying on `pickle` for everything (brittle, insecure)
- **Lost metadata**: Saving a model as bytes loses its hyperparameters
- **No visualization**: The UI can't show a preview of a custom object

**With UniFlow materializers**:
- **Optimized storage**: Save large arrays as Parquet/Numpy, not JSON
- **Rich visualization**: Tell the UI how to display your object
- **Cross-language support**: Save as standard formats (ONNX, CSV) usable by other tools

## 📦 Built-in Materializers

UniFlow automatically selects the appropriate materializer based on the type hint or object type.

- **PandasMaterializer**: Parquet or CSV.
- **NumpyMaterializer**: `.npy` files.
- **JsonMaterializer**: JSON files.
- **PickleMaterializer**: Fallback for arbitrary Python objects.

## 🛠 Custom Materializers

To support a custom type, subclass `BaseMaterializer`.

## Real-World Pattern: PyTorch Model Wrapper

Save PyTorch models with their metadata in a clean, versioned way.

```python
import torch
from uniflow.io import BaseMaterializer

class PyTorchMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (torch.nn.Module,)

    def handle_input(self, data_type):
        # Load model state dict
        with open(self.artifact.uri, 'rb') as f:
            return torch.load(f)

    def handle_return(self, model):
        # Save model state dict
        with open(self.artifact.uri, 'wb') as f:
            torch.save(model, f)

# Register it once
from uniflow import materializer_registry
materializer_registry.register(PyTorchMaterializer)
```

## 🎯 Usage

Once registered, UniFlow will automatically use your materializer when a step returns a `CustomGraph` object.

```python
@step
def build_graph() -> CustomGraph:
    return CustomGraph(...)
```

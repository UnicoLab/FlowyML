# Materializers 📦

Materializers are the secret sauce that allows UniFlow to save and load complex objects (like PyTorch models or Pandas DataFrames) to and from disk.

## How it Works ⚙️

When a step returns an object, UniFlow looks for a registered **Materializer** that supports that object type.

1.  **Serialization**: The materializer's `save()` method writes the object to the artifact store.
2.  **Deserialization**: When the object is needed (e.g., by a downstream step or when loading from cache), the `load()` method reads it back into memory.

## Supported Types ✅

UniFlow comes with built-in materializers for:

| Type | Materializer | Format |
|------|--------------|--------|
| `pandas.DataFrame` | `PandasMaterializer` | Parquet / CSV |
| `numpy.ndarray` | `NumpyMaterializer` | `.npy` |
| `torch.nn.Module` | `PyTorchMaterializer` | `.pt` (TorchScript/StateDict) |
| `tensorflow.keras.Model` | `TensorFlowMaterializer` | SavedModel |
| `sklearn.base.BaseEstimator` | `SklearnMaterializer` | Pickle (joblib) |
| Any other object | `PickleMaterializer` | Pickle |

## Custom Materializers 🛠️

You can define custom materializers for your own types.

### 1. Define the Materializer

Inherit from `BaseMaterializer` and implement `save`, `load`, and `supported_types`.

```python
from uniflow.storage.materializers.base import BaseMaterializer
from PIL import Image
import os

class ImageMaterializer(BaseMaterializer):
    def save(self, obj: Image.Image, path: Path) -> None:
        obj.save(os.path.join(path, "image.png"))

    def load(self, path: Path) -> Image.Image:
        return Image.open(os.path.join(path, "image.png"))

    @classmethod
    def supported_types(cls):
        return [Image.Image]
```

### 2. Register it

```python
from uniflow.storage.materializers import register_materializer

register_materializer(ImageMaterializer)
```

!!! success "Automatic Usage"
    Now, any step returning a PIL Image will automatically use your custom materializer!

```python
@step
def process_image() -> Image.Image:
    # ...
    return img  # Automatically saved as PNG
```

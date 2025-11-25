"""PyTorch materializer for model serialization."""

import json
from pathlib import Path
from typing import Any, Type

from uniflow.storage.materializers.base import BaseMaterializer, register_materializer

try:
    import torch
    import torch.nn as nn
    # Verify PyTorch has expected attributes
    _ = nn.Module
    _ = torch.Tensor
    PYTORCH_AVAILABLE = True
except (ImportError, AttributeError):
    PYTORCH_AVAILABLE = False
    torch = None
    nn = None


if PYTORCH_AVAILABLE:
    class PyTorchMaterializer(BaseMaterializer):
        """Materializer for PyTorch models and tensors."""

        def save(self, obj: Any, path: Path) -> None:
            """Save PyTorch object to path.

            Args:
                obj: PyTorch model or tensor
                path: Directory path where object should be saved
            """
            path.mkdir(parents=True, exist_ok=True)

            if isinstance(obj, nn.Module):
                # Save model
                model_path = path / "model.pt"
                torch.save(obj.state_dict(), model_path)

                # Save model architecture info
                metadata = {
                    "type": "pytorch_model",
                    "class_name": obj.__class__.__name__,
                    "module": obj.__class__.__module__,
                }

                # Try to capture model architecture
                try:
                    metadata["architecture"] = str(obj)
                except:
                    pass

                with open(path / "metadata.json", 'w') as f:
                    json.dump(metadata, f, indent=2)

            elif isinstance(obj, torch.Tensor):
                # Save tensor
                tensor_path = path / "tensor.pt"
                torch.save(obj, tensor_path)

                metadata = {
                    "type": "pytorch_tensor",
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                    "device": str(obj.device),
                }

                with open(path / "metadata.json", 'w') as f:
                    json.dump(metadata, f, indent=2)

            else:
                # Generic PyTorch object
                obj_path = path / "object.pt"
                torch.save(obj, obj_path)

                metadata = {"type": "pytorch_object"}
                with open(path / "metadata.json", 'w') as f:
                    json.dump(metadata, f, indent=2)

        def load(self, path: Path) -> Any:
            """Load PyTorch object from path.

            Args:
                path: Directory path from which to load object

            Returns:
                Loaded PyTorch object
            """
            # Load metadata
            metadata_path = path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            obj_type = metadata.get("type", "pytorch_object")

            if obj_type == "pytorch_model":
                # Load model state dict only (user needs to provide architecture)
                model_path = path / "model.pt"
                return torch.load(model_path, weights_only=True)

            elif obj_type == "pytorch_tensor":
                tensor_path = path / "tensor.pt"
                return torch.load(tensor_path, weights_only=True)

            else:
                obj_path = path / "object.pt"
                return torch.load(obj_path, weights_only=False)

        @classmethod
        def supported_types(cls) -> list[Type]:
            """Return PyTorch types supported by this materializer."""
            return [nn.Module, torch.Tensor]

    # Auto-register
    register_materializer(PyTorchMaterializer)

else:
    # Placeholder when PyTorch not available
    class PyTorchMaterializer(BaseMaterializer):
        """Placeholder materializer when PyTorch is not installed."""

        def save(self, obj: Any, path: Path) -> None:
            raise ImportError("PyTorch is not installed. Install with: pip install torch")

        def load(self, path: Path) -> Any:
            raise ImportError("PyTorch is not installed. Install with: pip install torch")

        @classmethod
        def supported_types(cls) -> list[Type]:
            return []

"""NumPy materializer for array serialization."""

import json
from pathlib import Path
from typing import Any, Type

from uniflow.storage.materializers.base import BaseMaterializer, register_materializer

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


if NUMPY_AVAILABLE:
    class NumPyMaterializer(BaseMaterializer):
        """Materializer for NumPy arrays."""

        def save(self, obj: Any, path: Path) -> None:
            """Save NumPy array to path.

            Args:
                obj: NumPy array
                path: Directory path where object should be saved
            """
            path.mkdir(parents=True, exist_ok=True)

            # Save array
            array_path = path / "array.npy"
            np.save(array_path, obj)

            # Save metadata
            metadata = {
                "type": "numpy_array",
                "shape": list(obj.shape),
                "dtype": str(obj.dtype),
                "size": int(obj.size),
                "ndim": int(obj.ndim),
            }

            # Add statistics for numerical arrays
            if np.issubdtype(obj.dtype, np.number):
                try:
                    metadata["min"] = float(np.min(obj))
                    metadata["max"] = float(np.max(obj))
                    metadata["mean"] = float(np.mean(obj))
                    metadata["std"] = float(np.std(obj))
                except:
                    pass

            with open(path / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)

        def load(self, path: Path) -> Any:
            """Load NumPy array from path.

            Args:
                path: Directory path from which to load object

            Returns:
                Loaded NumPy array
            """
            array_path = path / "array.npy"

            if not array_path.exists():
                raise FileNotFoundError(f"Array file not found at {array_path}")

            return np.load(array_path)

        @classmethod
        def supported_types(cls) -> list[Type]:
            """Return NumPy types supported by this materializer."""
            return [np.ndarray]

    # Auto-register
    register_materializer(NumPyMaterializer)

else:
    # Placeholder when NumPy not available
    class NumPyMaterializer(BaseMaterializer):
        """Placeholder materializer when NumPy is not installed."""

        def save(self, obj: Any, path: Path) -> None:
            raise ImportError("NumPy is not installed. Install with: pip install numpy")

        def load(self, path: Path) -> Any:
            raise ImportError("NumPy is not installed. Install with: pip install numpy")

        @classmethod
        def supported_types(cls) -> list[Type]:
            return []

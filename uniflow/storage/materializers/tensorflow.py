"""TensorFlow materializer for model serialization."""

import json
from pathlib import Path
from typing import Any, Type

from uniflow.storage.materializers.base import BaseMaterializer, register_materializer

try:
    import tensorflow as tf
    # Verify TensorFlow has expected attributes
    _ = tf.keras.Model
    _ = tf.Tensor
    _ = tf.Variable
    TENSORFLOW_AVAILABLE = True
except (ImportError, AttributeError):
    TENSORFLOW_AVAILABLE = False
    tf = None


if TENSORFLOW_AVAILABLE:
    class TensorFlowMaterializer(BaseMaterializer):
        """Materializer for TensorFlow/Keras models."""

        def save(self, obj: Any, path: Path) -> None:
            """Save TensorFlow object to path.

            Args:
                obj: TensorFlow model or tensor
                path: Directory path where object should be saved
            """
            path.mkdir(parents=True, exist_ok=True)

            if isinstance(obj, tf.keras.Model):
                # Save Keras model in SavedModel format
                model_path = path / "saved_model"
                obj.save(model_path, save_format='tf')

                # Save metadata
                metadata = {
                    "type": "tensorflow_keras_model",
                    "class_name": obj.__class__.__name__,
                    "input_shape": str(obj.input_shape) if hasattr(obj, 'input_shape') else None,
                    "output_shape": str(obj.output_shape) if hasattr(obj, 'output_shape') else None,
                }

                # Try to get model config
                try:
                    metadata["config"] = obj.get_config()
                except:
                    pass

                with open(path / "metadata.json", 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)

            elif isinstance(obj, tf.Tensor):
                # Save tensor as numpy array
                import numpy as np
                tensor_path = path / "tensor.npy"
                np.save(tensor_path, obj.numpy())

                metadata = {
                    "type": "tensorflow_tensor",
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                }

                with open(path / "metadata.json", 'w') as f:
                    json.dump(metadata, f, indent=2)

            elif isinstance(obj, tf.Variable):
                # Save variable
                import numpy as np
                var_path = path / "variable.npy"
                np.save(var_path, obj.numpy())

                metadata = {
                    "type": "tensorflow_variable",
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                    "name": obj.name,
                }

                with open(path / "metadata.json", 'w') as f:
                    json.dump(metadata, f, indent=2)

        def load(self, path: Path) -> Any:
            """Load TensorFlow object from path.

            Args:
                path: Directory path from which to load object

            Returns:
                Loaded TensorFlow object
            """
            # Load metadata
            metadata_path = path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            obj_type = metadata.get("type", "tensorflow_object")

            if obj_type == "tensorflow_keras_model":
                model_path = path / "saved_model"
                return tf.keras.models.load_model(model_path)

            elif obj_type == "tensorflow_tensor":
                import numpy as np
                tensor_path = path / "tensor.npy"
                array = np.load(tensor_path)
                return tf.convert_to_tensor(array)

            elif obj_type == "tensorflow_variable":
                import numpy as np
                var_path = path / "variable.npy"
                array = np.load(var_path)
                return tf.Variable(array, name=metadata.get("name"))

            else:
                raise ValueError(f"Unknown TensorFlow object type: {obj_type}")

        @classmethod
        def supported_types(cls) -> list[Type]:
            """Return TensorFlow types supported by this materializer."""
            return [tf.keras.Model, tf.Tensor, tf.Variable]

    # Auto-register
    register_materializer(TensorFlowMaterializer)

else:
    # Placeholder when TensorFlow not available
    class TensorFlowMaterializer(BaseMaterializer):
        """Placeholder materializer when TensorFlow is not installed."""

        def save(self, obj: Any, path: Path) -> None:
            raise ImportError("TensorFlow is not installed. Install with: pip install tensorflow")

        def load(self, path: Path) -> Any:
            raise ImportError("TensorFlow is not installed. Install with: pip install tensorflow")

        @classmethod
        def supported_types(cls) -> list[Type]:
            return []

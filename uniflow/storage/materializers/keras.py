"""Keras materializer for model serialization."""

import json
from pathlib import Path
from typing import Any, Type

from uniflow.storage.materializers.base import BaseMaterializer, register_materializer

try:
    import tensorflow as tf
    from tensorflow import keras
    # Verify Keras has expected attributes
    _ = keras.Model
    _ = keras.Sequential
    KERAS_AVAILABLE = True
except (ImportError, AttributeError):
    KERAS_AVAILABLE = False
    keras = None


if KERAS_AVAILABLE:
    class KerasMaterializer(BaseMaterializer):
        """Materializer for Keras models with full support for Sequential and Functional API."""

        def save(self, obj: Any, path: Path) -> None:
            """Save Keras model to path.

            Args:
                obj: Keras model (Sequential or Functional)
                path: Directory path where model should be saved
            """
            path.mkdir(parents=True, exist_ok=True)

            if isinstance(obj, keras.Model):
                # Save model in Keras native format (.keras)
                model_path = path / "model.keras"
                obj.save(model_path)

                # Save comprehensive metadata
                metadata = {
                    "type": "keras_model",
                    "class_name": obj.__class__.__name__,
                    "model_type": "Sequential" if isinstance(obj, keras.Sequential) else "Functional",
                }

                # Get input/output shapes
                try:
                    if hasattr(obj, 'input_shape'):
                        metadata["input_shape"] = str(obj.input_shape)
                    if hasattr(obj, 'output_shape'):
                        metadata["output_shape"] = str(obj.output_shape)
                except:
                    pass

                # Get model architecture summary
                try:
                    import io
                    string_buffer = io.StringIO()
                    obj.summary(print_fn=lambda x: string_buffer.write(x + '\n'))
                    metadata["summary"] = string_buffer.getvalue()
                except:
                    pass

                # Get layer information
                try:
                    metadata["num_layers"] = len(obj.layers)
                    metadata["layer_names"] = [layer.name for layer in obj.layers]
                    metadata["trainable_params"] = obj.count_params()
                except:
                    pass

                # Get optimizer info if compiled
                try:
                    if obj.optimizer:
                        metadata["optimizer"] = obj.optimizer.__class__.__name__
                        metadata["learning_rate"] = float(keras.backend.get_value(obj.optimizer.learning_rate))
                except:
                    pass

                # Get loss function if compiled
                try:
                    if obj.loss:
                        if hasattr(obj.loss, '__name__'):
                            metadata["loss"] = obj.loss.__name__
                        else:
                            metadata["loss"] = str(obj.loss)
                except:
                    pass

                # Get metrics if compiled
                try:
                    if obj.metrics:
                        metadata["metrics"] = [m.name for m in obj.metrics]
                except:
                    pass

                # Save model config
                try:
                    config = obj.get_config()
                    config_path = path / "config.json"
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2, default=str)
                    metadata["has_config"] = True
                except:
                    metadata["has_config"] = False

                # Save weights separately for backup - REMOVED for Keras 3 compatibility
                # try:
                #     weights_path = path / "weights.h5"
                #     obj.save_weights(weights_path)
                #     metadata["has_weights_backup"] = True
                # except:
                #     metadata["has_weights_backup"] = False

                # Save metadata
                metadata_path = path / "metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)

            else:
                raise TypeError(f"Expected keras.Model, got {type(obj)}")

        def load(self, path: Path) -> Any:
            """Load Keras model from path.

            Args:
                path: Directory path from which to load model

            Returns:
                Loaded Keras model
            """
            # Load metadata
            metadata_path = path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            # Load model from .keras file
            model_path = path / "model.keras"
            if model_path.exists():
                model = keras.models.load_model(model_path)
                return model

            # Fallback: try to load from SavedModel format
            saved_model_path = path / "saved_model"
            if saved_model_path.exists():
                model = keras.models.load_model(saved_model_path)
                return model

            raise FileNotFoundError(f"No Keras model found at {path}")

        @classmethod
        def supported_types(cls) -> list[Type]:
            """Return Keras types supported by this materializer."""
            return [keras.Model, keras.Sequential]

    # Auto-register
    register_materializer(KerasMaterializer)

else:
    # Placeholder when Keras not available
    class KerasMaterializer(BaseMaterializer):
        """Placeholder materializer when Keras is not installed."""

        def save(self, obj: Any, path: Path) -> None:
            raise ImportError("Keras/TensorFlow is not installed. Install with: pip install tensorflow")

        def load(self, path: Path) -> Any:
            raise ImportError("Keras/TensorFlow is not installed. Install with: pip install tensorflow")

        @classmethod
        def supported_types(cls) -> list[Type]:
            return []

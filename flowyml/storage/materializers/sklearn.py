"""Scikit-learn materializer for model serialization."""

import json
import pickle
from pathlib import Path
from typing import Any

from flowyml.storage.materializers.base import BaseMaterializer, register_materializer
import contextlib
import builtins

try:
    from sklearn.base import BaseEstimator

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


if SKLEARN_AVAILABLE:

    class SklearnMaterializer(BaseMaterializer):
        """Materializer for scikit-learn models."""

        def save(self, obj: Any, path: Path) -> None:
            """Save scikit-learn model to path.

            Args:
                obj: Scikit-learn model
                path: Directory path where object should be saved
            """
            path.mkdir(parents=True, exist_ok=True)

            # Save model using pickle
            model_path = path / "model.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(obj, f)

            # Save metadata
            metadata = {
                "type": "sklearn_model",
                "class_name": obj.__class__.__name__,
                "module": obj.__class__.__module__,
            }

            # Capture model parameters
            with contextlib.suppress(builtins.BaseException):
                metadata["params"] = obj.get_params()

            # Capture feature importance if available
            if hasattr(obj, "feature_importances_"):
                with contextlib.suppress(builtins.BaseException):
                    metadata["feature_importances"] = obj.feature_importances_.tolist()

            # Capture number of features
            if hasattr(obj, "n_features_in_"):
                metadata["n_features"] = int(obj.n_features_in_)

            # Capture feature names if available
            if hasattr(obj, "feature_names_in_"):
                with contextlib.suppress(builtins.BaseException):
                    metadata["feature_names"] = obj.feature_names_in_.tolist()

            # Capture classes if classifier
            if hasattr(obj, "classes_"):
                with contextlib.suppress(builtins.BaseException):
                    metadata["classes"] = obj.classes_.tolist()

            with open(path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2, default=str)

        def load(self, path: Path) -> Any:
            """Load scikit-learn model from path.

            Args:
                path: Directory path from which to load object

            Returns:
                Loaded scikit-learn model
            """
            model_path = path / "model.pkl"

            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found at {model_path}")

            with open(model_path, "rb") as f:
                return pickle.load(f)

        @classmethod
        def supported_types(cls) -> list[type]:
            """Return scikit-learn types supported by this materializer."""
            return [BaseEstimator]

    # Auto-register
    register_materializer(SklearnMaterializer)

else:
    # Placeholder when scikit-learn not available
    class SklearnMaterializer(BaseMaterializer):
        """Placeholder materializer when scikit-learn is not installed."""

        def save(self, obj: Any, path: Path) -> None:
            raise ImportError("Scikit-learn is not installed. Install with: pip install scikit-learn")

        def load(self, path: Path) -> Any:
            raise ImportError("Scikit-learn is not installed. Install with: pip install scikit-learn")

        @classmethod
        def supported_types(cls) -> list[type]:
            return []

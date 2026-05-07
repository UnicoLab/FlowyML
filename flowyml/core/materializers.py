"""Materializer System — Type-aware serialization/deserialization for artifacts.

Inspired by ZenML's materializer pattern, this module provides a registry of
type-specific serializers. Each materializer knows how to save and load a
specific Python type (DataFrame, ndarray, PyMC model, ArviZ InferenceData, etc.)

Built-in materializers:
    - CloudPickleMaterializer: Default fallback for any type
    - PandasMaterializer: DataFrames → parquet
    - NumpyMaterializer: ndarrays → .npy
    - JsonMaterializer: dicts/lists → JSON
    - ArviZMaterializer: InferenceData → netCDF

Users can register custom materializers:
    from flowyml.core.materializers import materializer_registry, Materializer

    class MyModelMaterializer(Materializer):
        ASSOCIATED_TYPES = (MyModel,)

        def save(self, data, path):
            data.save_weights(path / "weights.h5")

        def load(self, path):
            return MyModel.load(path / "weights.h5")

    materializer_registry.register(MyModelMaterializer)
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger("flowyml.materializers")


# ── Base Materializer ─────────────────────────────────────────────────────


class Materializer(ABC):
    """Base class for type-specific serialization.

    Subclass this and define ASSOCIATED_TYPES to create a materializer
    for your custom types. The materializer registry will automatically
    dispatch to the correct materializer based on the object's type.

    Attributes:
        ASSOCIATED_TYPES: Tuple of Python types this materializer handles.
    """

    ASSOCIATED_TYPES: tuple[type, ...] = ()

    @abstractmethod
    def save(self, data: Any, path: Path) -> None:
        """Serialize data to a file/directory.

        Args:
            data: The Python object to serialize.
            path: Base path (without extension). The materializer adds
                  the appropriate extension.
        """

    @abstractmethod
    def load(self, path: Path) -> Any:
        """Deserialize data from a file/directory.

        Args:
            path: Base path (the materializer knows which files to read).

        Returns:
            The deserialized Python object.
        """

    def get_extension(self) -> str:
        """Return the file extension used by this materializer."""
        return ".pkl"


# ── Built-in Materializers ───────────────────────────────────────────────


class CloudPickleMaterializer(Materializer):
    """Default materializer using cloudpickle.

    Handles virtually any Python object including closures, lambdas,
    compiled code, and complex nested structures. This is the universal
    fallback when no type-specific materializer is registered.
    """

    ASSOCIATED_TYPES = ()  # Matches everything as fallback

    def save(self, data: Any, path: Path) -> None:
        import cloudpickle

        target = path.with_suffix(".pkl")
        with open(target, "wb") as f:
            cloudpickle.dump(data, f)

    def load(self, path: Path) -> Any:
        import cloudpickle

        target = path.with_suffix(".pkl")
        with open(target, "rb") as f:
            return cloudpickle.load(f)

    def get_extension(self) -> str:
        return ".pkl"


class PandasMaterializer(Materializer):
    """Materializer for pandas DataFrames → Parquet format.

    Parquet provides efficient columnar storage, type preservation,
    and is much smaller than CSV for large datasets.
    Falls back to cloudpickle if pyarrow/fastparquet is not installed.
    """

    ASSOCIATED_TYPES = ()  # Populated at registration time

    def __init__(self):
        try:
            import pandas as pd

            self.ASSOCIATED_TYPES = (pd.DataFrame,)
        except ImportError:
            pass
        self._has_parquet = self._check_parquet()

    @staticmethod
    def _check_parquet() -> bool:
        """Check if a parquet engine is available."""
        try:
            import pyarrow  # noqa: F401

            return True
        except ImportError:
            pass
        try:
            import fastparquet  # noqa: F401

            return True
        except ImportError:
            pass
        return False

    def save(self, data: Any, path: Path) -> None:
        if self._has_parquet:
            target = path.with_suffix(".parquet")
            data.to_parquet(target, index=True)
        else:
            # Fallback: cloudpickle
            import cloudpickle

            target = path.with_suffix(".pkl")
            with open(target, "wb") as f:
                cloudpickle.dump(data, f)

    def load(self, path: Path) -> Any:
        parquet_path = path.with_suffix(".parquet")
        pkl_path = path.with_suffix(".pkl")
        if parquet_path.exists():
            import pandas as pd

            return pd.read_parquet(parquet_path)
        elif pkl_path.exists():
            import cloudpickle

            with open(pkl_path, "rb") as f:
                return cloudpickle.load(f)
        raise FileNotFoundError(f"No DataFrame file at {path}")

    def get_extension(self) -> str:
        return ".parquet" if self._has_parquet else ".pkl"


class NumpyMaterializer(Materializer):
    """Materializer for numpy arrays → .npy format."""

    ASSOCIATED_TYPES = ()

    def __init__(self):
        try:
            import numpy as np

            self.ASSOCIATED_TYPES = (np.ndarray,)
        except ImportError:
            pass

    def save(self, data: Any, path: Path) -> None:
        import numpy as np

        target = path.with_suffix(".npy")
        np.save(target, data, allow_pickle=False)

    def load(self, path: Path) -> Any:
        import numpy as np

        target = path.with_suffix(".npy")
        return np.load(target, allow_pickle=False)

    def get_extension(self) -> str:
        return ".npy"


class JsonMaterializer(Materializer):
    """Materializer for JSON-serializable dicts and lists."""

    ASSOCIATED_TYPES = (dict, list)

    def save(self, data: Any, path: Path) -> None:
        target = path.with_suffix(".json")
        with open(target, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load(self, path: Path) -> Any:
        target = path.with_suffix(".json")
        with open(target) as f:
            return json.load(f)

    def get_extension(self) -> str:
        return ".json"


class ArviZMaterializer(Materializer):
    """Materializer for ArviZ InferenceData → netCDF format.

    ArviZ InferenceData objects (produced by PyMC sampling) contain
    posterior samples, observed data, etc. netCDF is the standard
    format for xarray-based data structures.
    """

    ASSOCIATED_TYPES = ()

    def __init__(self):
        try:
            import arviz as az

            self.ASSOCIATED_TYPES = (az.InferenceData,)
        except ImportError:
            pass

    def save(self, data: Any, path: Path) -> None:
        target = path.with_suffix(".nc")
        data.to_netcdf(str(target))

    def load(self, path: Path) -> Any:
        import arviz as az

        target = path.with_suffix(".nc")
        return az.from_netcdf(str(target))

    def get_extension(self) -> str:
        return ".nc"


class FlowyMLArtifactMaterializer(Materializer):
    """Materializer for FlowyML Artifact types (Model, Dataset, Metrics, Report).

    These types wrap a `.data` attribute plus metadata. We serialize:
    1. The metadata envelope as JSON (.meta.json)
    2. The inner `.data` using the best available materializer for its type

    This ensures that even when the inner data is a complex PyMC model,
    the metadata is preserved and the data is serialized correctly.
    """

    ASSOCIATED_TYPES = ()

    def __init__(self):
        try:
            from flowyml.core.types import Artifact

            self.ASSOCIATED_TYPES = (Artifact,)
        except ImportError:
            pass

    def save(self, data: Any, path: Path) -> None:
        # Save metadata envelope
        meta_path = path.with_suffix(".artifact.json")
        meta = data.to_dict()
        # Add class info for deserialization
        meta["__artifact_class__"] = type(data).__name__
        meta["__artifact_module__"] = type(data).__module__

        # Collect non-data fields
        extra_fields = {}
        for attr_name in vars(data):
            if attr_name.startswith("_") or attr_name == "data":
                continue
            val = getattr(data, attr_name)
            if isinstance(val, (str, int, float, bool, list, dict, type(None))):
                extra_fields[attr_name] = val
        meta["__fields__"] = extra_fields

        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2, default=str)

        # Save the inner data using cloudpickle (handles PyMC, sklearn, etc.)
        data_path = path.with_suffix(".data.pkl")
        import cloudpickle

        with open(data_path, "wb") as f:
            cloudpickle.dump(data.data, f)

    def load(self, path: Path) -> Any:
        import importlib

        # Load metadata
        meta_path = path.with_suffix(".artifact.json")
        with open(meta_path) as f:
            meta = json.load(f)

        # Load inner data
        data_path = path.with_suffix(".data.pkl")
        import cloudpickle

        with open(data_path, "rb") as f:
            inner_data = cloudpickle.load(f)

        # Reconstruct the artifact
        cls_name = meta.get("__artifact_class__", "Artifact")
        cls_module = meta.get("__artifact_module__", "flowyml.core.types")
        mod = importlib.import_module(cls_module)
        cls = getattr(mod, cls_name)

        # Build kwargs from saved fields
        fields = meta.get("__fields__", {})
        fields["data"] = inner_data
        if "name" in meta and "name" not in fields:
            fields["name"] = meta.get("name")

        artifact = cls(**fields)
        return artifact

    def get_extension(self) -> str:
        return ".artifact.json"  # primary file


# ── Materializer Registry ───────────────────────────────────────────────


class MaterializerRegistry:
    """Registry that maps Python types to their materializers.

    Lookup order:
    1. Exact type match (user-registered custom materializers first)
    2. Subclass match (e.g., FlowyML Artifact types)
    3. Fallback to CloudPickleMaterializer
    """

    def __init__(self):
        self._registry: list[Materializer] = []
        self._fallback = CloudPickleMaterializer()
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in materializers."""
        # Order matters: more specific types first
        for mat_cls in [
            FlowyMLArtifactMaterializer,
            ArviZMaterializer,
            PandasMaterializer,
            NumpyMaterializer,
            # JsonMaterializer intentionally excluded from defaults —
            # dicts/lists are often used as generic containers that may
            # contain non-JSON-serializable values. CloudPickle handles
            # them safely.
        ]:
            mat = mat_cls()
            if mat.ASSOCIATED_TYPES:
                self._registry.append(mat)

    def register(self, materializer: Materializer | type) -> None:
        """Register a custom materializer.

        Custom materializers are checked before built-ins.

        Args:
            materializer: A Materializer instance or class.
        """
        if isinstance(materializer, type):
            materializer = materializer()
        # Insert at front for priority over built-ins
        self._registry.insert(0, materializer)
        logger.info(
            "Registered materializer %s for types: %s",
            type(materializer).__name__,
            [t.__name__ for t in materializer.ASSOCIATED_TYPES],
        )

    def get_materializer(self, obj: Any) -> Materializer:
        """Find the best materializer for an object.

        Args:
            obj: The Python object to serialize.

        Returns:
            The matched Materializer instance.
        """
        obj_type = type(obj)

        # 1. Exact type match
        for mat in self._registry:
            if obj_type in mat.ASSOCIATED_TYPES:
                return mat

        # 2. Subclass match (e.g., FlowyML Model → Artifact materializer)
        for mat in self._registry:
            for assoc_type in mat.ASSOCIATED_TYPES:
                if isinstance(obj, assoc_type):
                    return mat

        # 3. Fallback
        return self._fallback

    def get_materializer_for_type(self, type_name: str) -> Materializer:
        """Find a materializer by type name string (for deserialization).

        Args:
            type_name: The class name string.

        Returns:
            The matched Materializer instance.
        """
        for mat in self._registry:
            for assoc_type in mat.ASSOCIATED_TYPES:
                if assoc_type.__name__ == type_name:
                    return mat
        return self._fallback


# Module-level singleton
materializer_registry = MaterializerRegistry()

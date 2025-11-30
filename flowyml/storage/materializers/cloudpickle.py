"""Cloudpickle materializer for robust Python object serialization."""

from pathlib import Path
from typing import Any

from flowyml.storage.materializers.base import BaseMaterializer, register_materializer

try:
    import cloudpickle

    CLOUDPICKLE_AVAILABLE = True
except ImportError:
    CLOUDPICKLE_AVAILABLE = False


if CLOUDPICKLE_AVAILABLE:

    class CloudpickleMaterializer(BaseMaterializer):
        """Materializer using cloudpickle for robust serialization."""

        def save(self, obj: Any, path: Path) -> None:
            """Save object using cloudpickle.

            Args:
                obj: Object to save
                path: Directory path where object should be saved
            """
            path.mkdir(parents=True, exist_ok=True)

            file_path = path / "data.cloudpickle"
            with open(file_path, "wb") as f:
                cloudpickle.dump(obj, f)

        def load(self, path: Path) -> Any:
            """Load object using cloudpickle.

            Args:
                path: Directory path from which to load object

            Returns:
                Loaded object
            """
            file_path = path / "data.cloudpickle"
            if not file_path.exists():
                raise FileNotFoundError(f"Cloudpickle file not found at {file_path}")

            with open(file_path, "rb") as f:
                return cloudpickle.load(f)

        @classmethod
        def supported_types(cls) -> list[type]:
            """Return types supported by this materializer.

            Cloudpickle can handle almost anything, but we don't want it to claim
            types that have specific materializers (like DataFrame).
            So we return object, but it should be registered with low priority
            or used as explicit fallback.
            """
            return [object]

    # Register it
    register_materializer(CloudpickleMaterializer)

else:

    class CloudpickleMaterializer(BaseMaterializer):
        """Placeholder when cloudpickle is not available."""

        def save(self, obj: Any, path: Path) -> None:
            raise ImportError("cloudpickle is not installed")

        def load(self, path: Path) -> Any:
            raise ImportError("cloudpickle is not installed")

        @classmethod
        def supported_types(cls) -> list[type]:
            return []

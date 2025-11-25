"""Base materializer class and registry."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Type, Dict, Optional


class BaseMaterializer(ABC):
    """Base class for all materializers.

    Materializers handle serialization/deserialization of specific types.
    """

    @abstractmethod
    def save(self, obj: Any, path: Path) -> None:
        """Save object to path.

        Args:
            obj: Object to save
            path: Directory path where object should be saved
        """
        pass

    @abstractmethod
    def load(self, path: Path) -> Any:
        """Load object from path.

        Args:
            path: Directory path from which to load object

        Returns:
            Loaded object
        """
        pass

    @classmethod
    @abstractmethod
    def supported_types(cls) -> list[Type]:
        """Return list of types this materializer supports."""
        pass

    @classmethod
    def can_handle(cls, obj: Any) -> bool:
        """Check if this materializer can handle the given object.

        Args:
            obj: Object to check

        Returns:
            True if this materializer can handle the object
        """
        obj_type = type(obj)
        for supported_type in cls.supported_types():
            if isinstance(obj, supported_type):
                return True
            # Check module name for cross-import compatibility
            if hasattr(supported_type, '__module__') and hasattr(obj_type, '__module__'):
                if (obj_type.__name__ == supported_type.__name__ and
                    obj_type.__module__ == supported_type.__module__):
                    return True
        return False


class MaterializerRegistry:
    """Registry for materializers."""

    def __init__(self):
        self._materializers: Dict[str, Type[BaseMaterializer]] = {}

    def register(self, materializer: Type[BaseMaterializer]) -> None:
        """Register a materializer.

        Args:
            materializer: Materializer class to register
        """
        for supported_type in materializer.supported_types():
            key = f"{supported_type.__module__}.{supported_type.__name__}"
            self._materializers[key] = materializer

    def get_materializer(self, obj: Any) -> Optional[BaseMaterializer]:
        """Get materializer for object.

        Args:
            obj: Object to find materializer for

        Returns:
            Materializer instance or None if no suitable materializer found
        """
        # First try exact match
        obj_type = type(obj)
        key = f"{obj_type.__module__}.{obj_type.__name__}"

        if key in self._materializers:
            return self._materializers[key]()

        # Then try checking all materializers
        for materializer_cls in set(self._materializers.values()):
            if materializer_cls.can_handle(obj):
                return materializer_cls()

        return None

    def list_materializers(self) -> Dict[str, Type[BaseMaterializer]]:
        """List all registered materializers.

        Returns:
            Dictionary mapping type names to materializer classes
        """
        return self._materializers.copy()


# Global registry instance
materializer_registry = MaterializerRegistry()


def register_materializer(materializer: Type[BaseMaterializer]) -> None:
    """Register a materializer with the global registry.

    Args:
        materializer: Materializer class to register
    """
    materializer_registry.register(materializer)


def get_materializer(obj: Any) -> Optional[BaseMaterializer]:
    """Get materializer for object from global registry.

    Args:
        obj: Object to find materializer for

    Returns:
        Materializer instance or None
    """
    return materializer_registry.get_materializer(obj)

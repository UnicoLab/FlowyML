"""
Plugin System for Custom Stack Components

This module provides a plugin system that allows users to:
1. Create custom stack components
2. Register them via entry points
3. Auto-discover components
4. Reuse ZenML community components
"""

import importlib
import sys
from typing import Dict, Type, Optional, List, Any
from pathlib import Path
import inspect

from uniflow.stacks.components import (
    StackComponent,
    Orchestrator,
    ArtifactStore,
    ContainerRegistry,
)


class ComponentRegistry:
    """
    Registry for stack component plugins.
    
    Supports:
    - Auto-discovery via entry points
    - Manual registration
    - Custom component loading
    - ZenML component wrapping
    """
    
    def __init__(self):
        self._orchestrators: Dict[str, Type[Orchestrator]] = {}
        self._artifact_stores: Dict[str, Type[ArtifactStore]] = {}
        self._container_registries: Dict[str, Type[ContainerRegistry]] = {}
        self._custom_components: Dict[str, Type[StackComponent]] = {}
        
        # Auto-discover plugins
        self._discover_plugins()
    
    def _discover_plugins(self):
        """Auto-discover plugins via entry points."""
        try:
            if sys.version_info >= (3, 10):
                from importlib.metadata import entry_points
                eps = entry_points()
                uniflow_eps = eps.select(group='uniflow.stack_components')
            else:
                import pkg_resources
                uniflow_eps = pkg_resources.iter_entry_points('uniflow.stack_components')
            
            for ep in uniflow_eps:
                try:
                    component_class = ep.load()
                    self.register(component_class)
                except Exception as e:
                    print(f"Warning: Could not load plugin {ep.name}: {e}")
        except Exception:
            # Entry points not available, skip auto-discovery
            pass
    
    def register(self, component_class: Type[StackComponent], name: Optional[str] = None):
        """
        Register a stack component.
        
        Args:
            component_class: Component class to register
            name: Optional name override. If None, uses class name in snake_case
        """
        if name is None:
            # Convert ClassName to class_name
            name = self._class_to_snake_case(component_class.__name__)
        
        # Determine component type and register
        if issubclass(component_class, Orchestrator):
            self._orchestrators[name] = component_class
        elif issubclass(component_class, ArtifactStore):
            self._artifact_stores[name] = component_class
        elif issubclass(component_class, ContainerRegistry):
            self._container_registries[name] = component_class
        else:
            self._custom_components[name] = component_class
    
    def get_orchestrator(self, name: str) -> Optional[Type[Orchestrator]]:
        """Get orchestrator class by name."""
        return self._orchestrators.get(name)
    
    def get_artifact_store(self, name: str) -> Optional[Type[ArtifactStore]]:
        """Get artifact store class by name."""
        return self._artifact_stores.get(name)
    
    def get_container_registry(self, name: str) -> Optional[Type[ContainerRegistry]]:
        """Get container registry class by name."""
        return self._container_registries.get(name)
    
    def get_component(self, name: str) -> Optional[Type[StackComponent]]:
        """Get any component by name."""
        return (
            self._orchestrators.get(name) or
            self._artifact_stores.get(name) or
            self._container_registries.get(name) or
            self._custom_components.get(name)
        )
    
    def list_orchestrators(self) -> List[str]:
        """List all registered orchestrators."""
        return list(self._orchestrators.keys())
    
    def list_artifact_stores(self) -> List[str]:
        """List all registered artifact stores."""
        return list(self._artifact_stores.keys())
    
    def list_container_registries(self) -> List[str]:
        """List all registered container registries."""
        return list(self._container_registries.keys())
    
    def list_all(self) -> Dict[str, List[str]]:
        """List all registered components."""
        return {
            "orchestrators": self.list_orchestrators(),
            "artifact_stores": self.list_artifact_stores(),
            "container_registries": self.list_container_registries(),
            "custom": list(self._custom_components.keys()),
        }
    
    def load_from_path(self, path: str, class_name: str):
        """
        Load a component from a Python file.
        
        Args:
            path: Path to Python file
            class_name: Name of class to load
        """
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("custom_module", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        component_class = getattr(module, class_name)
        self.register(component_class)
    
    def load_from_module(self, module_path: str):
        """
        Load all components from a module.
        
        Args:
            module_path: Dotted module path (e.g., 'my_package.components')
        """
        module = importlib.import_module(module_path)
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, StackComponent) and obj != StackComponent:
                self.register(obj)
    
    def wrap_zenml_component(self, zenml_component_class: Any, name: str):
        """
        Wrap a ZenML component for use in UniFlow.
        
        Args:
            zenml_component_class: ZenML component class
            name: Name to register under
        """
        # Create wrapper that adapts ZenML interface to UniFlow
        # This is a simplified example - actual implementation would need
        # more sophisticated wrapping
        
        class ZenMLWrapper(StackComponent):
            def __init__(self, **kwargs):
                super().__init__(name)
                self._zenml_component = zenml_component_class(**kwargs)
            
            @property
            def component_type(self):
                # Map ZenML type to UniFlow type
                from uniflow.stacks.components import ComponentType
                return ComponentType.ORCHESTRATOR  # Would need proper mapping
            
            def validate(self) -> bool:
                if hasattr(self._zenml_component, 'validate'):
                    return self._zenml_component.validate()
                return True
            
            def to_dict(self) -> Dict[str, Any]:
                if hasattr(self._zenml_component, 'dict'):
                    return self._zenml_component.dict()
                return {"name": self.name, "type": "zenml_wrapper"}
        
        self.register(ZenMLWrapper, name)
    
    @staticmethod
    def _class_to_snake_case(name: str) -> str:
        """Convert ClassName to class_name."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


# Global registry instance
_global_component_registry: Optional[ComponentRegistry] = None


def get_component_registry() -> ComponentRegistry:
    """Get the global component registry."""
    global _global_component_registry
    if _global_component_registry is None:
        _global_component_registry = ComponentRegistry()
    return _global_component_registry


def register_component(component_class=None, name: Optional[str] = None):
    """
    Decorator to register a custom component.
    
    Example:
        ```python
        from uniflow.stacks.plugins import register_component
        from uniflow.stacks.components import Orchestrator
        
        @register_component
        class MyCustomOrchestrator(Orchestrator):
            def run_pipeline(self, pipeline):
                # Custom logic
                pass
        
       # Or with custom name:
        @register_component(name="my_custom_name")
        class AnotherOrchestrator(Orchestrator):
            pass
        ```
    """
    def wrapper(cls):
        get_component_registry().register(cls, name)
        return cls
    
    if component_class is not None:
        # Used without arguments: @register_component
        get_component_registry().register(component_class, name)
        return component_class
    
    # Used with arguments: @register_component(name="custom")
    return wrapper


def load_component(source: str, name: Optional[str] = None):
    """
    Load a component from various sources.
    
    Args:
        source: Can be:
            - Module path: "my_package.components"
            - File path: "/path/to/component.py:ClassName"
            - ZenML component: "zenml:zenml.orchestrators.kubernetes.KubernetesOrchestrator"
        name: Optional name to register as
    """
    registry = get_component_registry()
    
    if source.startswith("zenml:"):
        # Load from ZenML
        zenml_path = source.replace("zenml:", "")
        module_path, class_name = zenml_path.rsplit(".", 1)
        
        try:
            module = importlib.import_module(module_path)
            zenml_class = getattr(module, class_name)
            registry.wrap_zenml_component(zenml_class, name or class_name)
        except ImportError as e:
            raise ImportError(
                f"Could not import ZenML component: {e}\n"
                "Install ZenML with: pip install zenml"
            )
    
    elif ":" in source:
        # Load from file
        file_path, class_name = source.split(":", 1)
        registry.load_from_path(file_path, class_name)
    
    else:
        # Load from module
        registry.load_from_module(source)

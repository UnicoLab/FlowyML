"""Plugin System for Custom Stack Components.

This module provides a robust plugin system that allows users to:
1. Discover and install plugins from various sources (PyPI, Local)
2. Manage plugin lifecycles (install, update, remove)
3. Auto-discover components via entry points
4. Seamlessly integrate components from other ecosystems via Generic Bridges
"""

import importlib
import importlib.util
import importlib.metadata
import inspect
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from uniflow.stacks.components import (
    StackComponent,
    Orchestrator,
    ArtifactStore,
    ContainerRegistry,
    ComponentType,
)
from uniflow.stacks.bridge import GenericBridge, AdaptationRule


@dataclass
class PluginInfo:
    """Metadata about a plugin."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    is_installed: bool = False
    source: str = "pypi"  # "pypi", "local", "github"
    dependencies: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)


@runtime_checkable
class PluginBridge(Protocol):
    """Protocol for plugin bridges that adapt external components."""

    def wrap_component(
        self,
        component_class: Any,
        name: str,
        config: Optional[dict[str, Any]] = None,
    ) -> type[StackComponent]:
        """Wrap an external component class into a UniFlow component."""
        ...

    def is_available(self) -> bool:
        """Check if the external system is available."""
        ...


class ComponentRegistry:
    """Registry for stack component plugins.

    Supports:
    - Auto-discovery via entry points
    - Manual registration
    - Generic Bridge system for external integrations
    - Plugin management (install/uninstall)
    """

    def __init__(self):
        self._orchestrators: dict[str, type[Orchestrator]] = {}
        self._artifact_stores: dict[str, type[ArtifactStore]] = {}
        self._container_registries: dict[str, type[ContainerRegistry]] = {}
        self._custom_components: dict[str, type[StackComponent]] = {}
        self._plugins: dict[str, PluginInfo] = {}
        self._bridges: dict[str, PluginBridge] = {}

        # Register default generic bridge
        self._register_default_bridges()

        # Auto-discover plugins
        self._discover_installed_plugins()

    def _register_default_bridges(self) -> None:
        """Register default bridges."""
        # Register a generic bridge that can handle ZenML components via rules
        zenml_rules = [
            AdaptationRule(
                source_type="zenml.orchestrators.base.BaseOrchestrator",
                target_type=ComponentType.ORCHESTRATOR,
                method_mapping={"run_pipeline": "run"},
            ),
            AdaptationRule(
                source_type="zenml.artifact_stores.base_artifact_store.BaseArtifactStore",
                target_type=ComponentType.ARTIFACT_STORE,
            ),
            AdaptationRule(
                source_type="zenml.container_registries.base_container_registry.BaseContainerRegistry",
                target_type=ComponentType.CONTAINER_REGISTRY,
            ),
            # Fallback rule for anything named *Orchestrator
            AdaptationRule(
                name_pattern=".*Orchestrator",
                target_type=ComponentType.ORCHESTRATOR,
            ),
        ]
        self.register_bridge("zenml", GenericBridge(rules=zenml_rules))

        # We can add other default bridges here (e.g. Airflow) without hard deps

    def register_bridge(self, prefix: str, bridge: PluginBridge) -> None:
        """Register a bridge for a specific URI prefix (e.g., 'zenml:', 'airflow:')."""
        self._bridges[prefix] = bridge

    def _discover_installed_plugins(self) -> None:
        """Auto-discover installed plugins via entry points."""
        try:
            # Discover UniFlow plugins
            eps = importlib.metadata.entry_points()
            if hasattr(eps, "select"):
                uniflow_eps = eps.select(group="uniflow.stack_components")
            else:
                uniflow_eps = eps.get("uniflow.stack_components", [])

            for ep in uniflow_eps:
                try:
                    component_class = ep.load()
                    self.register(component_class)

                    # Record plugin info
                    dist = importlib.metadata.distribution(ep.dist.name)
                    self._plugins[ep.dist.name] = PluginInfo(
                        name=ep.dist.name,
                        version=dist.version,
                        description=dist.metadata.get("Summary", ""),
                        author=dist.metadata.get("Author", ""),
                        is_installed=True,
                        source="pypi",
                        components=[ep.name],
                    )
                except Exception:
                    pass

            # Discover Bridges
            if hasattr(eps, "select"):
                bridge_eps = eps.select(group="uniflow.bridges")
            else:
                bridge_eps = eps.get("uniflow.bridges", [])

            for ep in bridge_eps:
                try:
                    bridge_class = ep.load()
                    self.register_bridge(ep.name, bridge_class())
                except Exception:
                    pass

        except Exception:
            # Entry points not available or error in discovery
            pass

    def register(self, component_class: type[StackComponent], name: str | None = None) -> None:
        """Register a stack component.

        Args:
            component_class: Component class to register
            name: Optional name override. If None, uses class name in snake_case
        """
        if name is None:
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

    def get_orchestrator(self, name: str) -> type[Orchestrator] | None:
        """Get orchestrator class by name."""
        return self._orchestrators.get(name)

    def get_artifact_store(self, name: str) -> type[ArtifactStore] | None:
        """Get artifact store class by name."""
        return self._artifact_stores.get(name)

    def get_container_registry(self, name: str) -> type[ContainerRegistry] | None:
        """Get container registry class by name."""
        return self._container_registries.get(name)

    def get_component(self, name: str) -> type[StackComponent] | None:
        """Get any component by name."""
        return (
            self._orchestrators.get(name)
            or self._artifact_stores.get(name)
            or self._container_registries.get(name)
            or self._custom_components.get(name)
        )

    def list_orchestrators(self) -> list[str]:
        """List all registered orchestrators."""
        return list(self._orchestrators.keys())

    def list_artifact_stores(self) -> list[str]:
        """List all registered artifact stores."""
        return list(self._artifact_stores.keys())

    def list_container_registries(self) -> list[str]:
        """List all registered container registries."""
        return list(self._container_registries.keys())

    def list_all(self) -> dict[str, list[str]]:
        """List all registered components."""
        return {
            "orchestrators": self.list_orchestrators(),
            "artifact_stores": self.list_artifact_stores(),
            "container_registries": self.list_container_registries(),
            "custom": list(self._custom_components.keys()),
        }

    def list_plugins(self) -> list[PluginInfo]:
        """List all discovered plugins."""
        return list(self._plugins.values())

    def list_bridges(self) -> list[str]:
        """List all registered bridges."""
        return list(self._bridges.keys())

    def load_from_path(self, path: str, class_name: str) -> None:
        """Load a component from a Python file."""
        spec = importlib.util.spec_from_file_location("custom_module", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        component_class = getattr(module, class_name)
        self.register(component_class)

    def load_from_module(self, module_path: str) -> None:
        """Load all components from a module."""
        module = importlib.import_module(module_path)

        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, StackComponent) and obj != StackComponent:
                self.register(obj)

    def load_via_bridge(self, bridge_name: str, component_path: str, name: str | None = None) -> None:
        """Load a component via a registered bridge."""
        bridge = self._bridges.get(bridge_name)
        if not bridge:
            raise ValueError(f"Bridge '{bridge_name}' not found. Available: {list(self._bridges.keys())}")

        module_path, class_name = component_path.rsplit(".", 1)

        try:
            module = importlib.import_module(module_path)
            component_class = getattr(module, class_name)

            wrapper = bridge.wrap_component(component_class, name or class_name)
            self.register(wrapper, name or class_name)
        except ImportError as e:
            raise ImportError(f"Could not import component via {bridge_name}: {e}")

    def load_plugins_from_config(self, config_path: str) -> None:
        """Load plugins from a configuration file."""
        from uniflow.stacks.plugin_config import PluginManager

        manager = PluginManager()
        manager.load_from_yaml(config_path)

        # Get generic bridge (or create one if not exists)
        bridge = self._bridges.get("zenml")  # Use the default generic bridge
        if not bridge or not isinstance(bridge, GenericBridge):
            # Create a fresh generic bridge if needed
            bridge = GenericBridge()
            self.register_bridge("generic", bridge)

        # Register components from config
        for config in manager.configs:
            # Create specific rule for this component
            # Note: In a real implementation, we might want to merge rules or handle them more globally
            # For now, we'll just use the bridge to wrap it

            try:
                # Import the source class
                module_path, class_name = config.source.rsplit(".", 1)
                module = importlib.import_module(module_path)
                component_class = getattr(module, class_name)

                # Create rule from config
                # We need to add this rule to the bridge so it knows how to handle it
                # Or we can pass the rule directly to wrap_component if we modify GenericBridge
                # But GenericBridge uses internal rules.
                # Let's add the rule to the bridge

                # Convert config to rule (simplified)
                target_type = ComponentType.ORCHESTRATOR
                if config.component_type == "artifact_store":
                    target_type = ComponentType.ARTIFACT_STORE
                elif config.component_type == "container_registry":
                    target_type = ComponentType.CONTAINER_REGISTRY

                rule = AdaptationRule(
                    source_type=config.source,
                    target_type=target_type,
                    method_mapping=config.adaptation.get("method_mapping", {}),
                    attribute_mapping=config.adaptation.get("attribute_mapping", {}),
                )

                # Add rule to bridge
                if isinstance(bridge, GenericBridge):
                    bridge.rules.append(rule)

                # Wrap and register
                wrapper = bridge.wrap_component(component_class, config.name)
                self.register(wrapper, config.name)

            except Exception as e:
                print(f"Failed to load plugin {config.name}: {e}")

    def install_plugin(self, package_name: str) -> bool:
        """Install a plugin package via pip."""
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            # Refresh discovery
            importlib.invalidate_caches()
            self._discover_installed_plugins()
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def _class_to_snake_case(name: str) -> str:
        """Convert ClassName to class_name."""
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# Global registry instance
_global_component_registry: ComponentRegistry | None = None


def get_component_registry() -> ComponentRegistry:
    """Get the global component registry."""
    global _global_component_registry
    if _global_component_registry is None:
        _global_component_registry = ComponentRegistry()
    return _global_component_registry


def register_component(component_class=None, name: str | None = None):
    """Decorator to register a custom component."""

    def wrapper(cls):
        get_component_registry().register(cls, name)
        return cls

    if component_class is not None:
        get_component_registry().register(component_class, name)
        return component_class

    return wrapper


def load_component(source: str, name: str | None = None) -> None:
    """Load a component from various sources.

    Args:
        source: Can be:
            - Module path: "my_package.components"
            - File path: "/path/to/component.py:ClassName"
            - Bridge URI: "zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator"
            - Bridge URI: "airflow:airflow.providers.google.cloud.operators.bigquery.BigQueryExecuteQueryOperator"
        name: Optional name to register as
    """
    registry = get_component_registry()

    # Check for bridge prefixes (e.g., "zenml:", "airflow:")
    if ":" in source and not source.startswith("/") and not source.startswith("."):
        prefix, path = source.split(":", 1)

        # If prefix is a registered bridge, use it
        if prefix in registry.list_bridges():
            registry.load_via_bridge(prefix, path, name)
            return

        # Special case for file paths that might look like "c:/path" on windows or just "file:Class"
        # But here we assume "file_path:ClassName" for local loading
        if ".py" in prefix:
            registry.load_from_path(prefix, path)
            return

    # Fallback to module load
    registry.load_from_module(source)

"""Unit tests for the UniFlow plugin system."""

import pytest
from unittest.mock import MagicMock, patch, Mock
import sys
from typing import Any, Dict, Optional, Type

from uniflow.stacks.plugins import (
    ComponentRegistry,
    PluginInfo,
    PluginBridge,
    load_component,
    get_component_registry,
)
from uniflow.stacks.bridge import GenericBridge
from uniflow.stacks.components import StackComponent, ComponentType


class MockBridge:
    """Mock bridge for testing."""

    def __init__(self):
        self.wrap_called = False

    def is_available(self) -> bool:
        return True

    def wrap_component(
        self,
        component_class: Any,
        name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Type[StackComponent]:
        self.wrap_called = True

        # Return a mock component class
        from uniflow.stacks.components import Orchestrator

        class MockWrapper(Orchestrator):
            def __init__(self, **kwargs):
                super().__init__(name)

            @property
            def component_type(self):
                return ComponentType.ORCHESTRATOR

            def validate(self):
                return True

            def to_dict(self):
                return {"name": name}

            def run_pipeline(self, pipeline, **kwargs):
                pass

            def get_run_status(self, run_id):
                return "success"

        return MockWrapper


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    # Reset global registry
    import uniflow.stacks.plugins

    uniflow.stacks.plugins._global_component_registry = None
    return get_component_registry()


def test_registry_initialization(registry):
    """Test registry initialization."""
    assert registry is not None
    assert isinstance(registry._orchestrators, dict)
    assert isinstance(registry._bridges, dict)

    # Check default bridges (zenml should be registered via GenericBridge)
    assert "zenml" in registry.list_bridges()

    # Verify it's a GenericBridge
    bridge = registry._bridges["zenml"]
    assert isinstance(bridge, GenericBridge)
    assert len(bridge.rules) > 0


def test_register_bridge(registry):
    """Test registering a custom bridge."""
    mock_bridge = MockBridge()
    registry.register_bridge("mock", mock_bridge)

    assert "mock" in registry.list_bridges()
    assert registry._bridges["mock"] == mock_bridge


def test_load_via_bridge(registry):
    """Test loading a component via a bridge."""
    mock_bridge = MockBridge()
    registry.register_bridge("mock", mock_bridge)

    # Mock importlib to simulate external module
    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_class = MagicMock()
        mock_module.MockClass = mock_class
        mock_import.return_value = mock_module

        # Load via bridge
        registry.load_via_bridge("mock", "external.module.MockClass", "my_component")

        # Verify bridge was called
        assert mock_bridge.wrap_called

        # Verify component was registered
        assert "my_component" in registry.list_orchestrators()


def test_load_component_helper():
    """Test the global load_component helper."""
    # Reset registry
    import uniflow.stacks.plugins

    uniflow.stacks.plugins._global_component_registry = None
    registry = get_component_registry()

    mock_bridge = MockBridge()
    registry.register_bridge("mock", mock_bridge)

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_class = MagicMock()
        mock_module.MockClass = mock_class
        mock_import.return_value = mock_module

        # Test loading with prefix
        load_component("mock:external.module.MockClass", "test_comp")

        assert mock_bridge.wrap_called
        assert "test_comp" in registry.list_orchestrators()


def test_plugin_discovery():
    """Test plugin discovery via entry points."""

    # Mock entry point
    mock_ep = MagicMock()
    mock_ep.name = "test-plugin"
    mock_ep.dist.name = "test-plugin-dist"
    mock_ep.load.return_value = MagicMock  # Component class

    # Mock distribution
    mock_dist = MagicMock()
    mock_dist.version = "1.0.0"
    mock_dist.metadata = {"Summary": "Test Plugin", "Author": "Tester"}

    with patch("importlib.metadata.entry_points") as mock_eps:
        with patch("importlib.metadata.distribution") as mock_get_dist:
            # Setup mocks
            mock_eps.return_value.select.return_value = [mock_ep]
            mock_get_dist.return_value = mock_dist

            # Create new registry to trigger discovery
            registry = ComponentRegistry()

            # Verify plugin info
            plugins = registry.list_plugins()
            assert len(plugins) >= 1

            plugin = next((p for p in plugins if p.name == "test-plugin-dist"), None)
            assert plugin is not None
            assert plugin.version == "1.0.0"
            assert plugin.is_installed

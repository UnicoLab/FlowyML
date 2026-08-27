"""Unit tests for loading plugin configurations."""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import sys
from typing import Any

from flowyml.stacks.plugins import get_component_registry, ComponentRegistry
from flowyml.stacks.components import ComponentType, Orchestrator


# Mock external component
class ConfigurableOrchestrator:
    def __init__(self, **kwargs):
        self.config = kwargs

    def run(self, pipeline, **kwargs):
        return "config_run"


@pytest.fixture
def registry():
    import flowyml.stacks.plugins

    previous = flowyml.stacks.plugins._global_component_registry
    flowyml.stacks.plugins._global_component_registry = None
    try:
        yield get_component_registry()
    finally:
        # Restore the process-wide registry so this test cannot leak a rebuilt
        # instance into unrelated tests running in the same worker.
        flowyml.stacks.plugins._global_component_registry = previous


def test_load_plugins_from_yaml(registry):
    """Test loading plugins from a YAML file."""

    yaml_content = """
plugins:
  - name: my_custom_orch
    source: external.module.ConfigurableOrchestrator
    type: orchestrator
    adaptation:
      method_mapping:
        run_pipeline: run
"""

    with patch("builtins.open", mock_open(read_data=yaml_content)):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("importlib.import_module") as mock_import:
                # Setup mock module
                mock_module = MagicMock()
                mock_module.ConfigurableOrchestrator = ConfigurableOrchestrator
                mock_import.return_value = mock_module

                # Load config
                registry.load_plugins_from_config("dummy_config.yaml")

                # Verify registration
                orch = registry.get_orchestrator("my_custom_orch")
                assert orch is not None

                # Verify wrapper functionality
                instance = orch(param="test")
                assert isinstance(instance, Orchestrator)
                assert instance.run_pipeline("pipe") == "config_run"


def test_load_plugins_invalid_config(registry):
    """An unusable config must register nothing and must not raise.

    Asserted as a *delta* rather than an absolute count: a freshly built
    registry legitimately carries built-in flavors and any cloud components
    already registered in this process, and that baseline varies with import
    order across test workers.
    """
    before = set(registry.list_orchestrators())

    with patch("builtins.open", mock_open(read_data="invalid: yaml")):
        with patch("pathlib.Path.exists", return_value=True):
            # Should not raise exception, just log error
            registry.load_plugins_from_config("bad.yaml")

    assert set(registry.list_orchestrators()) == before

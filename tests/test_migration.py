"""Unit tests for stack migration."""

import pytest
from unittest.mock import MagicMock, patch
import sys

from uniflow.stacks.migration import StackMigrator


# Mock ZenML classes
class MockZenMLComponent:
    def __init__(self, name, type, config):
        self.name = name
        self.type = type
        self.configuration = config


class MockZenMLStack:
    def __init__(self, name, components):
        self.name = name
        self.components = components


@pytest.fixture
def mock_zenml_client():
    with patch.dict(sys.modules, {"zenml.client": MagicMock()}):
        mock_client = MagicMock()
        sys.modules["zenml.client"].Client.return_value = mock_client
        yield mock_client


def test_migrate_zenml_stack(mock_zenml_client):
    """Test migrating a ZenML stack."""
    # Setup mock stack
    orch = MockZenMLComponent("my_orch", "orchestrator", {"param": "val"})
    store = MockZenMLComponent("my_store", "artifact_store", {"uri": "s3://"})

    stack = MockZenMLStack(
        "test_stack",
        {
            "orchestrator": orch,
            "artifact_store": store,
        },
    )

    mock_zenml_client.get_stack.return_value = stack

    # Run migration
    migrator = StackMigrator()
    data = migrator.migrate_zenml_stack("test_stack")

    # Verify results
    assert data["stack"]["name"] == "test_stack"
    assert len(data["plugins"]) == 2

    # Verify orchestrator plugin
    orch_plugin = next(p for p in data["plugins"] if "orchestrator" in p["type"])
    assert orch_plugin["name"] == "zenml_my_orch"
    assert orch_plugin["adaptation"]["method_mapping"]["run_pipeline"] == "run"

    # Verify YAML generation
    yaml_out = migrator.generate_yaml(data)
    assert "plugins:" in yaml_out
    assert "zenml_my_orch" in yaml_out
    assert "test_stack" in yaml_out


def test_migrate_zenml_not_installed():
    """Test error when ZenML is not installed."""
    with patch.dict(sys.modules):
        if "zenml.client" in sys.modules:
            del sys.modules["zenml.client"]

        migrator = StackMigrator()
        # Ensure import fails
        with patch.dict(sys.modules, {"zenml.client": None}):
            with pytest.raises(ImportError):
                migrator.migrate_zenml_stack("stack")

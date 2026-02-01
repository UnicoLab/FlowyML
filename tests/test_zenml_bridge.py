"""Tests for ZenML Bridge integration.

Tests the ZenMLBridge class for automatic discovery and wrapping
of ZenML components.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Any

from flowyml.stacks.components import (
    Orchestrator,
    ArtifactStore,
    ContainerRegistry,
    ComponentType,
)


class MockZenMLOrchestrator:
    """Mock ZenML orchestrator for testing."""

    def __init__(self, **kwargs):
        self.config = kwargs

    def run(self, pipeline, **kwargs):
        return {"status": "success", "run_id": "mock-run-123"}

    def dict(self):
        return {"type": "mock_orchestrator", **self.config}


class MockZenMLArtifactStore:
    """Mock ZenML artifact store for testing."""

    def __init__(self, path: str = "/tmp", **kwargs):
        self.path = path

    def copyfile(self, src, dst):
        return dst

    def open(self, path):
        return f"content of {path}"

    def exists(self, path):
        return True

    def dict(self):
        return {"type": "mock_artifact_store", "path": self.path}


class TestZenMLBridge(unittest.TestCase):
    """Test ZenML bridge functionality."""

    def test_bridge_creation_without_zenml(self):
        """Test that bridge handles missing ZenML gracefully."""
        with patch.dict("sys.modules", {"zenml": None}):
            from flowyml.stacks.zenml_bridge import ZenMLBridge

            bridge = ZenMLBridge(auto_discover=False)

            # Should not crash, just report unavailable
            self.assertFalse(bridge.is_available())

    def test_wrap_orchestrator(self):
        """Test wrapping a mock orchestrator."""
        from flowyml.stacks.zenml_bridge import ZenMLBridge

        bridge = ZenMLBridge(auto_discover=False)

        # Wrap the mock orchestrator
        wrapped_class = bridge._create_orchestrator_wrapper_from_class(
            MockZenMLOrchestrator,
            "mock_orch",
        )

        # Verify it's a proper Orchestrator subclass
        self.assertTrue(issubclass(wrapped_class, Orchestrator))

        # Create an instance
        instance = wrapped_class(region="us-west-2")

        # Verify component type
        self.assertEqual(instance.component_type, ComponentType.ORCHESTRATOR)

        # Verify run_pipeline works
        result = instance.run_pipeline(None, run_id="test-run")
        self.assertEqual(result["status"], "success")

    def test_wrap_artifact_store(self):
        """Test wrapping a mock artifact store."""
        from flowyml.stacks.zenml_bridge import ZenMLBridge

        bridge = ZenMLBridge(auto_discover=False)

        wrapped_class = bridge._create_artifact_store_wrapper_from_class(
            MockZenMLArtifactStore,
            "mock_store",
        )

        self.assertTrue(issubclass(wrapped_class, ArtifactStore))

        instance = wrapped_class(path="/data")

        self.assertEqual(instance.component_type, ComponentType.ARTIFACT_STORE)
        self.assertTrue(instance.exists("/some/path"))

    def test_infer_component_type(self):
        """Test component type inference from class names."""
        from flowyml.stacks.zenml_bridge import ZenMLBridge

        bridge = ZenMLBridge(auto_discover=False)

        class KubernetesOrchestrator:
            pass

        class S3ArtifactStore:
            pass

        class ECRContainerRegistry:
            pass

        class MLFlowExperimentTracker:
            pass

        self.assertEqual(
            bridge._infer_component_type(KubernetesOrchestrator),
            ComponentType.ORCHESTRATOR,
        )
        self.assertEqual(
            bridge._infer_component_type(S3ArtifactStore),
            ComponentType.ARTIFACT_STORE,
        )
        self.assertEqual(
            bridge._infer_component_type(ECRContainerRegistry),
            ComponentType.CONTAINER_REGISTRY,
        )
        # Generic types default to EXECUTOR
        self.assertEqual(
            bridge._infer_component_type(MLFlowExperimentTracker),
            ComponentType.EXECUTOR,
        )

    def test_wrap_component_protocol(self):
        """Test that wrap_component follows the PluginBridge protocol."""
        from flowyml.stacks.zenml_bridge import ZenMLBridge

        bridge = ZenMLBridge(auto_discover=False)

        # wrap_component should work for any class
        wrapped = bridge.wrap_component(MockZenMLOrchestrator, "test_orch")

        self.assertTrue(issubclass(wrapped, Orchestrator))
        self.assertEqual(wrapped.__name__, "ZenMLMockZenMLOrchestratorWrapper")


class TestComponentRegistryZenMLMethods(unittest.TestCase):
    """Test ZenML methods on ComponentRegistry."""

    def test_list_zenml_integrations_without_zenml(self):
        """Test that listing returns empty when ZenML is not installed."""
        from flowyml.stacks.plugins import ComponentRegistry

        registry = ComponentRegistry()

        # Should return empty list, not crash
        integrations = registry.list_zenml_integrations()
        self.assertIsInstance(integrations, list)

    def test_import_all_zenml_without_zenml(self):
        """Test that import_all returns empty when ZenML is not installed."""
        from flowyml.stacks.plugins import ComponentRegistry

        registry = ComponentRegistry()

        # Should return empty dict, not crash
        result = registry.import_all_zenml()
        self.assertIsInstance(result, dict)


class TestZenMLFlavorInfo(unittest.TestCase):
    """Test ZenMLFlavorInfo dataclass."""

    def test_flavor_info_creation(self):
        """Test creating a flavor info object."""
        from flowyml.stacks.zenml_bridge import ZenMLFlavorInfo, ZenMLComponentType

        flavor = ZenMLFlavorInfo(
            name="mlflow",
            integration="mlflow",
            component_type=ZenMLComponentType.EXPERIMENT_TRACKER,
            flavor_class="zenml.integrations.mlflow.flavors.MLFlowExperimentTrackerFlavor",
            config_class="MLFlowExperimentTrackerConfig",
            implementation_class="zenml.integrations.mlflow.experiment_trackers.MLFlowExperimentTracker",
            is_available=True,
        )

        self.assertEqual(flavor.name, "mlflow")
        self.assertEqual(flavor.integration, "mlflow")
        self.assertTrue(flavor.is_available)


class TestZenMLIntegrationInfo(unittest.TestCase):
    """Test ZenMLIntegrationInfo dataclass."""

    def test_integration_info_creation(self):
        """Test creating an integration info object."""
        from flowyml.stacks.zenml_bridge import ZenMLIntegrationInfo

        integration = ZenMLIntegrationInfo(
            name="aws",
            requirements=["boto3", "sagemaker"],
            is_installed=True,
        )

        self.assertEqual(integration.name, "aws")
        self.assertEqual(len(integration.requirements), 2)
        self.assertTrue(integration.is_installed)


if __name__ == "__main__":
    unittest.main()

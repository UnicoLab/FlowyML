"""
Tests for plugin system and component registry.

Tests component registration, loading, and discovery.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict

from uniflow.stacks.components import (
    Orchestrator,
    ArtifactStore,
    ContainerRegistry,
    ComponentType,
    ResourceConfig,
    DockerConfig,
)
from uniflow.stacks.plugins import (
    ComponentRegistry,
    get_component_registry,
    register_component,
    load_component,
)


class TestComponentRegistry(unittest.TestCase):
    """Test component registry functionality."""

    def setUp(self):
        """Create fresh registry for each test."""
        self.registry = ComponentRegistry()

    def test_register_orchestrator(self):
        """Test registering an orchestrator component."""

        class TestOrchestrator(Orchestrator):
            def validate(self):
                return True

            def run_pipeline(self, pipeline, **kwargs):
                return "test_run"

            def get_run_status(self, run_id):
                return "SUCCESS"

            def to_dict(self):
                return {"type": "test"}

        self.registry.register(TestOrchestrator, "test_orch")

        self.assertIn("test_orch", self.registry.list_orchestrators())

    def test_register_artifact_store(self):
        """Test registering an artifact store component."""

        class TestArtifactStore(ArtifactStore):
            def validate(self):
                return True

            def save(self, artifact, path):
                return f"saved:{path}"

            def load(self, path):
                return f"loaded:{path}"

            def exists(self, path):
                return True

            def to_dict(self):
                return {"type": "test"}

        self.registry.register(TestArtifactStore, "test_store")

        self.assertIn("test_store", self.registry.list_artifact_stores())

    def test_register_container_registry(self):
        """Test registering a container registry component."""

        class TestContainerRegistry(ContainerRegistry):
            def validate(self):
                return True

            def push_image(self, image_name, tag="latest"):
                return f"{image_name}:{tag}"

            def pull_image(self, image_name, tag="latest"):
                pass

            def get_image_uri(self, image_name, tag="latest"):
                return f"reg/{image_name}:{tag}"

            def to_dict(self):
                return {"type": "test"}

        self.registry.register(TestContainerRegistry, "test_registry")

        self.assertIn("test_registry", self.registry.list_container_registries())

    def test_get_component(self):
        """Test retrieving registered components."""

        class TestOrchestrator(Orchestrator):
            def validate(self):
                return True

            def run_pipeline(self, pipeline, **kwargs):
                return "test"

            def get_run_status(self, run_id):
                return "SUCCESS"

            def to_dict(self):
                return {}

        self.registry.register(TestOrchestrator, "getter_test")
        component = self.registry.get_orchestrator("getter_test")

        self.assertEqual(component, TestOrchestrator)

    def test_list_all_components(self):
        """Test listing all registered components."""
        all_components = self.registry.list_all()

        self.assertIn("orchestrators", all_components)
        self.assertIn("artifact_stores", all_components)
        self.assertIn("container_registries", all_components)

    def test_snake_case_conversion(self):
        """Test class name to snake_case conversion."""

        class MyCustomOrchestrator(Orchestrator):
            def validate(self):
                return True

            def run_pipeline(self, pipeline, **kwargs):
                return "test"

            def get_run_status(self, run_id):
                return "SUCCESS"

            def to_dict(self):
                return {}

        # Register without explicit name
        self.registry.register(MyCustomOrchestrator)

        # Should be registered as my_custom_orchestrator
        self.assertIn("my_custom_orchestrator", self.registry.list_orchestrators())


class TestRegisterDecorator(unittest.TestCase):
    """Test @register_component decorator."""

    def setUp(self):
        """Get global registry."""
        self.registry = get_component_registry()
        # Note: Global registry persists between tests

    def test_decorator_auto_registers(self):
        """Test that decorator automatically registers component."""

        @register_component
        class DecoratedOrchestrator(Orchestrator):
            def validate(self):
                return True

            def run_pipeline(self, pipeline, **kwargs):
                return "decorated"

            def get_run_status(self, run_id):
                return "SUCCESS"

            def to_dict(self):
                return {"type": "decorated"}

        # Should be auto-registered
        all_orcestrators = self.registry.list_orchestrators()
        self.assertIn("decorated_orchestrator", all_orcestrators)

    def test_decorator_with_custom_name(self):
        """Test decorator with custom name."""

        @register_component(name="my_custom_name")
        class AnotherOrchestrator(Orchestrator):
            def validate(self):
                return True

            def run_pipeline(self, pipeline, **kwargs):
                return "custom"

            def get_run_status(self, run_id):
                return "SUCCESS"

            def to_dict(self):
                return {}

        self.assertIn("my_custom_name", self.registry.list_orchestrators())


class TestComponentValidation(unittest.TestCase):
    """Test component validation."""

    def test_orchestrator_validation(self):
        """Test orchestrator validation."""

        class ValidatingOrchestrator(Orchestrator):
            def __init__(self, config_value):
                super().__init__("validator")
                self.config_value = config_value

            def validate(self):
                if not self.config_value:
                    raise ValueError("config_value is required")
                return True

            def run_pipeline(self, pipeline, **kwargs):
                return "test"

            def get_run_status(self, run_id):
                return "SUCCESS"

            def to_dict(self):
                return {"config": self.config_value}

        # Valid configuration
        valid_orch = ValidatingOrchestrator("valid")
        self.assertTrue(valid_orch.validate())

        # Invalid configuration
        invalid_orch = ValidatingOrchestrator(None)
        with self.assertRaises(ValueError):
            invalid_orch.validate()

    def test_artifact_store_validation(self):
        """Test artifact store validation."""

        class ValidatingStore(ArtifactStore):
            def __init__(self, endpoint):
                super().__init__("validator")
                self.endpoint = endpoint

            def validate(self):
                if not self.endpoint:
                    raise ValueError("endpoint is required")
                return True

            def save(self, artifact, path):
                return path

            def load(self, path):
                return None

            def exists(self, path):
                return False

            def to_dict(self):
                return {"endpoint": self.endpoint}

        valid_store = ValidatingStore("http://localhost:9000")
        self.assertTrue(valid_store.validate())

        invalid_store = ValidatingStore(None)
        with self.assertRaises(ValueError):
            invalid_store.validate()


class TestComponentSerialization(unittest.TestCase):
    """Test component serialization."""

    def test_orchestrator_to_dict(self):
        """Test orchestrator serialization."""

        class SerializableOrchestrator(Orchestrator):
            def __init__(self):
                super().__init__("serializable")
                self.config = {"key": "value"}

            def validate(self):
                return True

            def run_pipeline(self, pipeline, **kwargs):
                return "test"

            def get_run_status(self, run_id):
                return "SUCCESS"

            def to_dict(self):
                return {
                    "type": "serializable",
                    "name": self.name,
                    "config": self.config,
                }

        orch = SerializableOrchestrator()
        serialized = orch.to_dict()

        self.assertEqual(serialized["type"], "serializable")
        self.assertEqual(serialized["name"], "serializable")
        self.assertIn("config", serialized)

    def test_artifact_store_to_dict(self):
        """Test artifact store serialization."""

        class SerializableStore(ArtifactStore):
            def __init__(self, bucket):
                super().__init__("serializable")
                self.bucket = bucket

            def validate(self):
                return True

            def save(self, artifact, path):
                return path

            def load(self, path):
                return None

            def exists(self, path):
                return False

            def to_dict(self):
                return {
                    "type": "test_store",
                    "bucket": self.bucket,
                }

        store = SerializableStore("my-bucket")
        serialized = store.to_dict()

        self.assertEqual(serialized["bucket"], "my-bucket")


class TestDynamicComponentLoading(unittest.TestCase):
    """Test dynamic component loading."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.registry = ComponentRegistry()

    def test_load_from_file(self):
        """Test loading component from file."""
        # Create a test component file
        component_file = Path(self.test_dir) / "test_component.py"
        component_file.write_text(
            """
from uniflow.stacks.components import Orchestrator

class FileOrchestrator(Orchestrator):
    def validate(self): return True
    def run_pipeline(self, pipeline, **kwargs): return "from_file"
    def get_run_status(self, run_id): return "SUCCESS"
    def to_dict(self): return {"type": "file"}
""",
        )

        # Load component
        self.registry.load_from_path(str(component_file), "FileOrchestrator")

        # Verify it's registered
        self.assertIn("file_orchestrator", self.registry.list_orchestrators())


class TestGlobalRegistry(unittest.TestCase):
    """Test global registry functionality."""

    def test_get_global_registry(self):
        """Test getting global registry instance."""
        registry1 = get_component_registry()
        registry2 = get_component_registry()

        # Should be same instance
        self.assertIs(registry1, registry2)

    def test_global_registry_persistence(self):
        """Test that components persist in global registry."""

        @register_component
        class PersistentOrchestrator(Orchestrator):
            def validate(self):
                return True

            def run_pipeline(self, pipeline, **kwargs):
                return "persistent"

            def get_run_status(self, run_id):
                return "SUCCESS"

            def to_dict(self):
                return {}

        # Get registry again
        registry = get_component_registry()

        # Component should still be there
        self.assertIn("persistent_orchestrator", registry.list_orchestrators())


if __name__ == "__main__":
    unittest.main()

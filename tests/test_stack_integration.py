"""
Tests for stack integration with pipelines.

Tests that pipelines correctly use stacks, resources, and configurations.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

from uniflow import Pipeline, step
from uniflow.stacks import LocalStack
from uniflow.stacks.components import ResourceConfig, DockerConfig
from uniflow.stacks.registry import StackRegistry, get_registry


class TestStackIntegration(unittest.TestCase):
    """Test stack integration with pipelines."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

        # Clear global registry
        get_registry().clear()

    def test_pipeline_with_local_stack(self):
        """Test pipeline execution with local stack."""
        stack = LocalStack(
            name="test_local",
            artifact_path=f"{self.test_dir}/artifacts",
            metadata_path=f"{self.test_dir}/metadata.db",
        )

        @step
        def add_one(x: int):
            return {"result": x + 1}

        pipeline = Pipeline("test_pipeline", stack=stack)
        pipeline.add_step(add_one)

        result = pipeline.run(context={"x": 5})

        self.assertIsNotNone(result)
        self.assertEqual(pipeline.stack, stack)

    def test_pipeline_with_stack_registry(self):
        """Test pipeline uses stack from registry."""
        stack = LocalStack(name="registered")

        registry = get_registry()
        registry.register_stack(stack, set_active=True)

        @step
        def process():
            return {"data": "processed"}

        pipeline = Pipeline("test_pipeline")
        pipeline.add_step(process)

        # Pipeline should use active stack from registry
        result = pipeline.run()

        self.assertIsNotNone(result)

    def test_pipeline_validates_stack(self):
        """Test pipeline validates stack before execution."""
        stack = LocalStack(name="validation_test")

        @step
        def dummy():
            return {}

        pipeline = Pipeline("test", stack=stack)
        pipeline.add_step(dummy)

        # Should validate successfully
        self.assertTrue(stack.validate())

    def test_multiple_stacks_same_pipeline(self):
        """Test running same pipeline on different stacks."""
        stack1 = LocalStack(
            name="stack1",
            artifact_path=f"{self.test_dir}/stack1",
        )
        stack2 = LocalStack(
            name="stack2",
            artifact_path=f"{self.test_dir}/stack2",
        )

        @step
        def compute(value: int):
            return {"result": value * 2}

        pipeline = Pipeline("multi_stack_test")
        pipeline.add_step(compute)

        # Run on stack1
        result1 = pipeline.run(stack=stack1, context={"value": 5})
        self.assertIsNotNone(result1)

        # Run on stack2
        result2 = pipeline.run(stack=stack2, context={"value": 10})
        self.assertIsNotNone(result2)


class TestResourceConfiguration(unittest.TestCase):
    """Test resource configuration with pipelines."""

    def test_resource_config_creation(self):
        """Test creating resource configurations."""
        config = ResourceConfig(
            cpu="4",
            memory="16Gi",
            gpu="nvidia-tesla-t4",
            gpu_count=2,
        )

        self.assertEqual(config.cpu, "4")
        self.assertEqual(config.memory, "16Gi")
        self.assertEqual(config.gpu, "nvidia-tesla-t4")
        self.assertEqual(config.gpu_count, 2)

    def test_resource_config_to_dict(self):
        """Test resource config serialization."""
        config = ResourceConfig(cpu="8", memory="32Gi")
        config_dict = config.to_dict()

        self.assertIn("cpu", config_dict)
        self.assertIn("memory", config_dict)
        self.assertEqual(config_dict["cpu"], "8")

    def test_default_resources(self):
        """Test default resource values."""
        config = ResourceConfig()

        self.assertEqual(config.cpu, "1")
        self.assertEqual(config.memory, "2Gi")
        self.assertEqual(config.gpu_count, 0)


class TestDockerConfiguration(unittest.TestCase):
    """Test Docker configuration."""

    def test_docker_config_with_image(self):
        """Test Docker config with pre-built image."""
        config = DockerConfig(image="gcr.io/project/image:v1")

        self.assertEqual(config.image, "gcr.io/project/image:v1")
        self.assertIsNone(config.dockerfile)

    def test_docker_config_with_dockerfile(self):
        """Test Docker config with Dockerfile."""
        config = DockerConfig(
            dockerfile="./Dockerfile",
            build_context=".",
        )

        self.assertEqual(config.dockerfile, "./Dockerfile")
        self.assertEqual(config.build_context, ".")

    def test_docker_config_with_requirements(self):
        """Test Docker config with requirements list."""
        config = DockerConfig(
            requirements=["tensorflow>=2.12.0", "pandas>=2.0.0"],
        )

        self.assertIn("tensorflow>=2.12.0", config.requirements)
        self.assertEqual(len(config.requirements), 2)

    def test_docker_config_env_vars(self):
        """Test Docker config environment variables."""
        config = DockerConfig(
            env_vars={"PYTHONUNBUFFERED": "1", "DEBUG": "false"},
        )

        self.assertEqual(config.env_vars["PYTHONUNBUFFERED"], "1")
        self.assertEqual(len(config.env_vars), 2)

    def test_docker_config_to_dict(self):
        """Test Docker config serialization."""
        config = DockerConfig(
            image="test:latest",
            env_vars={"KEY": "value"},
        )
        config_dict = config.to_dict()

        self.assertIn("image", config_dict)
        self.assertIn("env_vars", config_dict)


class TestStackRegistry(unittest.TestCase):
    """Test stack registry functionality."""

    def setUp(self):
        """Clear registry before each test."""
        get_registry().clear()

    def test_register_stack(self):
        """Test registering a stack."""
        registry = get_registry()
        stack = LocalStack(name="test")

        registry.register_stack(stack)

        self.assertIn("test", registry.list_stacks())

    def test_get_stack(self):
        """Test retrieving a registered stack."""
        registry = get_registry()
        stack = LocalStack(name="retrieve_test")

        registry.register_stack(stack)
        retrieved = registry.get_stack("retrieve_test")

        self.assertEqual(retrieved, stack)

    def test_set_active_stack(self):
        """Test setting active stack."""
        registry = get_registry()

        stack1 = LocalStack(name="stack1")
        stack2 = LocalStack(name="stack2")

        registry.register_stack(stack1)
        registry.register_stack(stack2)

        registry.set_active_stack("stack2")
        active = registry.get_active_stack()

        self.assertEqual(active, stack2)

    def test_unregister_stack(self):
        """Test removing a stack from registry."""
        registry = get_registry()
        stack = LocalStack(name="removable")

        registry.register_stack(stack)
        self.assertIn("removable", registry.list_stacks())

        registry.unregister_stack("removable")
        self.assertNotIn("removable", registry.list_stacks())

    def test_describe_stack(self):
        """Test getting stack description."""
        registry = get_registry()
        stack = LocalStack(name="describable")

        registry.register_stack(stack, set_active=True)
        description = registry.describe_stack("describable")

        self.assertIn("name", description)
        self.assertIn("is_active", description)
        self.assertTrue(description["is_active"])


class TestPipelineStackIntegration(unittest.TestCase):
    """Integration tests for pipeline and stack interaction."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        get_registry().clear()

    def test_end_to_end_pipeline_with_stack(self):
        """Test complete pipeline execution with stack."""
        # Create stack
        stack = LocalStack(
            name="e2e_test",
            artifact_path=f"{self.test_dir}/artifacts",
            metadata_path=f"{self.test_dir}/metadata.db",
        )

        # Define pipeline
        @step
        def load_data(path: str):
            return {"data": f"loaded from {path}"}

        @step
        def process_data(data_dict: dict):
            return {"processed": data_dict["data"].upper()}

        @step
        def save_results(processed: dict):
            return {"saved": True, "data": processed["processed"]}

        # Create and run pipeline
        pipeline = Pipeline("e2e_pipeline", stack=stack)
        pipeline.add_step(load_data)
        pipeline.add_step(process_data)
        pipeline.add_step(save_results)

        result = pipeline.run(context={"path": "/data/test.csv"})

        # Verify execution
        self.assertIsNotNone(result)

        # Verify artifacts were stored
        artifact_path = Path(f"{self.test_dir}/artifacts")
        self.assertTrue(artifact_path.exists())

    def test_pipeline_respects_resource_config(self):
        """Test that pipeline respects resource configuration."""
        stack = LocalStack(name="resource_test")
        resources = ResourceConfig(cpu="8", memory="32Gi")

        @step
        def resource_heavy_task():
            return {"completed": True}

        pipeline = Pipeline("resource_pipeline", stack=stack)
        pipeline.add_step(resource_heavy_task)

        # This should work even though we don't use resources locally
        result = pipeline.run(resources=resources)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()

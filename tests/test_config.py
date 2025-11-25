"""
Tests for configuration system.

Tests YAML configuration loading, environment variable expansion,
and stack creation from configuration.
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path

from uniflow.utils.stack_config import (
    ConfigLoader,
    load_config,
    create_stack_from_config,
    create_resource_config_from_dict,
    create_docker_config_from_dict,
)
from uniflow.stacks.components import ResourceConfig, DockerConfig


class TestConfigLoader(unittest.TestCase):
    """Test configuration loading."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
    
    def test_load_basic_config(self):
        """Test loading basic configuration."""
        config_path = Path(self.test_dir) / "uniflow.yaml"
        config_path.write_text("""
stacks:
  local:
    type: local
    artifact_store:
      path: .uniflow/artifacts

default_stack: local
""")
        
        loader = ConfigLoader(str(config_path))
        config = loader.load()
        
        self.assertIn("local", config.stacks)
        self.assertEqual(config.default_stack, "local")
    
    def test_environment_variable_expansion(self):
        """Test environment variable expansion."""
        os.environ["TEST_PROJECT_ID"] = "test-project"
        os.environ["TEST_BUCKET"] = "test-bucket"
        
        config_path = Path(self.test_dir) / "uniflow.yaml"
        config_path.write_text("""
stacks:
  prod:
    type: gcp
    project_id: ${TEST_PROJECT_ID}
    artifact_store:
      bucket: ${TEST_BUCKET}
""")
        
        loader = ConfigLoader(str(config_path))
        config = loader.load()
        
        self.assertEqual(
            config.stacks["prod"]["project_id"],
            "test-project"
        )
        self.assertEqual(
            config.stacks["prod"]["artifact_store"]["bucket"],
            "test-bucket"
        )
        
        # Cleanup
        del os.environ["TEST_PROJECT_ID"]
        del os.environ["TEST_BUCKET"]
    
    def test_resources_configuration(self):
        """Test loading resource configurations."""
        config_path = Path(self.test_dir) / "uniflow.yaml"
        config_path.write_text("""
resources:
  small:
    cpu: "2"
    memory: "8Gi"
  
  large:
    cpu: "16"
    memory: "64Gi"
    gpu: "nvidia-tesla-v100"
    gpu_count: 4
""")
        
        loader = ConfigLoader(str(config_path))
        config = loader.load()
        
        self.assertIn("small", config.resources)
        self.assertIn("large", config.resources)
        self.assertEqual(config.resources["small"]["cpu"], "2")
        self.assertEqual(config.resources["large"]["gpu_count"], 4)
    
    def test_docker_configuration(self):
        """Test loading Docker configurations."""
        config_path = Path(self.test_dir) / "uniflow.yaml"
        config_path.write_text("""
docker:
  dockerfile: ./Dockerfile
  build_context: .
  base_image: python:3.11-slim
  env_vars:
    PYTHONUNBUFFERED: "1"
""")
        
        loader = ConfigLoader(str(config_path))
        docker_config = loader.get_docker_config()
        
        self.assertEqual(docker_config["dockerfile"], "./Dockerfile")
        self.assertIn("PYTHONUNBUFFERED", docker_config["env_vars"])
    
    def test_get_stack_config(self):
        """Test retrieving specific stack configuration."""
        config_path = Path(self.test_dir) / "uniflow.yaml"
        config_path.write_text("""
stacks:
  dev:
    type: local
  prod:
    type: gcp
    project_id: my-project
""")
        
        loader = ConfigLoader(str(config_path))
        loader.load()
        
        dev_config = loader.get_stack_config("dev")
        prod_config = loader.get_stack_config("prod")
        
        self.assertEqual(dev_config["type"], "local")
        self.assertEqual(prod_config["type"], "gcp")
    
    def test_list_stacks(self):
        """Test listing configured stacks."""
        config_path = Path(self.test_dir) / "uniflow.yaml"
        config_path.write_text("""
stacks:
  stack1:
    type: local
  stack2:
    type: local
  stack3:
    type: gcp
""")
        
        loader = ConfigLoader(str(config_path))
        loader.load()
        stack_list = loader.list_stacks()
        
        self.assertEqual(len(stack_list), 3)
        self.assertIn("stack1", stack_list)
        self.assertIn("stack2", stack_list)
        self.assertIn("stack3", stack_list)
    
    def test_get_default_stack(self):
        """Test getting default stack."""
        config_path = Path(self.test_dir) / "uniflow.yaml"
        config_path.write_text("""
stacks:
  first:
    type: local
  second:
    type: local

default_stack: second
""")
        
        loader = ConfigLoader(str(config_path))
        loader.load()
        default = loader.get_default_stack()
        
        self.assertEqual(default, "second")


class TestStackCreation(unittest.TestCase):
    """Test creating stacks from configuration."""
    
    def test_create_local_stack_from_config(self):
        """Test creating local stack from config dict."""
        config = {
            "type": "local",
            "artifact_store": {"path": "/tmp/artifacts"},
            "metadata_store": {"path": "/tmp/metadata.db"}
        }
        
        stack = create_stack_from_config(config, "test_local")
        
        self.assertEqual(stack.name, "test_local")
        self.assertIsNotNone(stack.artifact_store)
    
    def test_create_gcp_stack_from_config(self):
        """Test creating GCP stack from config dict."""
        config = {
            "type": "gcp",
            "project_id": "test-project",
            "region": "us-central1",
            "artifact_store": {"bucket": "test-bucket"}
        }
        
        stack = create_stack_from_config(config, "test_gcp")
        
        self.assertEqual(stack.name, "test_gcp")
        self.assertEqual(stack.project_id, "test-project")


class TestResourceCreation(unittest.TestCase):
    """Test creating resource configs from dictionaries."""
    
    def test_create_cpu_resource_config(self):
        """Test creating CPU resource configuration."""
        config_dict = {
            "cpu": "4",
            "memory": "16Gi",
            "disk_size": "100Gi"
        }
        
        config = create_resource_config_from_dict(config_dict)
        
        self.assertIsInstance(config, ResourceConfig)
        self.assertEqual(config.cpu, "4")
        self.assertEqual(config.memory, "16Gi")
    
    def test_create_gpu_resource_config(self):
        """Test creating GPU resource configuration."""
        config_dict = {
            "cpu": "16",
            "memory": "64Gi",
            "gpu": "nvidia-tesla-v100",
            "gpu_count": 4,
            "machine_type": "n1-highmem-16"
        }
        
        config = create_resource_config_from_dict(config_dict)
        
        self.assertEqual(config.gpu, "nvidia-tesla-v100")
        self.assertEqual(config.gpu_count, 4)
        self.assertEqual(config.machine_type, "n1-highmem-16")


class TestDockerCreation(unittest.TestCase):
    """Test creating Docker configs from dictionaries."""
    
    def test_create_docker_config_with_image(self):
        """Test creating Docker config with image."""
        config_dict = {
            "image": "gcr.io/project/image:v1",
            "env_vars": {"KEY": "value"}
        }
        
        config = create_docker_config_from_dict(config_dict)
        
        self.assertIsInstance(config, DockerConfig)
        self.assertEqual(config.image, "gcr.io/project/image:v1")
        self.assertEqual(config.env_vars["KEY"], "value")
    
    def test_create_docker_config_with_dockerfile(self):
        """Test creating Docker config with Dockerfile."""
        config_dict = {
            "dockerfile": "./Dockerfile",
            "build_context": ".",
            "build_args": {"PYTHON_VERSION": "3.11"}
        }
        
        config = create_docker_config_from_dict(config_dict)
        
        self.assertEqual(config.dockerfile, "./Dockerfile")
        self.assertEqual(config.build_context, ".")
        self.assertEqual(config.build_args["PYTHON_VERSION"], "3.11")
    
    def test_create_docker_config_with_requirements(self):
        """Test creating Docker config with requirements."""
        config_dict = {
            "requirements": ["tensorflow>=2.12.0", "pandas>=2.0.0"],
            "base_image": "python:3.11-slim"
        }
        
        config = create_docker_config_from_dict(config_dict)
        
        self.assertEqual(len(config.requirements), 2)
        self.assertIn("tensorflow>=2.12.0", config.requirements)


class TestAutoDetection(unittest.TestCase):
    """Test auto-detection of Docker configuration."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.addCleanup(os.chdir, self.original_cwd)
    
    def test_auto_detect_dockerfile(self):
        """Test auto-detection of Dockerfile."""
        # Create Dockerfile
        Path("Dockerfile").write_text("FROM python:3.11-slim")
        
        loader = ConfigLoader()
        docker_config = loader._get_default_docker_config()
        
        self.assertEqual(docker_config["dockerfile"], "Dockerfile")
    
    def test_auto_detect_poetry(self):
        """Test auto-detection of Poetry."""
        # Create pyproject.toml
        Path("pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
        
        loader = ConfigLoader()
        docker_config = loader._get_default_docker_config()
        
        self.assertTrue(docker_config["use_poetry"])
    
    def test_auto_detect_requirements(self):
        """Test auto-detection of requirements.txt."""
        # Create requirements.txt
        Path("requirements.txt").write_text("tensorflow>=2.12.0\npandas>=2.0.0")
        
        loader = ConfigLoader()
        docker_config = loader._get_default_docker_config()
        
        self.assertEqual(docker_config["requirements_file"], "requirements.txt")


if __name__ == "__main__":
    unittest.main()

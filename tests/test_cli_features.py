"""
Tests for CLI features including stack and component management.
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from click.testing import CliRunner
from flowyml.cli.stack_cli import cli
from flowyml.stacks.registry import get_registry
from flowyml.stacks.local import LocalStack


class TestCLIFeatures(unittest.TestCase):
    """Test CLI commands for stacks and components."""

    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Reset global registry to force re-initialization in new CWD
        from flowyml.stacks import registry

        registry._global_registry = None
        get_registry()  # This will create .flowyml directory in new CWD

    def tearDown(self):
        """Clean up."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        get_registry().clear()

    def test_init_command(self):
        """Test 'init' command creates flowyml.yaml."""
        result = self.runner.invoke(cli, ["init"])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(Path("flowyml.yaml").exists())
        self.assertIn("Created flowyml.yaml", result.output)

    def test_stack_list_empty(self):
        """Test 'stack list' with no config."""
        result = self.runner.invoke(cli, ["stack", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No stacks configured", result.output)

    def test_stack_list_with_config(self):
        """Test 'stack list' with configuration."""
        # Create config
        Path("flowyml.yaml").write_text(
            """
stacks:
  dev:
    type: local
  prod:
    type: gcp
default_stack: dev
""",
        )
        result = self.runner.invoke(cli, ["stack", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("dev (default) [local]", result.output)
        self.assertIn("prod [gcp]", result.output)

    def test_stack_show(self):
        """Test 'stack show' command."""
        Path("flowyml.yaml").write_text(
            """
stacks:
  dev:
    type: local
    artifact_store:
      path: ./artifacts
""",
        )
        result = self.runner.invoke(cli, ["stack", "show", "dev"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Stack: dev", result.output)
        self.assertIn("path: ./artifacts", result.output)

    def test_stack_set_default(self):
        """Test 'stack set-default' command."""
        # Register stacks in registry since set-default uses registry
        registry = get_registry()
        registry.register_stack(LocalStack("dev"))
        registry.register_stack(LocalStack("prod"))

        result = self.runner.invoke(cli, ["stack", "set-default", "prod"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Set 'prod' as active stack", result.output)
        self.assertEqual(registry.get_active_stack().name, "prod")

    def test_component_list(self):
        """Test 'component list' command."""
        result = self.runner.invoke(cli, ["component", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Registered Components", result.output)

    def test_component_load_failure(self):
        """Test 'component load' with invalid source."""
        result = self.runner.invoke(cli, ["component", "load", "nonexistent.module"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Error loading component", result.output)

    def test_run_dry_run(self):
        """Test 'run' command with dry-run."""
        # Create dummy pipeline
        Path("pipeline.py").write_text(
            """
from flowyml import Pipeline, step
@step
def task(): pass
pipeline = Pipeline("test")
pipeline.add_step(task)
""",
        )
        # Create config
        Path("flowyml.yaml").write_text(
            """
stacks:
  local:
    type: local
""",
        )

        result = self.runner.invoke(cli, ["run", "pipeline.py", "--dry-run"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Dry run - configuration", result.output)
        self.assertIn("Stack:", result.output)

    def test_run_with_context_and_resources(self):
        """Test 'run' command with context and resources flags."""
        Path("pipeline.py").write_text(
            """
from flowyml import Pipeline, step
@step
def task(): pass
pipeline = Pipeline("test")
pipeline.add_step(task)
""",
        )
        Path("flowyml.yaml").write_text(
            """
stacks:
  local:
    type: local
resources:
  gpu:
    gpu_count: 1
""",
        )

        result = self.runner.invoke(
            cli,
            [
                "run",
                "pipeline.py",
                "--dry-run",
                "--resources",
                "gpu",
                "--context",
                "key=value",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Resources:", result.output)
        self.assertIn("gpu_count=1", result.output)
        self.assertIn("'key': 'value'", result.output)


if __name__ == "__main__":
    unittest.main()

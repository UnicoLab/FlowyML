"""Test suite for pipeline functionality."""

import unittest
from flowyml import Pipeline, step
from flowyml.core.context import Context
from tests.base import BaseTestCase


class TestPipeline(BaseTestCase):
    """Test suite for pipeline functionality."""

    def test_pipeline_creation(self):
        """Test pipeline creation."""
        p = Pipeline("test_pipeline")
        self.assertEqual(p.name, "test_pipeline")
        self.assertEqual(len(p.steps), 0)

    def test_pipeline_with_context(self):
        """Test pipeline creation with context."""
        ctx = Context(param1="value1")
        p = Pipeline("ctx_pipeline", context=ctx)

        self.assertEqual(p.context.get("param1"), "value1")

    def test_pipeline_add_step(self):
        """Test adding steps to pipeline."""

        @step
        def step1():
            return "result1"

        p = Pipeline("add_step_test")
        p.add_step(step1)

        self.assertEqual(len(p.steps), 1)

    def test_pipeline_add_multiple_steps(self):
        """Test adding multiple steps."""

        @step
        def step1():
            return "r1"

        @step
        def step2():
            return "r2"

        @step
        def step3():
            return "r3"

        p = Pipeline("multi_step_test")
        p.add_step(step1)
        p.add_step(step2)
        p.add_step(step3)

        self.assertEqual(len(p.steps), 3)

    def test_pipeline_execution_success(self):
        """Test successful pipeline execution."""

        @step
        def double(value: int):
            return value * 2

        p = Pipeline("success_test", context=Context(value=21))
        p.add_step(double)

        result = p.run()

        self.assertTrue(result.success)
        self.assertEqual(result["double"], 42)

    def test_pipeline_with_cache_enabled(self):
        """Test pipeline with caching enabled."""
        p = Pipeline("cache_enabled", enable_cache=True)
        self.assertTrue(p.enable_cache)
        self.assertIsNotNone(p.cache_store)

    def test_pipeline_with_cache_disabled(self):
        """Test pipeline with caching disabled."""
        p = Pipeline("cache_disabled", enable_cache=False)
        self.assertFalse(p.enable_cache)
        self.assertIsNone(p.cache_store)

    def test_pipeline_run_creates_run_directory(self):
        """Test that pipeline run creates run directory."""

        @step
        def simple():
            return "done"

        p = Pipeline("run_dir_test")
        p.add_step(simple)

        result = p.run()

        # Check that runs directory exists
        self.assertTrue(p.runs_dir.exists())

    def test_pipeline_result_access(self):
        """Test accessing pipeline results."""

        @step
        def return_value():
            return {"key": "value"}

        p = Pipeline("result_access_test")
        p.add_step(return_value)

        result = p.run()

        self.assertIn("return_value", result.outputs)
        self.assertEqual(result["return_value"]["key"], "value")

    def test_pipeline_with_failing_step(self):
        """Test pipeline with a failing step."""

        @step
        def failing_step():
            raise ValueError("Intentional failure")

        p = Pipeline("failure_test")
        p.add_step(failing_step)

        result = p.run()

        self.assertFalse(result.success)
        # Check that there's an error in the step results
        self.assertIsNotNone(result.step_results.get("failing_step"))

    def test_pipeline_with_project_name(self):
        """Test pipeline with project_name parameter."""
        import tempfile
        import shutil
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary projects directory
            projects_dir = Path(tmpdir) / "projects"
            projects_dir.mkdir()

            # Mock the projects directory
            from flowyml.utils.config import get_config, update_config

            original_projects_dir = get_config().projects_dir
            update_config(projects_dir=str(projects_dir))

            try:
                # Create pipeline with project_name (should create project automatically)
                p = Pipeline("test_pipeline", project_name="test_project")
                self.assertEqual(p.name, "test_pipeline")

                # Verify project was created
                project_dir = projects_dir / "test_project"
                self.assertTrue(project_dir.exists())
                self.assertTrue((project_dir / "project.json").exists())

                # Verify pipeline is using project's runs directory
                self.assertEqual(p.runs_dir, project_dir / "runs")
            finally:
                update_config(projects_dir=str(original_projects_dir))

    def test_pipeline_with_version_creates_versioned_pipeline(self):
        """Test that Pipeline with version parameter creates VersionedPipeline."""
        from flowyml.core.versioning import VersionedPipeline

        p = Pipeline("versioned_test", version="v1.0.0")
        self.assertIsInstance(p, VersionedPipeline)
        self.assertEqual(p.version, "v1.0.0")
        self.assertEqual(p.name, "versioned_test")

    def test_pipeline_with_version_and_context(self):
        """Test Pipeline with version and context parameters."""
        from flowyml.core.versioning import VersionedPipeline

        ctx = Context(learning_rate=0.001, epochs=10)
        p = Pipeline("versioned_with_ctx", context=ctx, version="v1.0.1")

        self.assertIsInstance(p, VersionedPipeline)
        self.assertEqual(p.version, "v1.0.1")
        self.assertEqual(p.context.get("learning_rate"), 0.001)
        self.assertEqual(p.context.get("epochs"), 10)

    def test_pipeline_with_version_and_project_name(self):
        """Test Pipeline with version and project_name parameters."""
        import tempfile
        from pathlib import Path
        from flowyml.core.versioning import VersionedPipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            projects_dir = Path(tmpdir) / "projects"
            projects_dir.mkdir()

            from flowyml.utils.config import get_config, update_config

            original_projects_dir = get_config().projects_dir
            update_config(projects_dir=str(projects_dir))

            try:
                p = Pipeline("versioned_project_test", version="v1.0.0", project_name="test_project")

                self.assertIsInstance(p, VersionedPipeline)
                self.assertEqual(p.version, "v1.0.0")

                # Verify project was created
                project_dir = projects_dir / "test_project"
                self.assertTrue(project_dir.exists())
            finally:
                update_config(projects_dir=str(original_projects_dir))


if __name__ == "__main__":
    unittest.main()

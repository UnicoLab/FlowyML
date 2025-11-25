"""Test suite for pipeline functionality."""

import unittest
from uniflow import Pipeline, step
from uniflow.core.context import Context
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


if __name__ == "__main__":
    unittest.main()

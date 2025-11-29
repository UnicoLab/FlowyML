"""Extended test suite for pipeline functionality."""

import unittest
from flowyml import Pipeline, step
from flowyml.core.context import Context
from tests.base import BaseTestCase


class TestPipelineExtended(BaseTestCase):
    """Extended test suite for pipeline functionality."""

    def test_pipeline_with_no_steps(self):
        """Test pipeline with no steps."""
        p = Pipeline("empty_pipeline")
        self.assertEqual(len(p.steps), 0)

    def test_pipeline_name_validation(self):
        """Test pipeline name is set correctly."""
        p = Pipeline("my_custom_pipeline")
        self.assertEqual(p.name, "my_custom_pipeline")

    def test_pipeline_context_injection(self):
        """Test context is properly injected into pipeline."""
        ctx = Context(param1="value1", param2=42)
        p = Pipeline("ctx_pipeline", context=ctx)

        self.assertEqual(p.context.get("param1"), "value1")
        self.assertEqual(p.context.get("param2"), 42)

    def test_pipeline_with_single_step(self):
        """Test pipeline with single step execution."""

        @step
        def single():
            return "single_result"

        p = Pipeline("single_step_pipeline")
        p.add_step(single)

        result = p.run()
        self.assertTrue(result.success)
        self.assertEqual(result["single"], "single_result")

    def test_pipeline_step_ordering(self):
        """Test that steps are executed in order."""
        execution_order = []

        @step
        def first():
            execution_order.append(1)
            return "first"

        @step
        def second():
            execution_order.append(2)
            return "second"

        @step
        def third():
            execution_order.append(3)
            return "third"

        p = Pipeline("ordered_pipeline")
        p.add_step(first)
        p.add_step(second)
        p.add_step(third)

        p.run()
        self.assertEqual(execution_order, [1, 2, 3])

    def test_pipeline_result_outputs(self):
        """Test accessing pipeline result outputs."""

        @step
        def produce_data():
            return {"key": "value", "number": 42}

        p = Pipeline("output_test")
        p.add_step(produce_data)

        result = p.run()
        self.assertIn("produce_data", result.outputs)
        self.assertEqual(result.outputs["produce_data"]["key"], "value")

    def test_pipeline_with_context_parameters(self):
        """Test pipeline using context parameters."""

        @step
        def use_context(multiplier: int, base: int):
            return base * multiplier

        ctx = Context(multiplier=5, base=10)
        p = Pipeline("context_params", context=ctx)
        p.add_step(use_context)

        result = p.run()
        self.assertEqual(result["use_context"], 50)

    def test_pipeline_caching_enabled(self):
        """Test pipeline with caching enabled."""
        p = Pipeline("cached_pipeline", enable_cache=True)
        self.assertTrue(p.enable_cache)
        self.assertIsNotNone(p.cache_store)

    def test_pipeline_caching_disabled(self):
        """Test pipeline with caching disabled."""
        p = Pipeline("uncached_pipeline", enable_cache=False)
        self.assertFalse(p.enable_cache)
        self.assertIsNone(p.cache_store)

    def test_pipeline_runs_directory_created(self):
        """Test that runs directory is created."""
        p = Pipeline("runs_dir_test")
        self.assertTrue(p.runs_dir.exists())
        self.assertTrue(p.runs_dir.is_dir())


if __name__ == "__main__":
    unittest.main()

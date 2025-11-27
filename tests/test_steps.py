"""Test suite for step functionality."""

import unittest
from uniflow import step, Pipeline
from uniflow.core.step import Step
from uniflow.core.context import Context
from tests.base import BaseTestCase


class TestSteps(BaseTestCase):
    """Test suite for step functionality."""

    def test_step_decorator_basic(self):
        """Test basic step decorator."""

        @step
        def simple_step():
            return "result"

        # Check that it's been wrapped
        self.assertTrue(callable(simple_step))

    def test_step_with_inputs_outputs(self):
        """Test step with explicit inputs and outputs."""

        @step(inputs=["data"], outputs=["processed"])
        def processing_step(data):
            return data.upper()

        self.assertEqual(processing_step.inputs, ["data"])
        self.assertEqual(processing_step.outputs, ["processed"])

    def test_step_with_retry(self):
        """Test step with retry configuration."""

        @step(retry=3)
        def retryable_step():
            return "success"

        self.assertEqual(retryable_step.retry, 3)

    def test_step_with_timeout(self):
        """Test step with timeout configuration."""

        @step(timeout=60)
        def timed_step():
            return "done"

        self.assertEqual(timed_step.timeout, 60)

    def test_step_with_resources(self):
        """Test step with resource requirements."""

        @step(resources={"gpu": 1, "memory": "4GB"})
        def gpu_step():
            return "computed"

        self.assertEqual(gpu_step.resources["gpu"], 1)
        self.assertEqual(gpu_step.resources["memory"], "4GB")

    def test_step_with_cache_disabled(self):
        """Test step with caching disabled."""

        @step(cache=False)
        def no_cache_step():
            return "fresh"

        self.assertEqual(no_cache_step.cache, False)

    def test_step_with_cache_strategy(self):
        """Test step with specific cache strategy."""

        @step(cache="input_hash")
        def cached_step():
            return "cached"

        self.assertEqual(cached_step.cache, "input_hash")

    def test_step_execution_in_pipeline(self):
        """Test step execution within pipeline."""

        @step
        def add_ten(value: int):
            return value + 10

        p = Pipeline("step_exec_test", context=Context(value=5))
        p.add_step(add_ten)

        result = p.run()
        self.assertEqual(result["add_ten"], 15)

    def test_step_with_default_parameters(self):
        """Test step with default parameter values."""

        @step
        def with_defaults(required, optional="default"):
            return f"{required}_{optional}"

        p = Pipeline("defaults_test", context=Context(required="value"))
        p.add_step(with_defaults)

        result = p.run()
        self.assertEqual(result["with_defaults"], "value_default")

    def test_step_name_inference(self):
        """Test that step name is inferred from function name."""

        @step
        def my_custom_step():
            return "result"

        self.assertEqual(my_custom_step.name, "my_custom_step")


if __name__ == "__main__":
    unittest.main()

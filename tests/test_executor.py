"""Test suite for executor functionality."""

import unittest
from uniflow import Pipeline, step
from uniflow.core.executor import LocalExecutor
from uniflow.core.context import Context
from tests.base import BaseTestCase


class TestExecutor(BaseTestCase):
    """Test suite for executor functionality."""

    def test_local_executor_creation(self):
        """Test creating a local executor."""
        executor = LocalExecutor()
        self.assertIsNotNone(executor)

    def test_executor_executes_step(self):
        """Test that executor can execute a step."""

        @step
        def simple_step():
            return 42

        p = Pipeline("executor_test")
        p.add_step(simple_step)

        result = p.run()
        self.assertTrue(result.success)
        self.assertEqual(result["simple_step"], 42)

    def test_executor_handles_step_failure(self):
        """Test that executor handles step failures."""

        @step
        def failing_step():
            raise ValueError("Test error")

        p = Pipeline("failure_test")
        p.add_step(failing_step)

        result = p.run()
        self.assertFalse(result.success)

    def test_executor_with_multiple_steps(self):
        """Test executor with multiple sequential steps."""

        @step
        def step1():
            return 10

        @step
        def step2(value: int):
            return value * 2

        @step
        def step3(value: int):
            return value + 5

        p = Pipeline("multi_step", context=Context(value=10))
        p.add_step(step1)
        p.add_step(step2)
        p.add_step(step3)

        result = p.run()
        self.assertTrue(result.success)

    def test_executor_step_timing(self):
        """Test that executor tracks step execution time."""

        @step
        def timed_step():
            import time

            time.sleep(0.1)
            return "done"

        p = Pipeline("timing_test")
        p.add_step(timed_step)

        result = p.run()
        self.assertTrue(result.success)
        self.assertIn("timed_step", result.step_results)


if __name__ == "__main__":
    unittest.main()

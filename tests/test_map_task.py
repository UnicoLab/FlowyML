"""Tests for map task functionality."""

import unittest
from flowyml.core.map_task import map_task, MapTaskStep, MapTaskResult, MapTaskConfig
from tests.base import BaseTestCase


class TestMapTask(BaseTestCase):
    """Test suite for @map_task decorator and MapTaskStep."""

    def test_map_task_decorator_basic(self):
        """@map_task creates a MapTaskStep."""

        @map_task
        def double(x: int) -> int:
            return x * 2

        self.assertIsInstance(double, MapTaskStep)
        self.assertEqual(double.name, "double")

    def test_map_task_decorator_with_config(self):
        """@map_task accepts configuration arguments."""

        @map_task(concurrency=8, retries=2, min_success_ratio=0.9)
        def process(x: int) -> int:
            return x + 1

        self.assertIsInstance(process, MapTaskStep)
        self.assertEqual(process.map_config.concurrency, 8)
        self.assertEqual(process.map_config.retries, 2)
        self.assertAlmostEqual(process.map_config.min_success_ratio, 0.9)

    def test_map_task_execution(self):
        """Map task executes function over a collection."""

        @map_task(concurrency=2)
        def square(x: int) -> int:
            return x**2

        result = square([1, 2, 3, 4, 5])
        self.assertIsInstance(result, MapTaskResult)
        self.assertEqual(result.total, 5)
        self.assertEqual(result.successes, 5)
        self.assertEqual(result.failures, 0)
        self.assertEqual(sorted(result.results), [1, 4, 9, 16, 25])

    def test_map_task_partial_failure(self):
        """Map task handles partial failures with min_success_ratio."""

        @map_task(concurrency=2, min_success_ratio=0.5)
        def risky(x: int) -> int:
            if x == 3:
                raise ValueError("Bad value")
            return x

        result = risky([1, 2, 3, 4])
        self.assertEqual(result.successes, 3)
        self.assertEqual(result.failures, 1)
        self.assertIn(2, result.errors)  # Index 2 (value 3) failed

    def test_map_task_fail_below_threshold(self):
        """Map task raises when success ratio is below minimum."""

        @map_task(concurrency=1, min_success_ratio=1.0)
        def strict(x: int) -> int:
            if x == 1:
                raise ValueError("Fail")
            return x

        with self.assertRaises(RuntimeError):
            strict([1, 2, 3])

    def test_map_task_result_properties(self):
        """MapTaskResult has correct computed properties."""
        result = MapTaskResult(
            results=[1, None, 3],
            successes=2,
            failures=1,
            total=3,
            errors={1: "failed"},
        )
        self.assertAlmostEqual(result.success_ratio, 2 / 3)
        self.assertEqual(result.successful_results, [1, 3])

    def test_map_task_empty_collection(self):
        """Map task handles empty collections gracefully."""

        @map_task
        def noop(x: int) -> int:
            return x

        result = noop([])
        self.assertEqual(result.total, 0)
        self.assertEqual(result.successes, 0)

    def test_map_task_config_defaults(self):
        """MapTaskConfig has sensible defaults."""
        config = MapTaskConfig()
        self.assertEqual(config.concurrency, 4)
        self.assertEqual(config.retries, 0)
        self.assertAlmostEqual(config.min_success_ratio, 1.0)
        self.assertFalse(config.fail_fast)


if __name__ == "__main__":
    unittest.main()

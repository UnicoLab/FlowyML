"""Test suite for error handling."""

import unittest
from flowyml import Pipeline, step
from tests.base import BaseTestCase


class TestErrorHandling(BaseTestCase):
    """Test suite for error handling."""

    def test_step_exception_handling(self):
        """Test that step exceptions are properly caught."""

        @step
        def error_step():
            raise RuntimeError("Intentional error")

        p = Pipeline("error_test")
        p.add_step(error_step)

        result = p.run()
        self.assertFalse(result.success)

    def test_type_error_handling(self):
        """Test handling of type errors in steps."""

        @step
        def type_error_step():
            return 1 + "string"  # This will raise TypeError

        p = Pipeline("type_error_test")
        p.add_step(type_error_step)

        result = p.run()
        self.assertFalse(result.success)

    def test_value_error_handling(self):
        """Test handling of value errors."""

        @step
        def value_error_step():
            raise ValueError("Invalid value")

        p = Pipeline("value_error_test")
        p.add_step(value_error_step)

        result = p.run()
        self.assertFalse(result.success)

    def test_multiple_step_failure(self):
        """Test pipeline with multiple steps where one fails."""

        @step
        def success_step():
            return "success"

        @step
        def fail_step():
            raise Exception("Failed")

        p = Pipeline("multi_fail_test")
        p.add_step(success_step)
        p.add_step(fail_step)

        result = p.run()
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()

"""Extended test suite for step functionality."""

import unittest
from flowyml import step, Pipeline
from flowyml.core.context import Context
from tests.base import BaseTestCase


class TestStepsExtended(BaseTestCase):
    """Extended test suite for step functionality."""

    def test_step_with_no_arguments(self):
        """Test step with no arguments."""

        @step
        def no_args():
            return 42

        p = Pipeline("no_args_test")
        p.add_step(no_args)
        result = p.run()

        self.assertEqual(result["no_args"], 42)

    def test_step_with_single_argument(self):
        """Test step with single argument."""

        @step
        def single_arg(value: int):
            return value * 2

        p = Pipeline("single_arg_test", context=Context(value=21))
        p.add_step(single_arg)
        result = p.run()

        self.assertEqual(result["single_arg"], 42)

    def test_step_with_multiple_arguments(self):
        """Test step with multiple arguments."""

        @step
        def multi_args(a: int, b: int, c: int):
            return a + b + c

        p = Pipeline("multi_args_test", context=Context(a=10, b=20, c=12))
        p.add_step(multi_args)
        result = p.run()

        self.assertEqual(result["multi_args"], 42)

    def test_step_with_default_values(self):
        """Test step with default parameter values."""

        @step
        def with_defaults(required, optional1="default1", optional2=100):
            return f"{required}-{optional1}-{optional2}"

        p = Pipeline("defaults_test", context=Context(required="test"))
        p.add_step(with_defaults)
        result = p.run()

        self.assertEqual(result["with_defaults"], "test-default1-100")

    def test_step_returning_none(self):
        """Test step that returns None."""

        @step
        def returns_none():
            return None

        p = Pipeline("none_test")
        p.add_step(returns_none)
        result = p.run()

        self.assertIsNone(result["returns_none"])

    def test_step_returning_list(self):
        """Test step that returns a list."""

        @step
        def returns_list():
            return [1, 2, 3, 4, 5]

        p = Pipeline("list_test")
        p.add_step(returns_list)
        result = p.run()

        self.assertEqual(result["returns_list"], [1, 2, 3, 4, 5])

    def test_step_returning_dict(self):
        """Test step that returns a dictionary."""

        @step
        def returns_dict():
            return {"key1": "value1", "key2": 42}

        p = Pipeline("dict_test")
        p.add_step(returns_dict)
        result = p.run()

        self.assertEqual(result["returns_dict"]["key1"], "value1")
        self.assertEqual(result["returns_dict"]["key2"], 42)

    def test_step_with_type_hints(self):
        """Test step with type hints."""

        @step
        def typed_step(x: int, y: str) -> str:
            return f"{y}_{x}"

        p = Pipeline("typed_test", context=Context(x=42, y="answer"))
        p.add_step(typed_step)
        result = p.run()

        self.assertEqual(result["typed_step"], "answer_42")

    def test_step_name_from_function(self):
        """Test that step name is derived from function name."""

        @step
        def my_custom_step_name():
            return "test"

        self.assertEqual(my_custom_step_name.name, "my_custom_step_name")

    def test_step_with_explicit_name(self):
        """Test step with explicitly set name."""

        @step(name="custom_name")
        def some_function():
            return "test"

        self.assertEqual(some_function.name, "custom_name")


if __name__ == "__main__":
    unittest.main()

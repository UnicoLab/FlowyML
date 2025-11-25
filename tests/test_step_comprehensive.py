"""Comprehensive test suite for step decorator and configuration."""

import unittest
from uniflow import step, Pipeline
from uniflow.core.step import Step
from uniflow.core.context import Context
from tests.base import BaseTestCase


class TestStepComprehensive(BaseTestCase):
    """Comprehensive test suite for step functionality."""

    def test_step_decorator_without_parens(self):
        """Test step decorator without parentheses."""
        @step
        def my_step():
            return "result"
        
        self.assertTrue(callable(my_step))
        self.assertTrue(hasattr(my_step, 'name'))

    def test_step_decorator_with_parens(self):
        """Test step decorator with parentheses."""
        @step()
        def my_step():
            return "result"
        
        self.assertTrue(callable(my_step))

    def test_step_name_attribute(self):
        """Test step has name attribute."""
        @step
        def named_step():
            return "result"
        
        self.assertEqual(named_step.name, "named_step")

    def test_step_custom_name(self):
        """Test step with custom name."""
        @step(name="custom")
        def some_function():
            return "result"
        
        self.assertEqual(some_function.name, "custom")

    def test_step_inputs_configuration(self):
        """Test step inputs configuration."""
        @step(inputs=["input1", "input2"])
        def process(input1, input2):
            return input1 + input2
        
        self.assertEqual(process.inputs, ["input1", "input2"])

    def test_step_outputs_configuration(self):
        """Test step outputs configuration."""
        @step(outputs=["output1", "output2"])
        def produce():
            return {"output1": 1, "output2": 2}
        
        self.assertEqual(produce.outputs, ["output1", "output2"])

    def test_step_cache_configuration(self):
        """Test step cache configuration."""
        @step(cache=True)
        def cached():
            return "result"
        
        self.assertTrue(cached.cache)

    def test_step_cache_disabled(self):
        """Test step with cache disabled."""
        @step(cache=False)
        def uncached():
            return "result"
        
        self.assertFalse(uncached.cache)

    def test_step_retry_configuration(self):
        """Test step retry configuration."""
        @step(retry=3)
        def retryable():
            return "result"
        
        self.assertEqual(retryable.retry, 3)

    def test_step_timeout_configuration(self):
        """Test step timeout configuration."""
        @step(timeout=30)
        def timed():
            return "result"
        
        self.assertEqual(timed.timeout, 30)

    def test_step_resources_configuration(self):
        """Test step resources configuration."""
        @step(resources={"cpu": 2, "memory": "4GB"})
        def resource_heavy():
            return "result"
        
        self.assertEqual(resource_heavy.resources["cpu"], 2)
        self.assertEqual(resource_heavy.resources["memory"], "4GB")

    def test_step_execution_with_return_value(self):
        """Test step execution returns value."""
        @step
        def returns_value():
            return 42
        
        p = Pipeline("return_test")
        p.add_step(returns_value)
        result = p.run()
        
        self.assertEqual(result["returns_value"], 42)

    def test_step_execution_with_dict_return(self):
        """Test step execution with dict return."""
        @step
        def returns_dict():
            return {"key": "value", "number": 123}
        
        p = Pipeline("dict_return_test")
        p.add_step(returns_dict)
        result = p.run()
        
        self.assertEqual(result["returns_dict"]["key"], "value")
        self.assertEqual(result["returns_dict"]["number"], 123)

    def test_step_with_context_parameter(self):
        """Test step using context parameter."""
        @step
        def uses_context(param: str):
            return f"Got: {param}"
        
        p = Pipeline("context_test", context=Context(param="test_value"))
        p.add_step(uses_context)
        result = p.run()
        
        self.assertEqual(result["uses_context"], "Got: test_value")

    def test_step_with_multiple_context_params(self):
        """Test step using multiple context parameters."""
        @step
        def multi_params(a: int, b: int, c: int):
            return a + b + c
        
        p = Pipeline("multi_test", context=Context(a=10, b=20, c=30))
        p.add_step(multi_params)
        result = p.run()
        
        self.assertEqual(result["multi_params"], 60)


if __name__ == "__main__":
    unittest.main()

"""Tests for dynamic workflow functionality."""

import unittest
from flowyml.core.dynamic import dynamic, DynamicStep, DynamicWorkflowResult
from tests.base import BaseTestCase


class TestDynamic(BaseTestCase):
    """Test suite for @dynamic decorator."""

    def test_dynamic_decorator_basic(self):
        """@dynamic creates a DynamicStep."""

        @dynamic
        def my_dynamic():
            return None

        self.assertIsInstance(my_dynamic, DynamicStep)
        self.assertEqual(my_dynamic.name, "my_dynamic")

    def test_dynamic_decorator_with_name(self):
        """@dynamic accepts a custom name."""

        @dynamic(name="custom_name")
        def my_dynamic():
            return None

        self.assertIsInstance(my_dynamic, DynamicStep)
        self.assertEqual(my_dynamic.name, "custom_name")

    def test_dynamic_returns_none(self):
        """Dynamic step returning None produces empty result."""

        @dynamic
        def empty_dynamic():
            return None

        result = empty_dynamic()
        self.assertIsInstance(result, DynamicWorkflowResult)
        self.assertFalse(result.expanded)
        self.assertIsNone(result.results)

    def test_dynamic_returns_direct_value(self):
        """Dynamic step returning non-Pipeline wraps as direct result."""

        @dynamic
        def direct_dynamic():
            return {"key": "value"}

        result = direct_dynamic()
        self.assertIsInstance(result, DynamicWorkflowResult)
        self.assertEqual(result.results, {"key": "value"})

    def test_dynamic_workflow_result_defaults(self):
        """DynamicWorkflowResult has sensible defaults."""
        result = DynamicWorkflowResult()
        self.assertIsNone(result.sub_pipeline)
        self.assertIsNone(result.results)
        self.assertFalse(result.expanded)


if __name__ == "__main__":
    unittest.main()

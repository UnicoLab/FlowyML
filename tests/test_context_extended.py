"""Extended test suite for context functionality."""

import unittest
from uniflow.core.context import Context
from uniflow import Pipeline, step
from tests.base import BaseTestCase


class TestContextExtended(BaseTestCase):
    """Extended test suite for context functionality."""

    def test_context_empty_creation(self):
        """Test creating an empty context."""
        ctx = Context()
        self.assertIsNotNone(ctx)

    def test_context_with_single_param(self):
        """Test context with single parameter."""
        ctx = Context(param="value")
        self.assertEqual(ctx.get("param"), "value")

    def test_context_with_numeric_values(self):
        """Test context with numeric values."""
        ctx = Context(int_val=42, float_val=3.14, bool_val=True)

        self.assertEqual(ctx.get("int_val"), 42)
        self.assertAlmostEqual(ctx.get("float_val"), 3.14)
        self.assertTrue(ctx.get("bool_val"))

    def test_context_with_list_values(self):
        """Test context with list values."""
        ctx = Context(my_list=[1, 2, 3, 4, 5])
        self.assertEqual(ctx.get("my_list"), [1, 2, 3, 4, 5])

    def test_context_with_dict_values(self):
        """Test context with dictionary values."""
        ctx = Context(my_dict={"nested": "value", "count": 10})
        self.assertEqual(ctx.get("my_dict")["nested"], "value")
        self.assertEqual(ctx.get("my_dict")["count"], 10)

    def test_context_get_nonexistent_key(self):
        """Test getting non-existent key from context."""
        ctx = Context(existing="value")
        self.assertIsNone(ctx.get("nonexistent"))

    def test_context_get_with_default(self):
        """Test getting value with default."""
        ctx = Context(key="value")
        self.assertEqual(ctx.get("missing", "default"), "default")
        self.assertEqual(ctx.get("key", "default"), "value")

    def test_context_bracket_access(self):
        """Test accessing context with bracket notation."""
        ctx = Context(key="value")
        self.assertEqual(ctx["key"], "value")

    def test_context_injection_with_missing_param(self):
        """Test context injection when parameter is missing."""

        @step
        def needs_param(required_param: str = "default"):
            return required_param

        p = Pipeline("missing_param_test", context=Context())
        p.add_step(needs_param)
        result = p.run()

        self.assertEqual(result["needs_param"], "default")

    def test_context_with_complex_types(self):
        """Test context with complex nested types."""
        ctx = Context(
            config={
                "model": {
                    "type": "neural_network",
                    "layers": [128, 64, 32],
                    "activation": "relu",
                },
                "training": {
                    "epochs": 100,
                    "batch_size": 32,
                },
            },
        )

        self.assertEqual(ctx.get("config")["model"]["type"], "neural_network")
        self.assertEqual(ctx.get("config")["training"]["epochs"], 100)


if __name__ == "__main__":
    unittest.main()

"""
Tests for advanced context features.

Tests context inheritance, validation, and injection.
"""

import unittest
from typing import Optional
from uniflow.core.context import Context


class TestAdvancedContext(unittest.TestCase):
    """Test advanced context features."""

    def test_context_inheritance(self):
        """Test context inheritance from parent."""
        parent = Context(global_param="global", shared="parent_value")
        child = parent.inherit(local_param="local", shared="child_value")

        # Test access
        self.assertEqual(child.global_param, "global")
        self.assertEqual(child.local_param, "local")
        self.assertEqual(child.shared, "child_value")  # Override

        # Parent should be unchanged
        self.assertEqual(parent.shared, "parent_value")
        with self.assertRaises(AttributeError):
            _ = parent.local_param

    def test_context_injection(self):
        """Test parameter injection into functions."""
        ctx = Context(a=1, b=2, c=3)

        def func(a, b, d=4):
            return a + b + d

        injected = ctx.inject_params(func)

        self.assertEqual(injected["a"], 1)
        self.assertEqual(injected["b"], 2)
        self.assertNotIn("c", injected)  # Not in signature
        self.assertNotIn("d", injected)  # Has default

    def test_context_validation(self):
        """Test validation of required parameters."""
        ctx = Context(a=1)

        def func(a, b):
            pass

        missing = ctx.validate_for_step(func)
        self.assertEqual(missing, ["b"])

        # With exclude
        missing_excluded = ctx.validate_for_step(func, exclude=["b"])
        self.assertEqual(missing_excluded, [])

    def test_context_update_nested(self):
        """Test updating context values."""
        ctx = Context(x=1)
        ctx.update({"y": 2})

        self.assertEqual(ctx.x, 1)
        self.assertEqual(ctx.y, 2)

        # Update existing
        ctx.update({"x": 10})
        self.assertEqual(ctx.x, 10)

    def test_context_to_dict_inheritance(self):
        """Test to_dict with inheritance."""
        parent = Context(p=1)
        child = parent.inherit(c=2)

        d = child.to_dict()
        self.assertEqual(d["p"], 1)
        self.assertEqual(d["c"], 2)


if __name__ == "__main__":
    unittest.main()

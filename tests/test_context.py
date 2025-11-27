"""Test suite for context and parameter injection."""

import unittest
from uniflow.core.context import Context
from uniflow import Pipeline, step
from tests.base import BaseTestCase


class TestContext(BaseTestCase):
    """Test suite for context functionality."""

    def test_context_creation_with_params(self):
        """Test context creation with parameters."""
        ctx = Context(
            learning_rate=0.01,
            batch_size=32,
            epochs=10,
        )

        self.assertEqual(ctx["learning_rate"], 0.01)
        self.assertEqual(ctx["batch_size"], 32)
        self.assertEqual(ctx["epochs"], 10)

    def test_context_get_param(self):
        """Test getting parameters from context."""
        ctx = Context(model_name="resnet50", version="v1.0")

        self.assertEqual(ctx.get("model_name"), "resnet50")
        self.assertEqual(ctx.get("version"), "v1.0")
        self.assertIsNone(ctx.get("nonexistent"))

    def test_context_get_param_with_default(self):
        """Test getting parameters with default values."""
        ctx = Context(existing_param="value")

        self.assertEqual(ctx.get("existing_param", "default"), "value")
        self.assertEqual(ctx.get("missing_param", "default"), "default")

    def test_parameter_injection_in_pipeline(self):
        """Test automatic parameter injection in pipeline."""
        ctx = Context(multiplier=3, offset=10)

        @step
        def compute(multiplier: int, offset: int):
            return multiplier * 5 + offset

        p = Pipeline("injection_test", context=ctx)
        p.add_step(compute)

        result = p.run()
        self.assertEqual(result["compute"], 25)  # 3 * 5 + 10

    def test_partial_parameter_injection(self):
        """Test injection with some params from context, some from args."""
        ctx = Context(multiplier=2, value=7)

        @step
        def mixed_params(value, multiplier: int):
            return value * multiplier

        p = Pipeline("mixed_test", context=ctx)
        p.add_step(mixed_params)

        result = p.run()
        self.assertEqual(result["mixed_params"], 14)

    def test_context_with_nested_dict(self):
        """Test context with nested dictionary parameters."""
        ctx = Context(
            model_config={
                "layers": 5,
                "units": 128,
            },
            training_config={
                "lr": 0.001,
                "epochs": 20,
            },
        )

        self.assertEqual(ctx.get("model_config")["layers"], 5)
        self.assertEqual(ctx.get("training_config")["lr"], 0.001)


if __name__ == "__main__":
    unittest.main()

"""
Test suite for UniFlow package.
"""

import pytest
from uniflow import Pipeline, step, context, Dataset, Model, Metrics
from tests.base import BaseTestCase


class TestUniFlow(BaseTestCase):
    """Test suite for UniFlow package."""

    def test_context_creation(self):
        """Test context creation and parameter access."""
        ctx = context(learning_rate=0.001, epochs=10)

        self.assertEqual(ctx.learning_rate, 0.001)
        self.assertEqual(ctx.epochs, 10)
        self.assertEqual(ctx["learning_rate"], 0.001)

    def test_context_injection(self):
        """Test automatic parameter injection."""
        ctx = context(lr=0.001, epochs=10)

        def dummy_func(lr: float, epochs: int):
            return lr, epochs

        injected = ctx.inject_params(dummy_func)
        self.assertEqual(injected, {"lr": 0.001, "epochs": 10})

    def test_step_decorator(self):
        """Test step decorator."""

        @step(outputs=["model"])
        def train(lr: float = 0.001):
            return {"trained": True}

        self.assertEqual(train.name, "train")
        self.assertEqual(train.outputs, ["model"])
        self.assertTrue(callable(train))

    def test_basic_pipeline(self):
        """Test basic pipeline execution."""
        ctx = context(value=42)

        @step(outputs=["result"])
        def compute(value: int):
            return value * 2

        pipeline = Pipeline("test_pipeline", context=ctx)
        pipeline.add_step(compute)

        result = pipeline.run()

        self.assertTrue(result.success)
        # Access by step name
        self.assertEqual(result["compute"], 84)

    def test_multi_step_pipeline(self):
        """Test pipeline with multiple steps."""
        ctx = context(base=10)

        @step(outputs=["doubled"])
        def double(base: int):
            return base * 2

        @step(inputs=["doubled"], outputs=["squared"])
        def square(doubled):
            return doubled**2

        pipeline = Pipeline("multi_step", context=ctx)
        pipeline.add_step(double)
        pipeline.add_step(square)

        result = pipeline.run()

        self.assertTrue(result.success)
        self.assertEqual(result["double"], 20)
        self.assertEqual(result["square"], 400)

    def test_asset_creation(self):
        """Test asset creation."""
        dataset = Dataset.create(
            data=[1, 2, 3],
            name="test_dataset",
            properties={"size": 3},
        )

        self.assertEqual(dataset.name, "test_dataset")
        self.assertEqual(dataset.data, [1, 2, 3])
        # Properties are nested because of how create handles kwargs,
        # but we fixed Asset.create to handle 'properties' arg explicitly.
        # So it should be flat now.
        self.assertEqual(dataset.metadata.properties["size"], 3)

    def test_asset_lineage(self):
        """Test asset lineage tracking."""
        parent = Dataset.create(data=[1, 2, 3], name="parent")
        child = Dataset.create(data=[2, 3, 4], name="child", parent=parent)

        self.assertIn(child, parent.children)
        self.assertIn(parent, child.parents)

        ancestors = child.get_all_ancestors()
        self.assertIn(parent, ancestors)

    def test_metrics_asset(self):
        """Test metrics asset."""
        metrics = Metrics.create(
            accuracy=0.95,
            loss=0.05,
            f1_score=0.93,
        )

        self.assertEqual(metrics.get_metric("accuracy"), 0.95)
        self.assertEqual(metrics.get_metric("loss"), 0.05)

    def test_caching(self):
        """Test caching functionality."""
        ctx = context(value=10)

        # Use a list to hold mutable state
        call_count = {"count": 0}

        @step(outputs=["result"], cache="code_hash")
        def expensive_compute(value: int):
            call_count["count"] += 1
            return value * 2

        pipeline = Pipeline("cache_test", context=ctx, enable_cache=True)
        pipeline.add_step(expensive_compute)

        # First run
        result1 = pipeline.run()
        self.assertEqual(call_count["count"], 1)

        # Second run (should use cache)
        result2 = pipeline.run()
        self.assertEqual(call_count["count"], 1)  # Should not increment

        self.assertEqual(result1["expensive_compute"], result2["expensive_compute"])


if __name__ == "__main__":
    unittest.main()

"""
Test suite for Flowy package
"""

import pytest
from flowy import Pipeline, step, context, Dataset, Model, Metrics


def test_context_creation():
    """Test context creation and parameter access."""
    ctx = context(learning_rate=0.001, epochs=10)
    
    assert ctx.learning_rate == 0.001
    assert ctx.epochs == 10
    assert ctx['learning_rate'] == 0.001


def test_context_injection():
    """Test automatic parameter injection."""
    ctx = context(lr=0.001, epochs=10)
    
    def dummy_func(lr: float, epochs: int):
        return lr, epochs
    
    injected = ctx.inject_params(dummy_func)
    assert injected == {'lr': 0.001, 'epochs': 10}


def test_step_decorator():
    """Test step decorator."""
    @step(outputs=["model"])
    def train(lr: float = 0.001):
        return {"trained": True}
    
    assert train.name == "train"
    assert train.outputs == ["model"]
    assert callable(train)


def test_basic_pipeline():
    """Test basic pipeline execution."""
    ctx = context(value=42)
    
    @step(outputs=["result"])
    def compute(value: int):
        return value * 2
    
    pipeline = Pipeline("test_pipeline", context=ctx)
    pipeline.add_step(compute)
    
    result = pipeline.run()
    
    assert result.success
    assert result["result"] == 84


def test_multi_step_pipeline():
    """Test pipeline with multiple steps."""
    ctx = context(base=10)
    
    @step(outputs=["doubled"])
    def double(base: int):
        return base * 2
    
    @step(inputs=["doubled"], outputs=["squared"])
    def square(doubled):
        return doubled ** 2
    
    pipeline = Pipeline("multi_step", context=ctx)
    pipeline.add_step(double)
    pipeline.add_step(square)
    
    result = pipeline.run()
    
    assert result.success
    assert result["doubled"] == 20
    assert result["squared"] == 400


def test_asset_creation():
    """Test asset creation."""
    dataset = Dataset.create(
        data=[1, 2, 3],
        name="test_dataset",
        properties={"size": 3}
    )
    
    assert dataset.name == "test_dataset"
    assert dataset.data == [1, 2, 3]
    assert dataset.metadata.properties["size"] == 3


def test_asset_lineage():
    """Test asset lineage tracking."""
    parent = Dataset.create(data=[1, 2, 3], name="parent")
    child = Dataset.create(data=[2, 3, 4], name="child", parent=parent)
    
    assert child in parent.children
    assert parent in child.parents
    
    ancestors = child.get_all_ancestors()
    assert parent in ancestors


def test_metrics_asset():
    """Test metrics asset."""
    metrics = Metrics.create(
        accuracy=0.95,
        loss=0.05,
        f1_score=0.93
    )
    
    assert metrics.get_metric("accuracy") == 0.95
    assert metrics.get_metric("loss") == 0.05


def test_caching():
    """Test caching functionality."""
    ctx = context(value=10)
    
    call_count = {"count": 0}
    
    @step(outputs=["result"], cache="code_hash")
    def expensive_compute(value: int):
        call_count["count"] += 1
        return value * 2
    
    pipeline = Pipeline("cache_test", context=ctx, enable_cache=True)
    pipeline.add_step(expensive_compute)
    
    # First run
    result1 = pipeline.run()
    assert call_count["count"] == 1
    
    # Second run (should use cache)
    result2 = pipeline.run()
    assert call_count["count"] == 1  # Should not increment
    
    assert result1["result"] == result2["result"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

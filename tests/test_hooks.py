"""Tests for lifecycle hooks."""

import pytest
from flowyml.core.pipeline import Pipeline
from flowyml.core.step import step
from flowyml.core.hooks import (
    HookRegistry,
    on_pipeline_start,
    on_pipeline_end,
    on_step_start,
    on_step_end,
)


class TestHooks:
    """Test lifecycle hooks functionality."""

    def test_hook_registry_creation(self):
        """Test creating a hook registry."""
        registry = HookRegistry()
        assert len(registry.on_pipeline_start) == 0
        assert len(registry.on_pipeline_end) == 0
        assert len(registry.on_step_start) == 0
        assert len(registry.on_step_end) == 0

    def test_register_pipeline_hooks(self):
        """Test registering pipeline hooks."""
        registry = HookRegistry()

        def start_hook(pipeline):
            pass

        def end_hook(pipeline, result):
            pass

        registry.register_pipeline_start_hook(start_hook)
        registry.register_pipeline_end_hook(end_hook)

        assert len(registry.on_pipeline_start) == 1
        assert len(registry.on_pipeline_end) == 1

    def test_hook_decorators(self):
        """Test hook decorator registration."""
        from flowyml.core.hooks import get_global_hooks

        # Clear global hooks first
        hooks = get_global_hooks()
        initial_start = len(hooks.on_pipeline_start)

        @on_pipeline_start
        def my_start_hook(pipeline):
            pass

        @on_pipeline_end
        def my_end_hook(pipeline, result):
            pass

        assert len(hooks.on_pipeline_start) == initial_start + 1
        assert len(hooks.on_pipeline_end) >= 1

    def test_hooks_execution(self):
        """Test that hooks actually execute."""
        registry = HookRegistry()

        executed = {"start": False, "end": False}

        def start_hook(pipeline):
            executed["start"] = True

        def end_hook(pipeline, result):
            executed["end"] = True

        registry.register_pipeline_start_hook(start_hook)
        registry.register_pipeline_end_hook(end_hook)

        # Create a simple pipeline
        @step(outputs=["msg"])
        def test_step() -> str:
            return "test"

        pipeline = Pipeline("test_hooks_pipeline")
        pipeline.add_step(test_step)

        # Execute hooks
        registry.run_pipeline_start_hooks(pipeline)
        assert executed["start"] is True

        # Mock result
        from flowyml.core.pipeline import PipelineResult

        result = PipelineResult("test-run", "test_hooks_pipeline")

        registry.run_pipeline_end_hooks(pipeline, result)
        assert executed["end"] is True

    def test_hook_error_handling(self):
        """Test that hook errors don't crash execution."""
        registry = HookRegistry()

        def failing_hook(pipeline):
            raise ValueError("Hook error")

        registry.register_pipeline_start_hook(failing_hook)

        @step(outputs=["msg"])
        def test_step() -> str:
            return "test"

        pipeline = Pipeline("test_error_handling")
        pipeline.add_step(test_step)

        # Should not raise
        registry.run_pipeline_start_hooks(pipeline)

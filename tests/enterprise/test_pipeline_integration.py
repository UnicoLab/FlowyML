"""Tests for pipeline ↔ enterprise stack integration."""

import pytest

from flowyml.stacks.enterprise.models import StackDefinition


class TestPipelineStackAcceptance:
    """Pipeline constructor accepts various stack argument types."""

    def test_pipeline_accepts_stack_string(self):
        """Pipeline(stack='local') creates without error."""
        from flowyml.core.pipeline import Pipeline

        pipeline = Pipeline("test_pipe", stack="local")
        assert pipeline.name == "test_pipe"

    def test_pipeline_accepts_stack_definition(self, sample_stack):
        """Pipeline(stack=StackDefinition) stores the definition."""
        from flowyml.core.pipeline import Pipeline

        pipeline = Pipeline("test_pipe", stack=sample_stack)
        assert pipeline._stack_definition is not None, "StackDefinition should be stored on the pipeline"
        assert pipeline._stack_definition.name == "test_cpu_stack"

    def test_pipeline_accepts_env(self):
        """Pipeline(env='dev') creates without error."""
        from flowyml.core.pipeline import Pipeline

        pipeline = Pipeline("test_pipe", env="dev")
        assert pipeline.name == "test_pipe"


class TestPipelineDryRun:
    """Pipeline dry-run validation."""

    def test_pipeline_dry_run_method(self, sample_stack):
        """dry_run() returns a PipelineResult without executing steps."""
        from flowyml.core.pipeline import Pipeline

        pipeline = Pipeline("test_dry", stack=sample_stack, auto_start_ui=False)
        result = pipeline.dry_run()
        assert result is not None, "dry_run() should return a result"

    def test_pipeline_dry_run_via_run(self, sample_stack):
        """run(dry_run=True) returns a PipelineResult."""
        from flowyml.core.pipeline import Pipeline

        pipeline = Pipeline("test_dry_run", stack=sample_stack, auto_start_ui=False)
        result = pipeline.run(dry_run=True, auto_start_ui=False)
        assert result is not None, "run(dry_run=True) should return a result"


class TestUseStackContextManager:
    """use_stack() context manager."""

    def test_use_stack_context_manager_with_definition(self, sample_stack):
        """use_stack(StackDefinition) yields the definition back."""
        from flowyml.stacks import use_stack

        with use_stack(sample_stack) as s:
            assert s is sample_stack, "Context should yield the StackDefinition"

    def test_use_stack_context_manager_with_string(self):
        """use_stack('local') yields a value without error."""
        from flowyml.stacks import use_stack

        with use_stack("local") as s:
            assert s is not None, "Context should yield a non-None value"

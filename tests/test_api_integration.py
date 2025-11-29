"""
Integration tests for new features.
"""

import pytest
import tempfile
from flowyml.registry.pipeline_registry import pipeline_registry, register_pipeline
from flowyml.core.pipeline import Pipeline
from flowyml.core.step import step
from flowyml.core.project import Project
from flowyml.core.versioning import VersionedPipeline
from flowyml.core.scheduler import PipelineScheduler


def test_pipeline_registry():
    """Test PipelineRegistry functionality."""

    # Register a pipeline
    @register_pipeline("test_pipeline")
    def create_pipeline():
        p = Pipeline("test_pipeline")

        @step(outputs=["result"])
        def task():
            return {"value": 42}

        p.add_step(task)
        return p

    # Verify registration
    assert "test_pipeline" in pipeline_registry.pipelines

    # Get and execute
    factory = pipeline_registry.get("test_pipeline")
    assert factory is not None

    pipeline = factory()
    result = pipeline.run()
    assert result.success

    # Cleanup
    pipeline_registry.pipelines.pop("test_pipeline", None)


def test_project_integration():
    """Test Project integration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Project("test_project", projects_dir=tmpdir)

        # Create pipeline
        pipeline = project.create_pipeline("test_pipe")

        @step(outputs=["data"])
        def load():
            return {"items": [1, 2, 3]}

        pipeline.add_step(load)
        result = pipeline.run()

        assert result.success
        assert "load" in result.outputs  # step name, not output name

        # Check project stats
        stats = project.get_stats()
        assert stats["total_runs"] > 0


def test_versioned_pipeline_integration():
    """Test VersionedPipeline integration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vp = VersionedPipeline("test_versioned", versions_dir=tmpdir)
        vp.version = "v1.0.0"

        @step(outputs=["result"])
        def process():
            return {"value": 100}

        vp.add_step(process)
        vp.save_version()

        # Verify version saved
        versions = vp.list_versions()
        assert "v1.0.0" in versions

        # Run pipeline
        result = vp.run()
        assert result.success


def test_scheduler_integration():
    """Test PipelineScheduler integration."""
    scheduler = PipelineScheduler()

    executed = []

    def test_func():
        executed.append(1)

    # Schedule
    scheduler.schedule_interval(
        name="test_schedule",
        pipeline_func=test_func,
        seconds=3600,
    )

    # Verify scheduled
    schedules = scheduler.list_schedules()
    assert len(schedules) > 0

    # Cleanup
    scheduler.unschedule("test_schedule")
    scheduler.stop()


def test_full_workflow():
    """Test complete workflow: Project -> Pipeline -> Versioning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create project
        project = Project("workflow_test", projects_dir=tmpdir)

        # Create versioned pipeline
        vp = VersionedPipeline("workflow_pipeline", versions_dir=tmpdir)
        vp.version = "v1.0.0"

        @step(outputs=["data"])
        def extract():
            return [1, 2, 3, 4, 5]

        @step(inputs=["data"], outputs=["processed"])
        def transform(data):
            return [x * 2 for x in data]

        vp.add_step(extract)
        vp.add_step(transform)
        vp.save_version()

        # Run
        result = vp.run()

        assert result.success
        assert "transform" in result.outputs  # step name
        assert result.outputs["transform"] == [2, 4, 6, 8, 10]

        # Verify project stats
        stats = project.get_stats()
        assert stats is not None

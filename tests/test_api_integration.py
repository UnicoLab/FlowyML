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


def test_versioned_pipeline_with_context():
    """Test VersionedPipeline with context parameter."""
    from flowyml import context

    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = context(learning_rate=0.001, epochs=10)
        vp = VersionedPipeline("test_versioned_ctx", context=ctx, version="v1.0.0", versions_dir=tmpdir)

        @step(outputs=["result"])
        def process(learning_rate: float, epochs: int):
            return {"value": learning_rate * epochs}

        vp.add_step(process)
        vp.save_version()

        # Verify context is passed to pipeline
        assert vp.pipeline.context.get("learning_rate") == 0.001
        assert vp.pipeline.context.get("epochs") == 10

        # Run pipeline
        result = vp.run()
        assert result.success
        assert result["process"]["value"] == 0.01


def test_versioned_pipeline_with_project_name():
    """Test VersionedPipeline with project_name parameter."""
    from pathlib import Path
    from flowyml import context
    from flowyml.utils.config import get_config

    with tempfile.TemporaryDirectory() as tmpdir:
        projects_dir = Path(tmpdir) / "projects"
        projects_dir.mkdir()

        from flowyml.utils.config import update_config

        original_projects_dir = get_config().projects_dir
        update_config(projects_dir=str(projects_dir))

        try:
            ctx = context(learning_rate=0.001)
            vp = VersionedPipeline(
                "test_versioned_project",
                context=ctx,
                version="v1.0.0",
                project_name="test_project",
            )

            @step(outputs=["result"])
            def process(learning_rate: float):
                return {"value": learning_rate}

            vp.add_step(process)
            vp.save_version()

            # Verify project was created
            project_dir = projects_dir / "test_project"
            assert project_dir.exists()
            assert (project_dir / "project.json").exists()

            # Verify pipeline uses project's runs directory
            assert vp.pipeline.runs_dir == project_dir / "runs"
        finally:
            update_config(projects_dir=str(original_projects_dir))


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

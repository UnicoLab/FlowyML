"""
Integration tests for all features working together.
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path
import numpy as np

from flowyml import (
    # Core
    Pipeline,
    step,
    context,
    # Versioning & Projects
    VersionedPipeline,
    Project,
    # Caching
    ContentBasedCache,
    memoize,
    # Debugging
    StepDebugger,
    trace_step,
    profile_step,
    # Monitoring
    configure_notifications,
    get_notifier,
    detect_drift,
    # Leaderboard
    ModelLeaderboard,
    # Scheduler
    PipelineScheduler,
    # Checkpoints
    PipelineCheckpoint,
)


class TestFeatureIntegration(unittest.TestCase):
    """Test that all features work together seamlessly."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.debugger = StepDebugger()
        self.debugger.enabled = False  # Disable interactive debugging for tests

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_versioned_pipeline_with_project(self):
        """Test versioned pipeline within a project."""
        # Create project
        project = Project("test_project", projects_dir=self.test_dir)

        # Create pipeline
        pipeline = project.create_pipeline("versioned_training")

        @step(outputs=["data"])
        def load_data():
            return np.random.rand(100, 10)

        @step(inputs=["data"], outputs=["model"])
        def train(data):
            return {"weights": np.random.rand(10)}

        pipeline.add_step(load_data)
        pipeline.add_step(train)

        # Run pipeline
        result = pipeline.run()

        # Verify
        self.assertTrue(result.success)
        self.assertIn("model", result.outputs)

        # Check project stats
        stats = project.get_stats()
        self.assertGreater(stats["total_runs"], 0)

    def test_pipeline_with_checkpointing_and_caching(self):
        """Test pipeline with both checkpointing and caching."""
        ctx = context(learning_rate=0.001)
        ctx = context(learning_rate=0.001)
        pipeline = Pipeline("test_checkpoint_cache", context=ctx, cache_dir=os.path.join(self.test_dir, "cache"))

        checkpoint = PipelineCheckpoint(run_id="test_run", checkpoint_dir=self.test_dir)
        cache = ContentBasedCache(cache_dir=os.path.join(self.test_dir, "cache"))

        call_count = {"load": 0, "train": 0}

        @step(outputs=["data"])
        def load_data():
            call_count["load"] += 1
            data = np.random.rand(50, 5)
            checkpoint.save_step_state("load_data", data)
            return data

        @step(inputs=["data"], outputs=["model"])
        def train(data, learning_rate: float):
            call_count["train"] += 1
            model = {"lr": learning_rate}
            checkpoint.save_step_state("train", model)
            return model

        pipeline.add_step(load_data)
        pipeline.add_step(train)

        # First run
        result1 = pipeline.run()
        first_load_count = call_count["load"]

        # Second run (should use cache)
        result2 = pipeline.run()

        # Verify both succeeded
        self.assertTrue(result1.success)
        self.assertTrue(result2.success)

        # Verify checkpoint exists
        self.assertTrue(checkpoint.exists())
        completed_steps = checkpoint.get_completed_steps()
        self.assertIn("train", completed_steps)

    def test_debugging_with_tracing_and_profiling(self):
        """Test debugging features work with pipeline execution."""
        pipeline = Pipeline("debug_test", cache_dir=os.path.join(self.test_dir, "cache"))

        execution_log = []

        @step(outputs=["data"])
        @trace_step()
        @profile_step()
        def load_data():
            execution_log.append("load")
            return np.random.rand(10, 3)

        @step(inputs=["data"], outputs=["processed"])
        @profile_step()
        def process(data):
            execution_log.append("process")
            return data * 2

        pipeline.add_step(load_data)
        pipeline.add_step(process)

        result = pipeline.run()

        # Verify execution
        self.assertTrue(result.success)
        self.assertEqual(execution_log, ["load", "process"])

    def test_project_with_leaderboard_and_drift_detection(self):
        """Test project integration with leaderboard and drift detection."""
        project = Project("ml_monitoring", projects_dir=self.test_dir)
        leaderboard = ModelLeaderboard(
            metric="accuracy",
            metadata_store=project.metadata_store,
        )

        # Create pipeline
        pipeline = project.create_pipeline("training_with_monitoring")

        reference_data = np.random.normal(0, 1, 1000)

        @step(outputs=["train_data", "test_data"])
        def load_data():
            train = np.random.normal(0, 1, 800)
            test = np.random.normal(0, 1, 200)

            # Check for drift
            drift_result = detect_drift(reference_data, train)
            if drift_result["drift_detected"]:
                print(f"Drift detected: PSI={drift_result['psi']}")

            return train, test

        @step(inputs=["train_data", "test_data"], outputs=["metrics"])
        def train_and_evaluate(train_data, test_data):
            accuracy = 0.85 + np.random.rand() * 0.1
            return {"accuracy": accuracy}

        pipeline.add_step(load_data)
        pipeline.add_step(train_and_evaluate)

        # Run pipeline
        result = pipeline.run()
        self.assertTrue(result.success)

        # Add to leaderboard
        metrics = result.outputs.get("metrics", {})
        if "accuracy" in metrics:
            leaderboard.add_score(
                model_name="test_model",
                run_id=result.run_id,
                score=metrics["accuracy"],
            )

        # Verify leaderboard
        top_models = leaderboard.get_top(n=1)
        self.assertEqual(len(top_models), 1)

    def test_versioned_pipeline_with_debugging(self):
        """Test versioned pipeline with debugging features."""
        versioned = VersionedPipeline("debug_versioned", versions_dir=self.test_dir)
        versioned.version = "v1.0.0"

        @step(outputs=["data"])
        @profile_step()
        def load():
            return {"values": [1, 2, 3]}

        @step(inputs=["data"], outputs=["processed"])
        def process(data):
            return {"values": [x * 2 for x in data["values"]]}

        versioned.add_step(load)
        versioned.add_step(process)
        versioned.save_version(metadata={"description": "Initial version"})

        # Verify version saved
        versions = versioned.list_versions()
        self.assertIn("v1.0.0", versions)

        # Run pipeline
        result = versioned.run()
        self.assertTrue(result.success)

    def test_memoization_with_pipeline(self):
        """Test memoization works within pipeline steps."""
        call_count = {"compute": 0}

        @memoize(ttl_seconds=60)
        def expensive_compute(x):
            call_count["compute"] += 1
            return x**2

        pipeline = Pipeline("memo_test", cache_dir=os.path.join(self.test_dir, "cache"))

        @step(outputs=["result"])
        def compute_step():
            # Call multiple times with same input
            r1 = expensive_compute(5)
            r2 = expensive_compute(5)
            r3 = expensive_compute(5)
            return r1 + r2 + r3

        pipeline.add_step(compute_step)
        result = pipeline.run()

        # Should only compute once due to memoization
        self.assertEqual(call_count["compute"], 1)
        self.assertEqual(result.outputs.get("result"), 75)  # 25 + 25 + 25

    def test_scheduler_with_versioned_pipeline(self):
        """Test scheduler works with versioned pipelines."""
        versioned = VersionedPipeline("scheduled", versions_dir=self.test_dir)
        versioned.version = "v1.0.0"

        execution_count = {"count": 0}

        @step(outputs=["result"])
        def task():
            execution_count["count"] += 1
            return {"done": True}

        versioned.add_step(task)
        versioned.save_version()

        # Create scheduler
        scheduler = PipelineScheduler()
        scheduler.schedule_interval(
            name="test_schedule",
            pipeline_func=lambda: versioned.run(),
            seconds=1,
        )

        # Verify schedule created
        schedules = scheduler.list_schedules()
        self.assertEqual(len(schedules), 1)

        # Clean up
        scheduler.unschedule("test_schedule")

    def test_project_with_multiple_pipelines(self):
        """Test project can manage multiple related pipelines."""
        project = Project("multi_pipeline", projects_dir=self.test_dir)

        # Create multiple pipelines
        pipeline1 = project.create_pipeline("data_preparation")
        pipeline2 = project.create_pipeline("training")
        pipeline3 = project.create_pipeline("evaluation")

        @step(outputs=["data"])
        def prepare():
            return {"prepared": True}

        @step(outputs=["model"])
        def train():
            return {"trained": True}

        @step(outputs=["metrics"])
        def evaluate():
            return {"accuracy": 0.9}

        pipeline1.add_step(prepare)
        pipeline2.add_step(train)
        pipeline3.add_step(evaluate)

        # Run all
        r1 = pipeline1.run()
        r2 = pipeline2.run()
        r3 = pipeline3.run()

        # Verify
        self.assertTrue(all([r1.success, r2.success, r3.success]))

        # Check project has all pipelines
        pipelines = project.get_pipelines()
        self.assertEqual(len(pipelines), 3)

        # Check runs
        runs = project.list_runs()
        self.assertGreaterEqual(len(runs), 3)

    def test_full_ml_workflow_integration(self):
        """Test complete ML workflow using all features together."""
        # Setup project
        project = Project("full_ml_workflow", projects_dir=self.test_dir)

        # Create versioned pipeline
        pipeline = project.create_pipeline("end_to_end")
        versioned = VersionedPipeline("ml_pipeline", versions_dir=self.test_dir)

        # Link versioned pipeline to project
        versioned.pipeline.metadata_store = project.metadata_store
        versioned.pipeline.runs_dir = project.runs_dir
        versioned.pipeline.project_name = project.name  # Required for stats tracking
        versioned.version = "v1.0.0"

        # Setup monitoring
        configure_notifications(console=False)  # Disable for test
        leaderboard = ModelLeaderboard("f1_score", metadata_store=project.metadata_store)

        # Define workflow steps
        @step(outputs=["data"])
        @profile_step()
        def load_data():
            return np.random.rand(100, 5)

        @step(inputs=["data"], outputs=["train", "test"])
        def split_data(data):
            split_idx = int(len(data) * 0.8)
            return data[:split_idx], data[split_idx:]

        @step(inputs=["train"], outputs=["model"])
        @profile_step()
        def train_model(train):
            return {"weights": np.random.rand(5), "bias": 0.1}

        @step(inputs=["model", "test"], outputs=["metrics"])
        def evaluate_model(model, test):
            f1 = 0.75 + np.random.rand() * 0.2
            return {"f1_score": f1, "accuracy": 0.85}

        # Build pipeline
        versioned.add_step(load_data)
        versioned.add_step(split_data)
        versioned.add_step(train_model)
        versioned.add_step(evaluate_model)
        versioned.save_version()

        # Execute
        result = versioned.run()

        # Verify success
        self.assertTrue(result.success)
        self.assertIn("metrics", result.outputs)

        # Add to leaderboard
        metrics = result.outputs["metrics"]
        leaderboard.add_score(
            model_name="full_workflow_v1",
            run_id=result.run_id,
            score=metrics["f1_score"],
        )

        # Verify leaderboard entry
        top = leaderboard.get_top(n=1)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0].model_name, "full_workflow_v1")

        # Verify project stats
        stats = project.get_stats()
        self.assertGreater(stats["total_runs"], 0)


if __name__ == "__main__":
    unittest.main()

"""Test suite for tracking functionality."""

import unittest
from uniflow.tracking.runs import Run, RunMetadata
from datetime import datetime


class TestTracking(unittest.TestCase):
    """Test suite for tracking functionality."""

    def test_run_creation(self):
        """Test creating a run."""
        run = Run(
            run_id="test_run_123",
            pipeline_name="test_pipeline",
        )

        self.assertEqual(run.run_id, "test_run_123")
        self.assertEqual(run.pipeline_name, "test_pipeline")
        self.assertIsNotNone(run.metadata)

    def test_run_log_metric(self):
        """Test logging metrics to a run."""
        run = Run(
            run_id="metric_test",
            pipeline_name="test",
        )

        run.log_metric("accuracy", 0.95)
        self.assertEqual(run.metadata.metrics["accuracy"], 0.95)

    def test_run_log_multiple_metrics(self):
        """Test logging multiple metrics."""
        run = Run(
            run_id="multi_metric_test",
            pipeline_name="test",
        )

        run.log_metrics({"accuracy": 0.95, "loss": 0.05})
        self.assertEqual(run.metadata.metrics["accuracy"], 0.95)
        self.assertEqual(run.metadata.metrics["loss"], 0.05)

    def test_run_complete(self):
        """Test marking run as complete."""
        run = Run(
            run_id="complete_test",
            pipeline_name="test",
        )

        run.complete(status="success")
        self.assertEqual(run.metadata.status, "success")
        self.assertIsNotNone(run.metadata.ended_at)

    def test_run_metadata_creation(self):
        """Test creating run metadata."""
        metadata = RunMetadata(
            run_id="test_123",
            pipeline_name="test_pipeline",
            started_at=datetime.now(),
        )

        self.assertEqual(metadata.run_id, "test_123")
        self.assertEqual(metadata.pipeline_name, "test_pipeline")
        self.assertEqual(metadata.status, "running")


if __name__ == "__main__":
    unittest.main()

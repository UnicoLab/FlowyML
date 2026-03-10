"""Tests for selective re-execution / checkpoint resume."""

import unittest
from flowyml.core.checkpoint import PipelineCheckpoint
from tests.base import BaseTestCase


class TestSelectiveReExecution(BaseTestCase):
    """Test selective re-execution through checkpoint system."""

    def test_checkpoint_tracks_completed_steps(self):
        """Checkpoint can track completed steps."""
        import tempfile
        import os

        checkpoint_dir = tempfile.mkdtemp()
        cp = PipelineCheckpoint(
            run_id="test-run-123",
            checkpoint_dir=checkpoint_dir,
        )

        # Save a checkpoint with completed steps
        cp.save(
            {
                "completed_steps": ["load_data", "preprocess"],
                "step_outputs": {
                    "load_data": {"data": "loaded"},
                    "preprocess": {"data": "processed"},
                },
            },
        )

        # Load and verify
        self.assertTrue(cp.exists())
        data = cp.load()
        self.assertEqual(data["completed_steps"], ["load_data", "preprocess"])

    def test_checkpoint_round_trip(self):
        """Checkpoint save/load round-trips data correctly."""
        import tempfile

        checkpoint_dir = tempfile.mkdtemp()
        cp = PipelineCheckpoint(
            run_id="roundtrip-test",
            checkpoint_dir=checkpoint_dir,
        )

        original_data = {
            "completed_steps": ["step1", "step2"],
            "step_outputs": {"step1": {"result": 42}},
            "metadata": {"start_time": "2025-01-01T00:00:00"},
        }

        cp.save(original_data)
        loaded = cp.load()

        self.assertEqual(loaded["completed_steps"], original_data["completed_steps"])
        self.assertEqual(
            loaded["step_outputs"]["step1"]["result"],
            original_data["step_outputs"]["step1"]["result"],
        )

    def test_nonexistent_checkpoint(self):
        """Checkpoint.exists() returns False for nonexistent checkpoint."""
        import tempfile

        cp = PipelineCheckpoint(
            run_id="nonexistent-run",
            checkpoint_dir=tempfile.mkdtemp(),
        )
        self.assertFalse(cp.exists())


if __name__ == "__main__":
    unittest.main()

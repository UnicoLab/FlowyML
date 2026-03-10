"""Tests for immutable pipeline snapshots."""

import json
import hashlib
import unittest
from flowyml.core.versioning import PipelineSnapshot
from tests.base import BaseTestCase


class TestPipelineSnapshot(BaseTestCase):
    """Test suite for PipelineSnapshot."""

    def test_snapshot_defaults(self):
        """PipelineSnapshot has sensible defaults."""
        snap = PipelineSnapshot()
        self.assertEqual(snap.pipeline_name, "")
        self.assertEqual(snap.steps, [])
        self.assertEqual(snap.dag_edges, [])
        self.assertEqual(snap.context_params, {})
        self.assertEqual(snap.step_hashes, {})

    def test_snapshot_verify_valid(self):
        """Snapshot verify() returns True for valid hash."""
        snap = PipelineSnapshot(
            pipeline_name="test",
            steps=[{"name": "s1"}],
            dag_edges=[],
            context_params={"lr": 0.01},
            step_hashes={"s1": "abc123"},
        )

        # Compute the correct hash
        data = {
            "pipeline_name": "test",
            "steps": [{"name": "s1"}],
            "dag_edges": [],
            "context_params": {"lr": 0.01},
            "step_hashes": {"s1": "abc123"},
        }
        snap.snapshot_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode(),
        ).hexdigest()

        self.assertTrue(snap.verify())

    def test_snapshot_verify_tampered(self):
        """Snapshot verify() returns False if data was tampered."""
        snap = PipelineSnapshot(
            pipeline_name="test",
            steps=[{"name": "s1"}],
            dag_edges=[],
            context_params={},
            step_hashes={},
            snapshot_hash="fake_hash",
        )
        self.assertFalse(snap.verify())

    def test_snapshot_to_dict(self):
        """Snapshot serializes to dict."""
        snap = PipelineSnapshot(
            pipeline_name="my_pipeline",
            snapshot_hash="abc",
            created_at="2025-01-01",
        )
        d = snap.to_dict()
        self.assertEqual(d["pipeline_name"], "my_pipeline")
        self.assertEqual(d["snapshot_hash"], "abc")
        self.assertEqual(d["created_at"], "2025-01-01")

    def test_snapshot_with_version(self):
        """Snapshot stores version."""
        snap = PipelineSnapshot(
            pipeline_name="p",
            version="v1.2.3",
        )
        self.assertEqual(snap.version, "v1.2.3")


if __name__ == "__main__":
    unittest.main()

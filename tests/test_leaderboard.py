"""
Tests for model leaderboard and comparison.
"""

import unittest
import os
from datetime import datetime
from uniflow.tracking.leaderboard import ModelLeaderboard, ModelScore, compare_runs
from uniflow.storage.metadata import SQLiteMetadataStore


class TestModelLeaderboard(unittest.TestCase):
    def setUp(self):
        self.db_path = ".uniflow/test_leaderboard.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.metadata_store = SQLiteMetadataStore(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_score(self):
        """Test adding scores to leaderboard."""
        leaderboard = ModelLeaderboard(
            metric="accuracy",
            metadata_store=self.metadata_store,
        )

        leaderboard.add_score(
            model_name="bert-base",
            run_id="run_1",
            score=0.92,
        )

        # Verify metric was saved
        metrics = self.metadata_store.get_metrics("run_1")
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["name"], "leaderboard_accuracy")
        self.assertEqual(metrics[0]["value"], 0.92)

    def test_get_top_models(self):
        """Test retrieving top models."""
        leaderboard = ModelLeaderboard(
            metric="f1_score",
            higher_is_better=True,
            metadata_store=self.metadata_store,
        )

        # Add multiple scores
        leaderboard.add_score("model_a", "run_1", 0.85)
        leaderboard.add_score("model_b", "run_2", 0.92)
        leaderboard.add_score("model_c", "run_3", 0.88)

        # Get top 2
        top_models = leaderboard.get_top(n=2)

        self.assertEqual(len(top_models), 2)
        self.assertEqual(top_models[0].model_name, "model_b")
        self.assertEqual(top_models[0].metric_value, 0.92)
        self.assertEqual(top_models[1].model_name, "model_c")

    def test_lower_is_better(self):
        """Test leaderboard with lower_is_better metric."""
        leaderboard = ModelLeaderboard(
            metric="loss",
            higher_is_better=False,
            metadata_store=self.metadata_store,
        )

        leaderboard.add_score("model_a", "run_1", 0.5)
        leaderboard.add_score("model_b", "run_2", 0.3)
        leaderboard.add_score("model_c", "run_3", 0.4)

        top_models = leaderboard.get_top(n=3)

        # Should be ordered by lowest loss
        self.assertEqual(top_models[0].metric_value, 0.3)
        self.assertEqual(top_models[1].metric_value, 0.4)
        self.assertEqual(top_models[2].metric_value, 0.5)

    def test_compare_models(self):
        """Test comparing specific models."""
        leaderboard = ModelLeaderboard(
            metric="accuracy",
            metadata_store=self.metadata_store,
        )

        # Add runs with metrics
        self.metadata_store.save_run(
            "run_1",
            {
                "pipeline_name": "training",
                "status": "completed",
            },
        )
        self.metadata_store.save_metric("run_1", "accuracy", 0.85)

        self.metadata_store.save_run(
            "run_2",
            {
                "pipeline_name": "training",
                "status": "completed",
            },
        )
        self.metadata_store.save_metric("run_2", "accuracy", 0.90)

        comparison = leaderboard.compare_models(["run_1", "run_2"])

        self.assertEqual(len(comparison["models"]), 2)
        self.assertEqual(comparison["metric"], "accuracy")
        # Should be sorted by metric value (descending)
        self.assertEqual(comparison["models"][0]["metric_value"], 0.90)


class TestCompareRuns(unittest.TestCase):
    def setUp(self):
        self.db_path = ".uniflow/test_compare.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.metadata_store = SQLiteMetadataStore(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_compare_runs(self):
        """Test comparing multiple runs."""
        # Setup runs with metrics
        self.metadata_store.save_run("run_1", {"pipeline_name": "test"})
        self.metadata_store.save_metric("run_1", "accuracy", 0.85)
        self.metadata_store.save_metric("run_1", "f1_score", 0.82)

        self.metadata_store.save_run("run_2", {"pipeline_name": "test"})
        self.metadata_store.save_metric("run_2", "accuracy", 0.88)
        self.metadata_store.save_metric("run_2", "f1_score", 0.86)

        # Compare - patch the metadata store
        from unittest.mock import patch

        with patch("uniflow.tracking.leaderboard.SQLiteMetadataStore") as mock_store_class:
            mock_store_class.return_value = self.metadata_store
            comparison = compare_runs(["run_1", "run_2"], metrics=["accuracy", "f1_score"])

        self.assertIn("runs", comparison)
        self.assertIn("metrics", comparison)
        self.assertEqual(len(comparison["runs"]), 2)
        self.assertEqual(len(comparison["metrics"]), 2)

        # Check metric values
        self.assertIsNotNone(comparison["metrics"]["accuracy"]["run_1"])
        self.assertIsNotNone(comparison["metrics"]["accuracy"]["run_2"])


if __name__ == "__main__":
    unittest.main()

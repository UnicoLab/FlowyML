"""Tests for experiment tracking functionality."""

import unittest
from uniflow.tracking.experiment import Experiment
from tests.base import BaseTestCase


class TestExperiment(BaseTestCase):
    """Test suite for experiment tracking."""

    def test_experiment_creation(self):
        """Test creating an experiment."""
        exp = Experiment(name="test_experiment")
        
        self.assertEqual(exp.name, "test_experiment")
        self.assertIsNotNone(exp.experiment_dir)

    def test_experiment_with_description(self):
        """Test experiment with description."""
        exp = Experiment(
            name="described_experiment",
            description="This is a test experiment"
        )
        
        self.assertEqual(exp.description, "This is a test experiment")

    def test_experiment_log_run(self):
        """Test logging a run to experiment."""
        exp = Experiment(name="run_test")
        exp.log_run(
            run_id="run_001",
            metrics={"accuracy": 0.95},
            parameters={"lr": 0.01}
        )
        
        self.assertIn("run_001", exp.runs)
        metrics = exp.get_run_metrics("run_001")
        self.assertEqual(metrics["metrics"]["accuracy"], 0.95)

    def test_experiment_list_runs(self):
        """Test listing runs in experiment."""
        exp = Experiment(name="list_test")
        exp.log_run("run_001", metrics={"acc": 0.9})
        exp.log_run("run_002", metrics={"acc": 0.95})
        
        runs = exp.list_runs()
        self.assertEqual(len(runs), 2)
        self.assertIn("run_001", runs)
        self.assertIn("run_002", runs)

    def test_experiment_get_best_run(self):
        """Test getting best run from experiment."""
        exp = Experiment(name="best_test")
        exp.log_run("run_001", metrics={"accuracy": 0.9})
        exp.log_run("run_002", metrics={"accuracy": 0.95})
        exp.log_run("run_003", metrics={"accuracy": 0.92})
        
        best = exp.get_best_run("accuracy", maximize=True)
        self.assertEqual(best, "run_002")


if __name__ == "__main__":
    unittest.main()

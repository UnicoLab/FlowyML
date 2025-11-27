"""Tests for metrics asset functionality."""

import unittest
from uniflow import Metrics
from tests.base import BaseTestCase


class TestMetrics(BaseTestCase):
    """Test suite for Metrics asset."""

    def test_metrics_creation(self):
        """Test basic metrics creation."""
        metrics = Metrics.create(
            accuracy=0.95,
            name="test_metrics",
        )

        self.assertEqual(metrics.name, "test_metrics")
        self.assertEqual(metrics.metadata.asset_type, "Metrics")

    def test_metrics_classification(self):
        """Test classification metrics."""
        metrics = Metrics.create(
            accuracy=0.95,
            precision=0.93,
            recall=0.94,
            f1_score=0.935,
            name="classification_metrics",
        )

        self.assertAlmostEqual(metrics.metadata.properties["accuracy"], 0.95)
        self.assertAlmostEqual(metrics.metadata.properties["precision"], 0.93)
        self.assertAlmostEqual(metrics.metadata.properties["recall"], 0.94)
        self.assertAlmostEqual(metrics.metadata.properties["f1_score"], 0.935)

    def test_metrics_regression(self):
        """Test regression metrics."""
        metrics = Metrics.create(
            mse=0.05,
            rmse=0.22,
            mae=0.15,
            r2_score=0.92,
            name="regression_metrics",
        )

        self.assertAlmostEqual(metrics.metadata.properties["mse"], 0.05)
        self.assertAlmostEqual(metrics.metadata.properties["rmse"], 0.22)
        self.assertAlmostEqual(metrics.metadata.properties["mae"], 0.15)
        self.assertAlmostEqual(metrics.metadata.properties["r2_score"], 0.92)

    def test_metrics_with_custom_values(self):
        """Test metrics with custom values."""
        metrics = Metrics.create(
            custom_metric_1=0.88,
            custom_metric_2=0.76,
            name="custom_metrics",
        )

        self.assertEqual(metrics.metadata.properties["custom_metric_1"], 0.88)
        self.assertEqual(metrics.metadata.properties["custom_metric_2"], 0.76)

    def test_metrics_lineage(self):
        """Test metrics lineage from model."""
        from uniflow import Model

        model = Model.create(data={"weights": []}, name="test_model")
        metrics = Metrics.create(
            accuracy=0.95,
            name="model_metrics",
            parent=model,
        )

        self.assertIn(model, metrics.parents)
        self.assertIn(metrics, model.children)


if __name__ == "__main__":
    unittest.main()

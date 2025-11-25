"""Tests for model asset functionality."""

import unittest
from uniflow import Model
from tests.base import BaseTestCase


class TestModel(BaseTestCase):
    """Test suite for Model asset."""

    def test_model_creation(self):
        """Test basic model creation."""
        model = Model.create(
            data={"weights": [1, 2, 3]},
            name="test_model"
        )
        
        self.assertEqual(model.name, "test_model")
        self.assertEqual(model.metadata.asset_type, "Model")

    def test_model_with_framework(self):
        """Test model with framework specification."""
        model = Model.create(
            data={"weights": []},
            name="pytorch_model",
            framework="pytorch",
            version="v1.0.0"
        )
        
        self.assertEqual(model.metadata.properties["framework"], "pytorch")
        self.assertEqual(model.version, "v1.0.0")

    def test_model_with_hyperparameters(self):
        """Test model with hyperparameters."""
        model = Model.create(
            data={"weights": []},
            name="tuned_model",
            learning_rate=0.001,
            batch_size=32,
            epochs=100
        )
        
        self.assertEqual(model.metadata.properties["learning_rate"], 0.001)
        self.assertEqual(model.metadata.properties["batch_size"], 32)
        self.assertEqual(model.metadata.properties["epochs"], 100)

    def test_model_with_metrics(self):
        """Test model with performance metrics."""
        model = Model.create(
            data={"weights": []},
            name="evaluated_model",
            accuracy=0.95,
            f1_score=0.93
        )
        
        self.assertEqual(model.metadata.properties["accuracy"], 0.95)
        self.assertEqual(model.metadata.properties["f1_score"], 0.93)

    def test_model_lineage(self):
        """Test model lineage from dataset."""
        from uniflow import Dataset
        
        dataset = Dataset.create(data=[1, 2, 3], name="training_data")
        model = Model.create(
            data={"weights": []},
            name="trained_model",
            parent=dataset
        )
        
        self.assertIn(dataset, model.parents)
        self.assertIn(model, dataset.children)


if __name__ == "__main__":
    unittest.main()

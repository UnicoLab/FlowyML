"""Test suite for assets module."""

import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd

from uniflow import Dataset, Model, Metrics
from uniflow.assets.base import Asset
from uniflow.core.context import Context


class TestAssets(unittest.TestCase):
    """Test suite for assets."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_dataset_creation_with_dataframe(self):
        """Test dataset creation with pandas DataFrame."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        dataset = Dataset.create(
            data=df,
            name="test_dataset",
            rows=3,
            cols=2,
        )

        self.assertEqual(dataset.name, "test_dataset")
        self.assertEqual(dataset.metadata.properties["rows"], 3)
        self.assertEqual(dataset.metadata.properties["cols"], 2)

    def test_dataset_with_path(self):
        """Test dataset creation with file path."""
        dataset = Dataset.create(
            data="/path/to/data.csv",
            name="path_dataset",
            format="csv",
        )

        self.assertEqual(dataset.name, "path_dataset")
        self.assertEqual(dataset.metadata.properties["format"], "csv")

    def test_model_creation(self):
        """Test model asset creation."""
        model_obj = {"weights": [1, 2, 3]}

        model = Model.create(
            data=model_obj,
            name="test_model",
            framework="pytorch",
            lr=0.01,
            epochs=10,
        )

        self.assertEqual(model.name, "test_model")
        # Framework is stored in properties
        self.assertEqual(model.metadata.properties.get("framework"), "pytorch")

    def test_metrics_creation_with_kwargs(self):
        """Test metrics creation with keyword arguments."""
        metrics = Metrics.create(
            accuracy=0.95,
            precision=0.93,
            recall=0.94,
            f1_score=0.935,
        )

        # Metrics are stored in metadata properties
        self.assertAlmostEqual(metrics.metadata.properties["accuracy"], 0.95)
        self.assertAlmostEqual(metrics.metadata.properties["precision"], 0.93)

    def test_metrics_creation_with_dict(self):
        """Test metrics creation with dictionary."""
        metrics_dict = {
            "accuracy": 0.96,
            "loss": 0.04,
        }

        metrics = Metrics.create(**metrics_dict)

        self.assertAlmostEqual(metrics.metadata.properties["accuracy"], 0.96)
        self.assertAlmostEqual(metrics.metadata.properties["loss"], 0.04)

    def test_asset_with_tags(self):
        """Test asset creation with tags."""
        dataset = Dataset.create(
            data=[1, 2, 3],
            name="tagged_dataset",
            tags={"env": "test", "version": "v1"},
        )

        # Tags should be in metadata
        self.assertIn("env", dataset.metadata.tags)
        self.assertEqual(dataset.metadata.tags["env"], "test")

    def test_asset_lineage(self):
        """Test asset lineage tracking."""
        parent = Dataset.create(data=[1, 2, 3], name="parent")
        child = Dataset.create(data=[2, 4, 6], name="child", parent=parent)

        self.assertIn(parent, child.parents)
        self.assertIn(child, parent.children)


if __name__ == "__main__":
    unittest.main()

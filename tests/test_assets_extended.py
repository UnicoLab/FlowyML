"""Extended test suite for assets module."""

import unittest
import tempfile
import shutil
from pathlib import Path
import pandas as pd

from uniflow import Dataset, Model, Metrics, FeatureSet
from uniflow.assets.base import Asset
from tests.base import BaseTestCase


class TestAssetsExtended(BaseTestCase):
    """Extended test suite for assets."""

    def test_dataset_with_dataframe_properties(self):
        """Test dataset with DataFrame and custom properties."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})

        dataset = Dataset.create(
            data=df,
            name="df_dataset",
            source="test",
            version="v1.0.0",
        )

        self.assertEqual(dataset.name, "df_dataset")
        self.assertEqual(dataset.version, "v1.0.0")

    def test_model_with_framework(self):
        """Test model creation with framework specification."""
        model = Model.create(
            data={"weights": [1, 2, 3]},
            name="test_model",
            framework="tensorflow",
            version="v2.0.0",
        )

        self.assertEqual(model.name, "test_model")
        self.assertEqual(model.version, "v2.0.0")

    def test_metrics_with_multiple_values(self):
        """Test metrics with multiple performance values."""
        metrics = Metrics.create(
            accuracy=0.95,
            precision=0.93,
            recall=0.94,
            f1=0.935,
            auc=0.97,
        )

        self.assertIn("accuracy", metrics.metadata.properties)
        self.assertIn("precision", metrics.metadata.properties)
        self.assertIn("recall", metrics.metadata.properties)

    def test_asset_versioning(self):
        """Test asset version management."""
        asset1 = Dataset.create(data=[1, 2, 3], name="versioned", version="v1.0.0")
        asset2 = Dataset.create(data=[4, 5, 6], name="versioned", version="v2.0.0")

        self.assertEqual(asset1.version, "v1.0.0")
        self.assertEqual(asset2.version, "v2.0.0")
        self.assertNotEqual(asset1.asset_id, asset2.asset_id)

    def test_asset_parent_child_relationship(self):
        """Test parent-child relationships between assets."""
        parent = Dataset.create(data=[1, 2, 3], name="parent_data")
        child1 = Dataset.create(data=[2, 4, 6], name="child1", parent=parent)
        child2 = Dataset.create(data=[3, 6, 9], name="child2", parent=parent)

        self.assertEqual(len(parent.children), 2)
        self.assertIn(child1, parent.children)
        self.assertIn(child2, parent.children)

    def test_asset_with_custom_properties(self):
        """Test asset with custom metadata properties."""
        dataset = Dataset.create(
            data=[1, 2, 3],
            name="custom_props",
            custom_field="custom_value",
            numeric_field=42,
            boolean_field=True,
        )

        self.assertEqual(dataset.metadata.properties["custom_field"], "custom_value")
        self.assertEqual(dataset.metadata.properties["numeric_field"], 42)
        self.assertTrue(dataset.metadata.properties["boolean_field"])

    def test_asset_metadata_tags(self):
        """Test asset metadata with tags."""
        dataset = Dataset.create(
            data=[1, 2, 3],
            name="tagged_data",
            tags={"environment": "production", "team": "ml"},
        )

        self.assertEqual(dataset.metadata.tags["environment"], "production")
        self.assertEqual(dataset.metadata.tags["team"], "ml")


if __name__ == "__main__":
    unittest.main()

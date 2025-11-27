"""Comprehensive test suite for asset base functionality."""

import unittest
from datetime import datetime
from uniflow import Dataset, Model, Metrics
from uniflow.assets.base import Asset, AssetMetadata
from tests.base import BaseTestCase


class TestAssetBase(BaseTestCase):
    """Comprehensive test suite for asset base functionality."""

    def test_asset_id_generation(self):
        """Test that each asset gets unique ID."""
        asset1 = Dataset.create(data=[1, 2, 3], name="data1")
        asset2 = Dataset.create(data=[4, 5, 6], name="data2")

        self.assertNotEqual(asset1.asset_id, asset2.asset_id)
        self.assertIsNotNone(asset1.asset_id)
        self.assertIsNotNone(asset2.asset_id)

    def test_asset_metadata_creation(self):
        """Test asset metadata is properly created."""
        asset = Dataset.create(data=[1, 2, 3], name="test_data")

        self.assertIsNotNone(asset.metadata)
        self.assertEqual(asset.metadata.name, "test_data")
        self.assertEqual(asset.metadata.asset_type, "Dataset")

    def test_asset_metadata_timestamps(self):
        """Test asset metadata has timestamps."""
        asset = Dataset.create(data=[1, 2, 3], name="timestamped")

        self.assertIsInstance(asset.metadata.created_at, datetime)
        self.assertIsNotNone(asset.metadata.created_at)

    def test_asset_default_version(self):
        """Test asset default version."""
        asset = Dataset.create(data=[1, 2, 3], name="versioned")

        self.assertIsNotNone(asset.version)
        self.assertTrue(asset.version.startswith("v"))

    def test_asset_custom_version(self):
        """Test asset with custom version."""
        asset = Dataset.create(data=[1, 2, 3], name="custom_ver", version="v2.5.0")

        self.assertEqual(asset.version, "v2.5.0")

    def test_asset_empty_parents(self):
        """Test asset with no parents."""
        asset = Dataset.create(data=[1, 2, 3], name="orphan")

        self.assertEqual(len(asset.parents), 0)
        self.assertEqual(len(asset.children), 0)

    def test_asset_single_parent(self):
        """Test asset with single parent."""
        parent = Dataset.create(data=[1, 2, 3], name="parent")
        child = Dataset.create(data=[2, 4, 6], name="child", parent=parent)

        self.assertEqual(len(child.parents), 1)
        self.assertIn(parent, child.parents)

    def test_asset_parent_ids_in_metadata(self):
        """Test parent IDs are stored in metadata."""
        parent = Dataset.create(data=[1, 2, 3], name="parent")
        child = Dataset.create(data=[2, 4, 6], name="child", parent=parent)

        self.assertIn(parent.asset_id, child.metadata.parent_ids)

    def test_asset_children_list(self):
        """Test parent tracks children."""
        parent = Dataset.create(data=[1, 2, 3], name="parent")
        child1 = Dataset.create(data=[2, 4, 6], name="child1", parent=parent)
        child2 = Dataset.create(data=[3, 6, 9], name="child2", parent=parent)

        self.assertEqual(len(parent.children), 2)
        self.assertIn(child1, parent.children)
        self.assertIn(child2, parent.children)

    def test_asset_properties_storage(self):
        """Test asset properties are stored correctly."""
        asset = Dataset.create(
            data=[1, 2, 3],
            name="props_test",
            custom_prop="custom_value",
            numeric_prop=123,
        )

        self.assertEqual(asset.metadata.properties["custom_prop"], "custom_value")
        self.assertEqual(asset.metadata.properties["numeric_prop"], 123)

    def test_asset_tags_storage(self):
        """Test asset tags are stored correctly."""
        asset = Dataset.create(
            data=[1, 2, 3],
            name="tagged",
            tags={"env": "prod", "version": "1.0"},
        )

        self.assertEqual(asset.metadata.tags["env"], "prod")
        self.assertEqual(asset.metadata.tags["version"], "1.0")

    def test_asset_name_from_create(self):
        """Test asset name is set from create method."""
        asset = Dataset.create(data=[1, 2, 3], name="my_dataset")

        self.assertEqual(asset.name, "my_dataset")

    def test_asset_data_storage(self):
        """Test asset stores data correctly."""
        test_data = [1, 2, 3, 4, 5]
        asset = Dataset.create(data=test_data, name="data_test")

        self.assertEqual(asset.data, test_data)

    def test_model_asset_type(self):
        """Test Model asset type."""
        model = Model.create(data={"weights": []}, name="test_model")

        self.assertEqual(model.metadata.asset_type, "Model")

    def test_metrics_asset_type(self):
        """Test Metrics asset type."""
        metrics = Metrics.create(accuracy=0.95, name="test_metrics")

        self.assertEqual(metrics.metadata.asset_type, "Metrics")


if __name__ == "__main__":
    unittest.main()

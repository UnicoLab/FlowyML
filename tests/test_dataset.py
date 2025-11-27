"""Tests for dataset asset functionality."""

import unittest
import pandas as pd
from uniflow import Dataset
from tests.base import BaseTestCase


class TestDataset(BaseTestCase):
    """Test suite for Dataset asset."""

    def test_dataset_with_pandas_dataframe(self):
        """Test dataset creation with pandas DataFrame."""
        df = pd.DataFrame(
            {
                "col1": [1, 2, 3],
                "col2": [4, 5, 6],
            },
        )

        dataset = Dataset.create(data=df, name="pandas_dataset")

        self.assertEqual(dataset.name, "pandas_dataset")
        self.assertIsInstance(dataset.data, pd.DataFrame)

    def test_dataset_with_list(self):
        """Test dataset creation with list."""
        data = [1, 2, 3, 4, 5]
        dataset = Dataset.create(data=data, name="list_dataset")

        self.assertEqual(dataset.data, data)

    def test_dataset_with_dict(self):
        """Test dataset creation with dictionary."""
        data = {"key1": "value1", "key2": "value2"}
        dataset = Dataset.create(data=data, name="dict_dataset")

        self.assertEqual(dataset.data, data)

    def test_dataset_with_metadata(self):
        """Test dataset with custom metadata."""
        dataset = Dataset.create(
            data=[1, 2, 3],
            name="meta_dataset",
            source="test_source",
            format="csv",
            size_mb=1.5,
        )

        self.assertEqual(dataset.metadata.properties["source"], "test_source")
        self.assertEqual(dataset.metadata.properties["format"], "csv")
        self.assertEqual(dataset.metadata.properties["size_mb"], 1.5)

    def test_dataset_lineage_chain(self):
        """Test dataset lineage chain."""
        ds1 = Dataset.create(data=[1, 2, 3], name="original")
        ds2 = Dataset.create(data=[2, 4, 6], name="doubled", parent=ds1)
        ds3 = Dataset.create(data=[4, 8, 12], name="quadrupled", parent=ds2)

        # Check lineage
        self.assertIn(ds1, ds2.parents)
        self.assertIn(ds2, ds3.parents)

        # Check children
        self.assertIn(ds2, ds1.children)
        self.assertIn(ds3, ds2.children)


if __name__ == "__main__":
    unittest.main()

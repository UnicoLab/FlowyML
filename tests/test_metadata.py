"""Test suite for metadata storage."""

import unittest
import tempfile
import shutil
from pathlib import Path

from flowyml.storage.metadata import SQLiteMetadataStore


class TestMetadata(unittest.TestCase):
    """Test suite for metadata storage."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.db_path = Path(self.test_dir) / "test.db"

    def test_metadata_store_creation(self):
        """Test creating a metadata store."""
        store = SQLiteMetadataStore(str(self.db_path))
        self.assertIsNotNone(store)

    def test_metadata_store_default_path(self):
        """Test metadata store with default path."""
        store = SQLiteMetadataStore()
        self.assertIsNotNone(store)


if __name__ == "__main__":
    unittest.main()

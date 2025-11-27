"""Tests for storage and artifact functionality."""

import unittest
import tempfile
import shutil
from pathlib import Path
from uniflow.storage.artifacts import LocalArtifactStore
from uniflow import Dataset


class TestStorage(unittest.TestCase):
    """Test suite for storage functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_artifact_store_creation(self):
        """Test creating an artifact store."""
        store_path = Path(self.test_dir) / "artifacts"
        store = LocalArtifactStore(str(store_path))

        self.assertTrue(store_path.exists())

    def test_artifact_store_default_path(self):
        """Test artifact store with default path."""
        store = LocalArtifactStore()
        self.assertIsNotNone(store)


if __name__ == "__main__":
    unittest.main()

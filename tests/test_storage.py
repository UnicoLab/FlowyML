"""Tests for storage and artifact functionality."""

import unittest
import tempfile
import shutil
from pathlib import Path
from flowyml.storage.artifacts import LocalArtifactStore
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml import Dataset


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


class TestModelMetricsStorage(unittest.TestCase):
    """Test logging production model metrics."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)
        self.store = SQLiteMetadataStore(db_path=str(Path(self.tmpdir) / "metadata.db"))

    def test_log_and_list_model_metrics(self):
        """Ensure metrics can be logged and queried."""
        self.store.log_model_metrics(
            project="demo",
            model_name="classifier",
            metrics={"accuracy": 0.95, "loss": 0.12},
            environment="prod",
            tags={"stage": "prod"},
        )

        rows = self.store.list_model_metrics(project="demo", model_name="classifier")
        self.assertTrue(rows)
        names = {row["metric_name"] for row in rows}
        self.assertIn("accuracy", names)
        self.assertIn("loss", names)


if __name__ == "__main__":
    unittest.main()

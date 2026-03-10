"""Tests for centralized artifact catalog."""

import os
import tempfile
import unittest
from flowyml.storage.catalog.backend import CatalogEntry
from flowyml.storage.catalog.local_backend import LocalCatalogBackend
from flowyml.storage.catalog.manager import ArtifactCatalog
from tests.base import BaseTestCase


class TestCatalogEntry(BaseTestCase):
    """Test CatalogEntry dataclass."""

    def test_to_dict(self):
        """CatalogEntry serializes to dict."""
        entry = CatalogEntry(
            artifact_id="abc-123",
            name="test_model",
            artifact_type="Model",
            source_pipeline="training",
        )
        d = entry.to_dict()
        self.assertEqual(d["artifact_id"], "abc-123")
        self.assertEqual(d["name"], "test_model")
        self.assertEqual(d["artifact_type"], "Model")

    def test_from_dict(self):
        """CatalogEntry deserializes from dict."""
        data = {"artifact_id": "x", "name": "y", "artifact_type": "Dataset"}
        entry = CatalogEntry.from_dict(data)
        self.assertEqual(entry.artifact_id, "x")
        self.assertEqual(entry.name, "y")


class TestLocalCatalogBackend(BaseTestCase):
    """Test LocalCatalogBackend (SQLite)."""

    def setUp(self):
        super().setUp()
        self.db_path = os.path.join(tempfile.mkdtemp(), "test_catalog.db")
        self.backend = LocalCatalogBackend(db_path=self.db_path)

    def test_register_and_get(self):
        """Register and retrieve an artifact."""
        entry = CatalogEntry(
            name="model_v1",
            artifact_type="Model",
            source_pipeline="training",
            tags={"stage": "dev"},
        )
        artifact_id = self.backend.register(entry)
        self.assertTrue(len(artifact_id) > 0)

        retrieved = self.backend.get(artifact_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "model_v1")
        self.assertEqual(retrieved.tags["stage"], "dev")

    def test_list_by_type(self):
        """List artifacts filtered by type."""
        self.backend.register(CatalogEntry(name="m1", artifact_type="Model"))
        self.backend.register(CatalogEntry(name="d1", artifact_type="Dataset"))
        self.backend.register(CatalogEntry(name="m2", artifact_type="Model"))

        models = self.backend.list(artifact_type="Model")
        self.assertEqual(len(models), 2)

    def test_tagging(self):
        """Add tags to an artifact."""
        entry = CatalogEntry(name="test", artifact_type="Model")
        aid = self.backend.register(entry)

        self.backend.tag(aid, {"stage": "production", "team": "ml"})
        updated = self.backend.get(aid)
        self.assertEqual(updated.tags["stage"], "production")
        self.assertEqual(updated.tags["team"], "ml")

    def test_search(self):
        """Search artifacts by name."""
        self.backend.register(CatalogEntry(name="fraud_detector", artifact_type="Model"))
        self.backend.register(CatalogEntry(name="revenue_forecast", artifact_type="Model"))

        results = self.backend.search("fraud")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "fraud_detector")

    def test_lineage(self):
        """Track parent-child lineage."""
        parent_id = self.backend.register(
            CatalogEntry(name="features", artifact_type="Dataset"),
        )
        child_id = self.backend.register(
            CatalogEntry(
                name="model",
                artifact_type="Model",
                parent_ids=[parent_id],
            ),
        )

        lineage = self.backend.get_lineage(child_id)
        self.assertEqual(len(lineage["parents"]), 1)
        self.assertEqual(lineage["parents"][0]["name"], "features")

    def test_find_by_content_hash(self):
        """Find artifact by content hash."""
        entry = CatalogEntry(
            name="hashed",
            artifact_type="Model",
            content_hash="abc123def456",
        )
        self.backend.register(entry)

        found = self.backend.find_by_content_hash("abc123def456")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "hashed")

        not_found = self.backend.find_by_content_hash("nonexistent")
        self.assertIsNone(not_found)


class TestArtifactCatalog(BaseTestCase):
    """Test ArtifactCatalog facade."""

    def setUp(self):
        super().setUp()
        self.db_path = os.path.join(tempfile.mkdtemp(), "test_catalog.db")
        self.backend = LocalCatalogBackend(db_path=self.db_path)
        self.catalog = ArtifactCatalog(backend=self.backend)

    def test_register_convenience(self):
        """Catalog.register() creates entries from kwargs."""
        aid = self.catalog.register(
            name="test_model",
            artifact_type="Model",
            source_step="train",
            source_pipeline="training",
            tags={"v": "1"},
        )
        entry = self.catalog.get(aid)
        self.assertEqual(entry.name, "test_model")
        self.assertEqual(entry.tags["v"], "1")

    def test_content_hash_dedup(self):
        """Catalog computes content hash for deduplication."""
        aid = self.catalog.register(
            name="model",
            artifact_type="Model",
            data={"weights": [1, 2, 3]},
        )
        entry = self.catalog.get(aid)
        self.assertTrue(len(entry.content_hash) > 0)

    def test_tag_kwargs(self):
        """Catalog.tag() accepts keyword arguments."""
        aid = self.catalog.register(name="m", artifact_type="Model")
        self.catalog.tag(aid, stage="production")
        entry = self.catalog.get(aid)
        self.assertEqual(entry.tags["stage"], "production")


if __name__ == "__main__":
    unittest.main()

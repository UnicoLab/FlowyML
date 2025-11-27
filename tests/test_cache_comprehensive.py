"""Comprehensive test suite for cache functionality."""

import unittest
import tempfile
import shutil
from pathlib import Path
import time

from uniflow import Pipeline, step
from uniflow.core.cache import CacheStore
from uniflow.core.context import Context
from tests.base import BaseTestCase


class TestCacheComprehensive(BaseTestCase):
    """Comprehensive test suite for caching."""

    def test_cache_store_directory_creation(self):
        """Test that cache store creates directory."""
        cache_dir = Path(self.test_dir) / "new_cache"
        store = CacheStore(str(cache_dir))

        self.assertTrue(cache_dir.exists())
        self.assertTrue(cache_dir.is_dir())

    def test_cache_key_generation(self):
        """Test cache key generation."""
        cache_dir = Path(self.test_dir) / "cache"
        store = CacheStore(str(cache_dir))

        # Set and get with different keys
        store.set_value("key1", "value1", "step1", "hash1")
        store.set_value("key2", "value2", "step2", "hash2")

        self.assertEqual(store.get("key1"), "value1")
        self.assertEqual(store.get("key2"), "value2")

    def test_cache_overwrite(self):
        """Test cache value overwriting."""
        cache_dir = Path(self.test_dir) / "cache"
        store = CacheStore(str(cache_dir))

        store.set_value("key", "value1", "step", "hash1")
        store.set_value("key", "value2", "step", "hash2")

        self.assertEqual(store.get("key"), "value2")

    def test_cache_with_complex_data(self):
        """Test caching complex data structures."""
        cache_dir = Path(self.test_dir) / "cache"
        store = CacheStore(str(cache_dir))

        complex_data = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple": (1, 2, 3),
            "number": 42,
        }

        store.set_value("complex", complex_data, "step", "hash")
        retrieved = store.get("complex")

        self.assertEqual(retrieved["list"], [1, 2, 3])
        self.assertEqual(retrieved["dict"]["nested"], "value")

    def test_cache_hit_count(self):
        """Test cache hit counting."""
        cache_dir = Path(self.test_dir) / "cache"
        store = CacheStore(str(cache_dir))

        store.set_value("key", "value", "step", "hash")

        initial_hits = store.hits
        store.get("key")
        store.get("key")

        self.assertEqual(store.hits, initial_hits + 2)

    def test_cache_miss_count(self):
        """Test cache miss counting."""
        cache_dir = Path(self.test_dir) / "cache"
        store = CacheStore(str(cache_dir))

        initial_misses = store.misses
        store.get("nonexistent1")
        store.get("nonexistent2")

        self.assertEqual(store.misses, initial_misses + 2)

    def test_pipeline_cache_reuse(self):
        """Test pipeline reuses cache across runs."""
        execution_count = {"count": 0}

        @step
        def expensive_computation():
            execution_count["count"] += 1
            time.sleep(0.01)  # Simulate expensive operation
            return {"result": 42}

        p = Pipeline("cache_reuse", enable_cache=True)
        p.add_step(expensive_computation)

        # First run
        start1 = time.time()
        result1 = p.run()
        duration1 = time.time() - start1

        # Second run (should be cached)
        start2 = time.time()
        result2 = p.run()
        duration2 = time.time() - start2

        # Verify execution count
        self.assertEqual(execution_count["count"], 1)

        # Verify results are same
        self.assertEqual(result1["expensive_computation"], result2["expensive_computation"])

        # Second run should be faster (cached)
        self.assertLess(duration2, duration1)


if __name__ == "__main__":
    unittest.main()

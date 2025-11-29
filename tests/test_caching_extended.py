"""Extended test suite for caching functionality."""

import unittest
from flowyml import Pipeline, step
from flowyml.core.cache import CacheStore
from pathlib import Path
from tests.base import BaseTestCase


class TestCachingExtended(BaseTestCase):
    """Extended test suite for caching functionality."""

    def test_cache_store_initialization(self):
        """Test cache store initialization."""
        cache_dir = Path(self.test_dir) / "cache"
        store = CacheStore(str(cache_dir))

        self.assertTrue(cache_dir.exists())

    def test_cache_with_step_decorator(self):
        """Test caching with step decorator configuration."""
        call_count = {"count": 0}

        @step(cache="code_hash")
        def cached_step():
            call_count["count"] += 1
            return 42

        p = Pipeline("cache_decorator_test", enable_cache=True)
        p.add_step(cached_step)

        result1 = p.run()
        result2 = p.run()

        # Should only execute once due to caching
        self.assertEqual(call_count["count"], 1)
        self.assertEqual(result1["cached_step"], 42)
        self.assertEqual(result2["cached_step"], 42)

    def test_cache_disabled_per_step(self):
        """Test disabling cache for specific step."""
        call_count = {"count": 0}

        @step(cache=False)
        def uncached_step():
            call_count["count"] += 1
            return call_count["count"]

        p = Pipeline("step_no_cache", enable_cache=True)
        p.add_step(uncached_step)

        result1 = p.run()
        result2 = p.run()

        # Should execute twice
        self.assertEqual(result1["uncached_step"], 1)
        self.assertEqual(result2["uncached_step"], 2)

    def test_cache_store_get_miss(self):
        """Test cache store get with cache miss."""
        cache_dir = Path(self.test_dir) / "cache"
        store = CacheStore(str(cache_dir))

        result = store.get("nonexistent_key")
        self.assertIsNone(result)

    def test_cache_store_set_and_get(self):
        """Test cache store set and get operations."""
        cache_dir = Path(self.test_dir) / "cache"
        store = CacheStore(str(cache_dir))

        test_data = {"result": [1, 2, 3], "metadata": "test"}
        store.set_value("test_key", test_data, "test_step", "hash123")

        retrieved = store.get("test_key")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["result"], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()

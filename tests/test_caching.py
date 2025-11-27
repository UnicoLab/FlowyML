"""Test suite for caching functionality."""

import unittest
import tempfile
import shutil
from pathlib import Path

from uniflow import Pipeline, step
from uniflow.core.cache import CacheStore
from uniflow.core.context import Context
from tests.base import BaseTestCase


class TestCaching(BaseTestCase):
    """Test suite for caching."""

    def test_cache_hit(self):
        """Test cache hit on second run."""
        call_count = {"count": 0}

        @step
        def expensive_step():
            call_count["count"] += 1
            return 42

        p = Pipeline("cache_test", enable_cache=True)
        p.add_step(expensive_step)

        # First run
        result1 = p.run()
        self.assertEqual(call_count["count"], 1)
        self.assertEqual(result1["expensive_step"], 42)

        # Second run - should use cache
        result2 = p.run()
        self.assertEqual(call_count["count"], 1)  # Not incremented
        self.assertEqual(result2["expensive_step"], 42)

    def test_cache_disabled(self):
        """Test that caching can be disabled."""
        call_count = {"count": 0}

        @step
        def counting_step():
            call_count["count"] += 1
            return call_count["count"]

        p = Pipeline("no_cache_test", enable_cache=False)
        p.add_step(counting_step)

        # First run
        result1 = p.run()
        self.assertEqual(result1["counting_step"], 1)

        # Second run - should NOT use cache
        result2 = p.run()
        self.assertEqual(result2["counting_step"], 2)

    def test_cache_store_operations(self):
        """Test cache store get/set operations."""
        cache_dir = Path(self.test_dir) / "cache"
        cache_store = CacheStore(str(cache_dir))

        # Test set and get
        cache_store.set_value("test_key", {"result": 42}, "test_step", "code123")
        cached = cache_store.get("test_key")

        self.assertIsNotNone(cached)
        self.assertEqual(cached["result"], 42)

    def test_cache_miss(self):
        """Test cache miss for non-existent key."""
        cache_dir = Path(self.test_dir) / "cache"
        cache_store = CacheStore(str(cache_dir))

        cached = cache_store.get("nonexistent_key")
        self.assertIsNone(cached)


if __name__ == "__main__":
    unittest.main()

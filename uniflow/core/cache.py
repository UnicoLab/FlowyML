"""Cache Module - Intelligent caching strategies for pipeline steps."""

import json
import pickle
import hashlib
from pathlib import Path
from typing import Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    """A cache entry with metadata."""

    key: str
    value: Any
    created_at: datetime
    step_name: str
    code_hash: str
    input_hash: str | None = None
    size_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


class CacheStrategy:
    """Base class for caching strategies."""

    def get_key(self, step_name: str, inputs: dict[str, Any], code_hash: str) -> str:
        """Generate cache key."""
        raise NotImplementedError

    def should_cache(self, step_name: str) -> bool:
        """Determine if step should be cached."""
        return True


class CodeHashCache(CacheStrategy):
    """Cache based on function code hash."""

    def get_key(self, step_name: str, inputs: dict[str, Any], code_hash: str) -> str:
        return f"{step_name}:{code_hash}"


class InputHashCache(CacheStrategy):
    """Cache based on input hash."""

    def get_key(self, step_name: str, inputs: dict[str, Any], code_hash: str) -> str:
        input_str = json.dumps(inputs, sort_keys=True, default=str)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        return f"{step_name}:{code_hash}:{input_hash}"


class CacheStore:
    """Local cache storage for pipeline steps."""

    def __init__(self, cache_dir: str = ".uniflow/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._load_metadata()

        # Statistics
        self.hits = 0
        self.misses = 0

    def _load_metadata(self) -> dict[str, dict[str, Any]]:
        """Load cache metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                return json.load(f)
        return {}

    def _save_metadata(self) -> None:
        """Save cache metadata."""
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def _get_cache_path(self, key: str) -> Path:
        """Get path for cache file."""
        # Use hash to avoid filesystem issues with long keys
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.pkl"

    def get(self, key: str) -> Any | None:
        """Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self.misses += 1
            return None

        try:
            with open(cache_path, "rb") as f:
                value = pickle.load(f)
            self.hits += 1
            return value
        except Exception:
            self.misses += 1
            return None

    def set_value(self, key: str, value: Any, step_name: str, code_hash: str, input_hash: str | None = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            step_name: Name of the step
            code_hash: Hash of step code
            input_hash: Hash of inputs (optional)
        """
        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(value, f)

            # Update metadata
            size_bytes = cache_path.stat().st_size
            self.metadata[key] = {
                "step_name": step_name,
                "code_hash": code_hash,
                "input_hash": input_hash,
                "created_at": datetime.now().isoformat(),
                "size_bytes": size_bytes,
                "file": str(cache_path.name),
            }
            self._save_metadata()

        except Exception:
            pass

    def invalidate(self, key: str | None = None, step_name: str | None = None) -> None:
        """Invalidate cache entries.

        Args:
            key: Specific cache key to invalidate
            step_name: Invalidate all entries for a step
        """
        if key:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
            if key in self.metadata:
                del self.metadata[key]

        elif step_name:
            keys_to_remove = [k for k, v in self.metadata.items() if v["step_name"] == step_name]
            for k in keys_to_remove:
                cache_path = self._get_cache_path(k)
                if cache_path.exists():
                    cache_path.unlink()
                del self.metadata[k]

        self._save_metadata()

    def clear(self) -> None:
        """Clear all cache entries."""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
        self.metadata = {}
        self._save_metadata()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_size = sum(v["size_bytes"] for v in self.metadata.values())
        total_entries = len(self.metadata)

        by_step = {}
        for entry in self.metadata.values():
            step = entry["step_name"]
            if step not in by_step:
                by_step[step] = {"count": 0, "size_bytes": 0}
            by_step[step]["count"] += 1
            by_step[step]["size_bytes"] += entry["size_bytes"]

        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        return {
            "total_entries": total_entries,
            "total_size_mb": total_size / (1024 * 1024),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "by_step": by_step,
        }

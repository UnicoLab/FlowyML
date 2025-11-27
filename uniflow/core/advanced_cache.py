"""Advanced caching strategies."""

import hashlib
import pickle
from pathlib import Path
from typing import Any
from collections.abc import Callable
from datetime import datetime, timedelta


class ContentBasedCache:
    """Content-based caching using input hashing.

    Caches based on actual input content, not just step name.
    """

    def __init__(self, cache_dir: str = ".uniflow/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_hash(self, *args, **kwargs) -> str:
        """Compute hash of inputs."""
        # Serialize inputs
        try:
            content = pickle.dumps((args, kwargs))
            return hashlib.sha256(content).hexdigest()
        except Exception:
            # Fallback to str representation
            content = str((args, kwargs)).encode()
            return hashlib.sha256(content).hexdigest()

    def get(self, step_name: str, *args, **kwargs) -> Any | None:
        """Get cached result if exists."""
        content_hash = self._compute_hash(*args, **kwargs)
        cache_key = f"{step_name}_{content_hash}"
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        if cache_file.exists():
            with open(cache_file, "rb") as f:
                cached_data = pickle.load(f)

            # Check if still valid
            if "result" in cached_data:
                return cached_data["result"]

        return None

    def set_value(self, step_name: str, result: Any, *args, **kwargs) -> None:
        """Cache a result."""
        content_hash = self._compute_hash(*args, **kwargs)
        cache_key = f"{step_name}_{content_hash}"
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        cached_data = {
            "result": result,
            "cached_at": datetime.now().isoformat(),
            "inputs_hash": content_hash,
        }

        with open(cache_file, "wb") as f:
            pickle.dump(cached_data, f)

    def invalidate(self, step_name: str | None = None) -> None:
        """Invalidate cache entries."""
        pattern = f"{step_name}_*.pkl" if step_name else "*.pkl"

        for cache_file in self.cache_dir.glob(pattern):
            cache_file.unlink()


class SharedCache:
    """Shared cache across different pipeline runs.

    Allows cache reuse across multiple executions.
    """

    def __init__(self, cache_dir: str = ".uniflow/shared_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        """Load cache index."""
        import json

        if self.index_file.exists():
            with open(self.index_file) as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def _save_index(self) -> None:
        """Save cache index."""
        import json

        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=2)

    def get(self, cache_key: str) -> Any | None:
        """Get from shared cache."""
        if cache_key in self.index:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            if cache_file.exists():
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
        return None

    def set_value(self, cache_key: str, value: Any, metadata: dict | None = None) -> None:
        """Set shared cache entry."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        with open(cache_file, "wb") as f:
            pickle.dump(value, f)

        self.index[cache_key] = {
            "cached_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._save_index()

    def list_keys(self) -> list:
        """List all cache keys."""
        return list(self.index.keys())


class SmartCache:
    """Smart cache with TTL and automatic invalidation.

    Features:
    - Time-to-live (TTL)
    - Size limits
    - LRU eviction
    """

    def __init__(
        self,
        cache_dir: str = ".uniflow/smart_cache",
        ttl_seconds: int = 3600,
        max_size_mb: int = 1000,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.max_size_mb = max_size_mb

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        cache_file = self.cache_dir / f"{key}.pkl"
        metadata_file = self.cache_dir / f"{key}.meta"

        if not cache_file.exists() or not metadata_file.exists():
            return None

        # Check TTL
        import json

        with open(metadata_file) as f:
            metadata = json.load(f)

        cached_at = datetime.fromisoformat(metadata["cached_at"])
        if datetime.now() - cached_at > timedelta(seconds=self.ttl_seconds):
            # Expired
            cache_file.unlink()
            metadata_file.unlink()
            return None

        # Update access time
        metadata["last_accessed"] = datetime.now().isoformat()
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        with open(cache_file, "rb") as f:
            return pickle.load(f)

    def set_value(self, key: str, value: Any) -> None:
        """Set cached value."""
        import json

        # Check size limits
        self._evict_if_needed()

        cache_file = self.cache_dir / f"{key}.pkl"
        metadata_file = self.cache_dir / f"{key}.meta"

        with open(cache_file, "wb") as f:
            pickle.dump(value, f)

        metadata = {
            "cached_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "size_bytes": cache_file.stat().st_size,
        }

        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

    def _evict_if_needed(self) -> None:
        """Evict old entries if cache is too large."""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.pkl"))
        max_size_bytes = self.max_size_mb * 1024 * 1024

        if total_size > max_size_bytes:
            # LRU eviction
            import json

            entries = []
            for meta_file in self.cache_dir.glob("*.meta"):
                with open(meta_file) as f:
                    metadata = json.load(f)
                    entries.append(
                        (
                            meta_file.stem,
                            datetime.fromisoformat(metadata["last_accessed"]),
                        ),
                    )

            # Sort by access time
            entries.sort(key=lambda x: x[1])

            # Remove oldest entries until under limit
            for key, _ in entries:
                cache_file = self.cache_dir / f"{key}.pkl"
                meta_file = self.cache_dir / f"{key}.meta"

                if cache_file.exists():
                    cache_file.unlink()
                if meta_file.exists():
                    meta_file.unlink()

                # Recalculate size
                total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.pkl"))
                if total_size <= max_size_bytes:
                    break


def memoize(ttl_seconds: int | None = None):
    """Memoization decorator for functions.

    Args:
        ttl_seconds: Time-to-live for cached results

    Example:
        >>> @memoize(ttl_seconds=3600)
        ... def expensive_function(x):
        ...     return x**2
    """
    cache = {}
    cache_time = {}

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Create cache key
            key = (args, tuple(sorted(kwargs.items())))

            # Check if cached and valid
            if key in cache:
                if ttl_seconds is None:
                    return cache[key]

                elapsed = (datetime.now() - cache_time[key]).total_seconds()
                if elapsed < ttl_seconds:
                    return cache[key]

            # Compute and cache
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = datetime.now()

            return result

        return wrapper

    return decorator

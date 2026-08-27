"""File-based cache for resolved enterprise stack definitions.

This module provides a simple file-system cache that stores
:class:`~flowyml.stacks.enterprise.models.StackDefinition` instances as YAML
files under ``~/.flowyml/cache/stacks/``.  Cache keys are derived from the
source URI and content hash so that identical definitions always map to the
same cache entry.

Typical usage::

    cache = StackCache()
    cached = cache.get("github://org/repo@v1.0.0#my_stack")
    if cached is None:
        stack = source.load_stack("my_stack")
        cache.set("github://org/repo@v1.0.0#my_stack", stack)
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

import yaml

from flowyml.stacks.enterprise.models import StackDefinition

__all__ = [
    "StackCache",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default cache root
# ---------------------------------------------------------------------------

_DEFAULT_CACHE_ROOT = Path.home() / ".flowyml" / "cache" / "stacks"


class StackCache:
    """File-based cache for :class:`StackDefinition` objects.

    Each cached entry is stored as a YAML file whose name is derived from
    the SHA-256 hash of the supplied cache key.  This ensures deterministic
    lookup while avoiding file-system-unfriendly characters that may appear
    in source URIs.

    Args:
        root: Root directory for cache storage.  Defaults to
            ``~/.flowyml/cache/stacks/``.

    Example::

        cache = StackCache()
        cache.set("file:///stacks/prod.yaml", stack_def)
        hit = cache.get("file:///stacks/prod.yaml")
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _DEFAULT_CACHE_ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        logger.debug("StackCache initialised at %s", self._root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> StackDefinition | None:
        """Retrieve a cached stack definition.

        Args:
            key: Cache key (typically a source URI or URI + fragment).

        Returns:
            The cached :class:`StackDefinition` if present, otherwise
            ``None``.
        """
        path = self._key_path(key)
        if not path.exists():
            logger.debug("Cache MISS for key=%s", key)
            return None

        try:
            with open(path) as fh:
                data: dict[str, Any] = yaml.safe_load(fh)
            stack = StackDefinition.model_validate(data)
            logger.debug("Cache HIT for key=%s", key)
            return stack
        except Exception:
            logger.warning(
                "Corrupt cache entry for key=%s – removing",
                key,
                exc_info=True,
            )
            path.unlink(missing_ok=True)
            return None

    # A003 flags `set` as shadowing the builtin. It does not: the name is only
    # ever reached as `cache.set(...)`, and `get`/`set` is the conventional
    # cache interface this class implements. Later ruff releases removed the
    # rule for exactly this reason.
    def set(self, key: str, stack: StackDefinition) -> None:  # noqa: A003
        """Store a stack definition in the cache.

        Args:
            key: Cache key.
            stack: The :class:`StackDefinition` to cache.
        """
        path = self._key_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = stack.model_dump(mode="json", by_alias=True, exclude_none=True)
        try:
            with open(path, "w") as fh:
                yaml.safe_dump(data, fh, sort_keys=False, default_flow_style=False)
            logger.debug("Cache SET for key=%s → %s", key, path)
        except OSError as exc:
            logger.warning("Failed to write cache entry: %s", exc)

    def invalidate(self, key: str) -> None:
        """Remove a single cache entry.

        Args:
            key: Cache key to invalidate.
        """
        path = self._key_path(key)
        if path.exists():
            path.unlink()
            logger.debug("Cache INVALIDATE key=%s", key)

    def clear(self) -> None:
        """Remove **all** cached entries."""
        if self._root.exists():
            shutil.rmtree(self._root)
            self._root.mkdir(parents=True, exist_ok=True)
            logger.info("Cache cleared: %s", self._root)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_key(key: str) -> str:
        """Derive a filesystem-safe hash from *key*.

        Args:
            key: Arbitrary string (typically a URI).

        Returns:
            64-character hex SHA-256 digest.
        """
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _key_path(self, key: str) -> Path:
        """Return the filesystem path for a given cache key.

        The path uses the first two characters of the hash as a fan-out
        directory to avoid placing too many files in a single directory.
        """
        digest = self._hash_key(key)
        return self._root / digest[:2] / f"{digest}.yaml"

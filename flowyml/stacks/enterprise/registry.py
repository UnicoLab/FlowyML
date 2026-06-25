"""Enterprise Stack Registry — central hub for stack resolution.

The ``EnterpriseStackRegistry`` aggregates one or more ``StackSource``
instances and provides a unified API to discover, resolve, and import
stack definitions.  It optionally integrates with the ``StackLockManager``
for deterministic, reproducible resolution.

Example::

    registry = EnterpriseStackRegistry.from_source("github://my-org/stacks@v1")
    stack = registry.resolve("aml_cpu_small", version="1.2.0")
"""

from __future__ import annotations

import logging

from flowyml.stacks.enterprise.exceptions import (
    StackNotFoundError,
    StackSourceError,
)
from flowyml.stacks.enterprise.lock import StackLockManager
from flowyml.stacks.enterprise.models import StackDefinition, StackReference
from flowyml.stacks.enterprise.sources.base import StackSource, parse_source_uri

logger = logging.getLogger(__name__)

__all__ = [
    "EnterpriseStackRegistry",
]


class EnterpriseStackRegistry:
    """Central registry that aggregates stack sources and resolves stacks.

    The registry holds a list of ``StackSource`` backends (filesystem, Git,
    OCI, …) and exposes a single ``resolve()`` entry-point that searches
    each source in order.  When a ``StackLockManager`` is attached, the
    lock file is consulted first to honour pinned digests.

    Args:
        sources: Optional list of pre-built ``StackSource`` instances.
    """

    def __init__(self, sources: list[StackSource] | None = None) -> None:
        self._sources: list[StackSource] = list(sources) if sources else []
        self._lock_manager: StackLockManager | None = None
        logger.debug(
            "EnterpriseStackRegistry initialised with %d source(s).",
            len(self._sources),
        )

    # ------------------------------------------------------------------
    # Class-method constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_source(cls, uri: str) -> EnterpriseStackRegistry:
        """Create a registry backed by a single source URI.

        Args:
            uri: Source URI string (e.g. ``github://org/repo@v1``).

        Returns:
            A new ``EnterpriseStackRegistry`` instance.

        Raises:
            StackSourceError: If the URI cannot be parsed.
        """
        source = parse_source_uri(uri)
        return cls(sources=[source])

    @classmethod
    def from_sources(cls, uris: list[str]) -> EnterpriseStackRegistry:
        """Create a registry backed by multiple source URIs.

        Sources are searched in the order provided.

        Args:
            uris: List of source URI strings.

        Returns:
            A new ``EnterpriseStackRegistry`` instance.

        Raises:
            StackSourceError: If any URI cannot be parsed.
        """
        sources = [parse_source_uri(uri) for uri in uris]
        return cls(sources=sources)

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(
        self,
        name: str,
        version: str | None = None,
    ) -> StackDefinition:
        """Resolve a stack definition by name and optional version.

        Resolution order:
        1. If a ``StackLockManager`` is attached and the stack is locked,
           the locked source and digest are used for verification.
        2. Each registered source is queried in order.
        3. The first matching definition is returned.

        Args:
            name: Stack name to resolve.
            version: Optional semantic version constraint.

        Returns:
            The resolved ``StackDefinition``.

        Raises:
            StackNotFoundError: If no source contains the requested stack.
        """
        logger.info("Resolving stack '%s' (version=%s)…", name, version)

        # 1. Check lock file first
        if self._lock_manager is not None and self._lock_manager.is_locked(name):
            locked_digest = self._lock_manager.get_locked_digest(name)
            logger.debug(
                "Found locked entry for '%s' → digest=%s",
                name,
                locked_digest,
            )
            # Try to fetch from sources and verify against lock
            stack = self._fetch_from_sources(name, version)
            if stack is not None:
                # Verify digest matches the lock
                result = self._lock_manager.verify_stack(name, stack)
                if result.status == "modified":
                    logger.warning(
                        "Stack '%s' digest mismatch: expected %s, got %s",
                        name,
                        result.expected_digest,
                        result.actual_digest,
                    )
                return stack

        # 2. Search all sources
        stack = self._fetch_from_sources(name, version)
        if stack is not None:
            return stack

        # 3. Not found — build a helpful error
        available = [ref.name for ref in self.list_stacks()]
        raise StackNotFoundError(
            stack_name=name,
            available=available if available else None,
        )

    # ------------------------------------------------------------------
    # Listing & importing
    # ------------------------------------------------------------------

    def list_stacks(self) -> list[StackReference]:
        """List all available stacks across all registered sources.

        Returns:
            Aggregated list of ``StackReference`` objects.
        """
        refs: list[StackReference] = []
        for source in self._sources:
            try:
                refs.extend(source.list_stacks())
            except Exception as exc:
                logger.warning(
                    "Failed to list stacks from source '%s': %s",
                    source.uri,
                    exc,
                )
        return refs

    def import_stack(self, source_uri: str) -> list[StackDefinition]:
        """Import stack definitions from a remote source URI.

        The source is resolved, all its stacks are fetched, and the source
        is added to the registry for future resolution.

        Args:
            source_uri: URI of the source to import from.

        Returns:
            List of imported ``StackDefinition`` objects.

        Raises:
            StackSourceError: If the source cannot be accessed.
        """
        logger.info("Importing stacks from '%s'…", source_uri)
        source = parse_source_uri(source_uri)

        try:
            stacks = source.fetch_all()
        except Exception as exc:
            raise StackSourceError(
                source_uri=source_uri,
                reason=f"Failed to fetch stacks: {exc}",
            ) from exc

        # Add the source so subsequent resolve() calls find them
        if source not in self._sources:
            self._sources.append(source)

        logger.info(
            "Imported %d stack(s) from '%s'.",
            len(stacks),
            source_uri,
        )
        return stacks

    # ------------------------------------------------------------------
    # Source management
    # ------------------------------------------------------------------

    def add_source(self, source: StackSource) -> None:
        """Add a stack source to the registry.

        Sources are searched in the order they are added.

        Args:
            source: ``StackSource`` instance to register.
        """
        self._sources.append(source)
        logger.debug("Added source '%s'.", source.uri)

    def set_lock_manager(self, lock_manager: StackLockManager) -> None:
        """Attach a ``StackLockManager`` for digest-pinned resolution.

        Args:
            lock_manager: The lock manager to use.
        """
        self._lock_manager = lock_manager
        logger.debug("Lock manager attached (path=%s).", lock_manager.lock_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_from_sources(
        self,
        name: str,
        version: str | None = None,
    ) -> StackDefinition | None:
        """Try to fetch a stack from each registered source in order.

        Args:
            name: Stack name.
            version: Optional version.

        Returns:
            ``StackDefinition`` if found, otherwise ``None``.
        """
        for source in self._sources:
            try:
                stack = source.fetch(name, version)
                logger.debug(
                    "Resolved '%s' from source '%s'.",
                    name,
                    source.uri,
                )
                return stack
            except StackNotFoundError:
                continue
            except Exception as exc:
                logger.warning(
                    "Error fetching '%s' from source '%s': %s",
                    name,
                    source.uri,
                    exc,
                )
                continue
        return None

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    @property
    def sources(self) -> list[StackSource]:
        """Currently registered sources (read-only copy)."""
        return list(self._sources)

    def __repr__(self) -> str:
        return f"EnterpriseStackRegistry(sources={len(self._sources)}, lock={'yes' if self._lock_manager else 'no'})"

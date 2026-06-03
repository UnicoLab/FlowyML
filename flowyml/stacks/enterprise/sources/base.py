"""Base stack source abstraction for the Enterprise Stack Registry.

Defines the ``StackSource`` protocol and a ``parse_source_uri`` helper that
converts a URI string (e.g. ``github://org/repo@v1``, ``file:///path``) into
a concrete source instance.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from flowyml.stacks.enterprise.models import StackDefinition, StackReference

logger = logging.getLogger(__name__)

__all__ = [
    "StackSource",
    "parse_source_uri",
]


@runtime_checkable
class StackSource(Protocol):
    """Protocol defining how a stack source provides stack definitions.

    Implementations fetch stack YAML from various backends (local filesystem,
    Git repositories, OCI registries, HTTP endpoints, etc.).
    """

    @property
    def uri(self) -> str:
        """Canonical URI for this source (e.g. ``github://org/repo@v1``)."""
        ...

    def list_stacks(self) -> list[StackReference]:
        """Return lightweight references for every stack in this source.

        Returns:
            List of ``StackReference`` objects.
        """
        ...

    def fetch(self, name: str, version: str | None = None) -> StackDefinition:
        """Fetch a full stack definition by name (and optional version).

        Args:
            name: Stack name.
            version: Optional semantic version constraint.

        Returns:
            The resolved ``StackDefinition``.

        Raises:
            StackNotFoundError: If the requested stack is not found.
        """
        ...

    def fetch_all(self) -> list[StackDefinition]:
        """Fetch all stack definitions from this source.

        Returns:
            List of all ``StackDefinition`` objects.
        """
        ...


def parse_source_uri(uri: str) -> StackSource:
    """Parse a source URI string and return a matching ``StackSource``.

    Supported schemes:

    * ``file://`` — local filesystem path
    * ``github://`` — GitHub repository (``github://org/repo@ref``)

    Additional schemes can be registered via entry-points in the future.

    Args:
        uri: Source URI string.

    Returns:
        A ``StackSource`` implementation for the given URI.

    Raises:
        StackSourceError: If the scheme is unknown or the URI is malformed.
    """
    from flowyml.stacks.enterprise.exceptions import StackSourceError

    if not uri or "://" not in uri:
        raise StackSourceError(
            source_uri=uri,
            reason=f"Invalid source URI format: '{uri}'. Expected scheme://...",
            suggestion="Use a valid URI like 'file:///path/to/stacks' or 'github://org/repo@v1'.",
        )

    scheme = uri.split("://", 1)[0].lower()

    if scheme == "file":
        from flowyml.stacks.enterprise.sources.local import LocalStackSource

        path = uri.split("://", 1)[1]
        return LocalStackSource(paths=[path])

    if scheme in ("github", "gitlab", "git", "git+https"):
        from flowyml.stacks.enterprise.sources.git import GitStackSource

        return GitStackSource(uri=uri)

    if scheme in ("http", "https"):
        from flowyml.stacks.enterprise.sources.http import HTTPStackSource

        return HTTPStackSource(url=uri)

    raise StackSourceError(
        source_uri=uri,
        reason=f"Unknown source scheme: '{scheme}'.",
        suggestion=(
            "Supported schemes: file://, github://, gitlab://, git://, "
            "git+https://, http://, https://. "
            "Check the URI or register a custom source provider."
        ),
    )

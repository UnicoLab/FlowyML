"""HTTP(S)-backed stack source.

This module implements :class:`HTTPStackSource`, which fetches a single
enterprise stack definition YAML file from an HTTP or HTTPS URL.

The implementation uses `httpx <https://www.python-httpx.org/>`_ (already a
project dependency) for robust HTTP handling with timeouts and streaming
support.

Example::

    source = HTTPStackSource(url="https://stacks.example.com/prod.yaml")
    refs = source.list_stacks()  # → single-element list
    stack = source.load_stack("aml_cpu_small")
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import yaml

from flowyml.stacks.enterprise.exceptions import StackNotFoundError, StackSourceError
from flowyml.stacks.enterprise.models import StackDefinition, StackReference

__all__ = [
    "HTTPStackSource",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 30.0  # seconds
_MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MiB safety limit

_YAML_CONTENT_TYPES = frozenset(
    {
        "application/x-yaml",
        "application/yaml",
        "text/yaml",
        "text/x-yaml",
        "text/plain",
        "application/octet-stream",
    },
)


class HTTPStackSource:
    """Stack source that fetches YAML definitions over HTTP(S).

    For a single-file URL the source exposes exactly one stack.  The
    remote content is re-fetched on every call – use
    :class:`~flowyml.stacks.enterprise.cache.StackCache` for caching.

    Args:
        url: Full HTTPS (or HTTP) URL to a stack YAML file.
        timeout: Request timeout in seconds.

    Example::

        source = HTTPStackSource(url="https://cdn.example.com/stacks/prod.yaml")
        stack = source.load_stack("prod_gpu")
    """

    def __init__(
        self,
        url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._url = url
        self._timeout = timeout
        self._cached_definition: StackDefinition | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_yaml(self) -> dict[str, Any]:
        """Fetch and parse a YAML document from ``self._url``.

        Returns:
            Parsed YAML mapping.

        Raises:
            StackSourceError: On network errors, unexpected content types,
                or invalid YAML content.
        """
        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                response = client.get(self._url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise StackSourceError(
                source_uri=self._url,
                reason=f"HTTP request timed out after {self._timeout}s.",
                suggestion="Increase the timeout or check the URL availability.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise StackSourceError(
                source_uri=self._url,
                reason=(f"HTTP {exc.response.status_code}: {exc.response.reason_phrase}"),
                suggestion="Check the URL is correct and the server is accessible.",
            ) from exc
        except httpx.HTTPError as exc:
            raise StackSourceError(
                source_uri=self._url,
                reason=f"HTTP request failed: {exc}",
                suggestion="Check your network connection and the URL.",
            ) from exc

        # --- Validate content type -----------------------------------------
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        if content_type and content_type not in _YAML_CONTENT_TYPES:
            logger.warning(
                "Unexpected content-type '%s' from %s – attempting YAML parse anyway",
                content_type,
                self._url,
            )

        # --- Safety: limit content size ------------------------------------
        if len(response.content) > _MAX_CONTENT_LENGTH:
            raise StackSourceError(
                source_uri=self._url,
                reason=(
                    f"Response body is {len(response.content)} bytes, "
                    f"exceeding the {_MAX_CONTENT_LENGTH} byte safety limit."
                ),
                suggestion="The URL may not point to a stack YAML file.",
            )

        # --- Parse YAML ----------------------------------------------------
        try:
            data = yaml.safe_load(response.text)
        except yaml.YAMLError as exc:
            raise StackSourceError(
                source_uri=self._url,
                reason=f"Failed to parse YAML: {exc}",
                suggestion="Verify the URL points to a valid YAML stack definition.",
            ) from exc

        if not isinstance(data, dict):
            raise StackSourceError(
                source_uri=self._url,
                reason="YAML content must be a mapping, not a scalar or list.",
                suggestion="Ensure the remote file is a valid stack definition YAML.",
            )

        return data

    def _ensure_loaded(self) -> StackDefinition:
        """Fetch and validate the remote stack definition (cached per instance).

        Returns:
            Validated :class:`StackDefinition`.

        Raises:
            StackSourceError: On any fetch or validation error.
        """
        if self._cached_definition is not None:
            return self._cached_definition

        data = self._fetch_yaml()

        try:
            stack = StackDefinition.model_validate(data)
        except Exception as exc:
            name = data.get("metadata", {}).get("name", self._url)
            raise StackSourceError(
                source_uri=self._url,
                reason=f"Validation failed for stack '{name}': {exc}",
                suggestion="Check the remote YAML against the stack schema.",
            ) from exc

        self._cached_definition = stack
        logger.info(
            "Fetched stack %s@%s from %s",
            stack.name,
            stack.version,
            self._url,
        )
        return stack

    # ------------------------------------------------------------------
    # StackSource protocol
    # ------------------------------------------------------------------

    @property
    def uri(self) -> str:
        """Canonical URI for this source."""
        return self._url

    def fetch(self, name: str, version: str | None = None) -> StackDefinition:
        """Fetch a stack definition by name (StackSource protocol)."""
        return self.load_stack(name, version)

    def fetch_all(self) -> list[StackDefinition]:
        """Fetch all stack definitions from this URL."""
        return [self._ensure_loaded()]

    def list_stacks(self) -> list[StackReference]:
        """Return a single-element list for the remote stack.

        Returns:
            A list containing one :class:`StackReference`.

        Raises:
            StackSourceError: If the remote YAML cannot be fetched or parsed.
        """
        stack = self._ensure_loaded()
        return [
            StackReference(
                name=stack.name,
                version=stack.version,
                source=self._url,
                path=self._url,
            ),
        ]

    def load_stack(
        self,
        name: str,
        version: str | None = None,
    ) -> StackDefinition:
        """Load the stack definition from the remote URL.

        Args:
            name: Expected stack name.  Must match the definition's
                ``metadata.name``.
            version: Optional version filter.

        Returns:
            A validated :class:`StackDefinition`.

        Raises:
            StackNotFoundError: If *name* (or *version*) does not match
                the fetched definition.
            StackSourceError: If the remote YAML cannot be fetched.
        """
        stack = self._ensure_loaded()

        if stack.name != name:
            raise StackNotFoundError(
                stack_name=name,
                source=self._url,
                available=[stack.name],
            )

        if version is not None and stack.version != version:
            raise StackNotFoundError(
                stack_name=f"{name}@{version}",
                source=self._url,
                available=[f"{stack.name}@{stack.version}"],
            )

        return stack

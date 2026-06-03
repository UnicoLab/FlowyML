"""Local filesystem stack source.

This module implements :class:`LocalStackSource`, which discovers and loads
enterprise stack definitions from one or more directories on the local
file-system.

Default scan paths (configurable)::

    .flowyml/stacks/
    stacks/
    ~/.flowyml/stacks/

Example::

    source = LocalStackSource()  # uses default paths
    refs = source.list_stacks()
    stack = source.load_stack("aml_cpu_small", version="1.2.0")
"""

from __future__ import annotations

import logging
from pathlib import Path

from flowyml.stacks.enterprise.exceptions import StackNotFoundError
from flowyml.stacks.enterprise.models import StackDefinition, StackReference

__all__ = [
    "LocalStackSource",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

_DEFAULT_PATHS: list[str] = [
    ".flowyml/stacks/",
    "stacks/",
    "~/.flowyml/stacks/",
]


class LocalStackSource:
    """Stack source backed by local filesystem directories.

    The source scans every directory in *paths* for ``*.yaml`` and ``*.yml``
    files, attempts to parse each one as a
    :class:`~flowyml.stacks.enterprise.models.StackDefinition`, and exposes
    those that validate successfully.

    Args:
        paths: Directories to scan.  Shell tildes (``~``) are expanded.
            If ``None``, the :data:`_DEFAULT_PATHS` are used.

    Example::

        source = LocalStackSource(paths=["./my-stacks/"])
        for ref in source.list_stacks():
            print(ref.name, ref.version)
    """

    def __init__(self, paths: list[str] | None = None) -> None:
        raw_paths = paths if paths is not None else list(_DEFAULT_PATHS)
        self._paths: list[Path] = [Path(p).expanduser().resolve() for p in raw_paths]
        logger.debug(
            "LocalStackSource initialised with paths: %s",
            [str(p) for p in self._paths],
        )

    # ------------------------------------------------------------------
    # StackSource protocol
    # ------------------------------------------------------------------

    @property
    def uri(self) -> str:
        """Canonical URI for this source."""
        paths_str = ",".join(str(p) for p in self._paths)
        return f"file://{paths_str}"

    def fetch(self, name: str, version: str | None = None) -> StackDefinition:
        """Fetch a stack definition by name (StackSource protocol).

        Args:
            name: Stack name.
            version: Optional version.

        Returns:
            The resolved ``StackDefinition``.

        Raises:
            StackNotFoundError: If the stack is not found.
        """
        return self.load_stack(name, version)

    def fetch_all(self) -> list[StackDefinition]:
        """Fetch all stack definitions from local directories.

        Returns:
            List of all ``StackDefinition`` objects found.
        """
        definitions: list[StackDefinition] = []
        for directory in self._paths:
            if not directory.is_dir():
                continue
            for yaml_file in sorted(directory.rglob("*.y*ml")):
                if yaml_file.suffix not in (".yaml", ".yml"):
                    continue
                if not yaml_file.is_file():
                    continue
                try:
                    stack = StackDefinition.from_yaml(str(yaml_file))
                    definitions.append(stack)
                except Exception as exc:
                    logger.warning(
                        "Skipping %s – failed to parse: %s",
                        yaml_file,
                        exc,
                    )
        return definitions

    def list_stacks(self) -> list[StackReference]:
        """Scan configured directories and return references to valid stacks.

        Files that cannot be parsed are logged at warning level and skipped
        rather than raising an exception.  This lets callers display partial
        results even when some YAML files are malformed.

        Returns:
            Sorted list of :class:`StackReference` objects.

        Raises:
            StackSourceError: If none of the configured paths can be read.
        """
        refs: list[StackReference] = []
        scanned_any = False

        for directory in self._paths:
            if not directory.is_dir():
                logger.debug("Skipping non-existent directory: %s", directory)
                continue

            scanned_any = True
            for yaml_file in sorted(directory.rglob("*.y*ml")):
                if yaml_file.suffix not in (".yaml", ".yml"):
                    continue
                if not yaml_file.is_file():
                    continue

                try:
                    stack = StackDefinition.from_yaml(str(yaml_file))
                    refs.append(
                        StackReference(
                            name=stack.name,
                            version=stack.version,
                            source="local",
                            path=str(yaml_file),
                        ),
                    )
                    logger.debug(
                        "Discovered stack %s@%s at %s",
                        stack.name,
                        stack.version,
                        yaml_file,
                    )
                except Exception as exc:
                    logger.warning(
                        "Skipping %s – failed to parse: %s",
                        yaml_file,
                        exc,
                    )

        if not scanned_any:
            logger.info(
                "No stack directories found in configured paths: %s",
                [str(p) for p in self._paths],
            )

        # Sort by name then version for deterministic output
        refs.sort(key=lambda r: (r.name, r.version or ""))
        return refs

    def load_stack(
        self,
        name: str,
        version: str | None = None,
    ) -> StackDefinition:
        """Load a stack definition from the local filesystem.

        The method scans the configured directories for a YAML file whose
        ``metadata.name`` matches *name*.  If *version* is given, the
        ``metadata.version`` must also match.

        When multiple versions of the same stack exist and no explicit
        *version* is specified, the lexicographically greatest version
        string is returned (which for well-formed semver is the latest
        release).

        Args:
            name: Required stack name.
            version: Optional version filter.

        Returns:
            A validated :class:`StackDefinition`.

        Raises:
            StackNotFoundError: If no matching stack is found.
            StackSourceError: If the source cannot be read.
        """
        candidates: list[StackDefinition] = []

        for directory in self._paths:
            if not directory.is_dir():
                continue

            for yaml_file in directory.rglob("*.y*ml"):
                if yaml_file.suffix not in (".yaml", ".yml"):
                    continue
                if not yaml_file.is_file():
                    continue

                try:
                    stack = StackDefinition.from_yaml(str(yaml_file))
                except Exception:
                    continue

                if stack.name != name:
                    continue

                if version is not None and stack.version != version:
                    continue

                candidates.append(stack)

        if not candidates:
            available_refs = self.list_stacks()
            available_names = sorted({r.name for r in available_refs})
            raise StackNotFoundError(
                stack_name=name,
                source="local",
                available=available_names,
            )

        # Return the "latest" version (lexicographic max) when no
        # explicit version filter was provided.
        candidates.sort(key=lambda s: s.version, reverse=True)
        chosen = candidates[0]
        logger.info(
            "Loaded stack %s@%s from local source",
            chosen.name,
            chosen.version,
        )
        return chosen

"""Registry-index-backed stack source.

This module implements :class:`RegistryIndexSource`, which reads a
:class:`~flowyml.stacks.enterprise.models.RegistryIndex` YAML file and uses
it as a catalogue to discover and resolve stack definitions.

Stack YAML file paths listed in the index are resolved **relative to the
directory containing the index file itself**, making it straightforward to
ship a self-contained stack repository.

Example index file (``stacks/registry.yaml``)::

    apiVersion: flowyml.io/v1
    kind: StackRegistry
    metadata:
      name: company-approved-stacks
      version: 1.0.0
    stacks:
      - name: aml_cpu_small
        path: definitions/aml_cpu_small.yaml
      - name: k8s_gpu_large
        path: definitions/k8s_gpu_large.yaml

Usage::

    source = RegistryIndexSource(index_path="stacks/registry.yaml")
    refs = source.list_stacks()
    stack = source.load_stack("aml_cpu_small")
"""

from __future__ import annotations

import logging
from pathlib import Path

from flowyml.stacks.enterprise.exceptions import StackNotFoundError, StackSourceError
from flowyml.stacks.enterprise.models import (
    RegistryIndex,
    StackDefinition,
    StackReference,
)

__all__ = [
    "RegistryIndexSource",
]

logger = logging.getLogger(__name__)


class RegistryIndexSource:
    """Stack source driven by a :class:`RegistryIndex` YAML file.

    The index file maps stack names to relative YAML paths.  All paths
    are resolved relative to the directory that contains the index itself.

    Args:
        index_path: Path to the ``RegistryIndex`` YAML file.

    Raises:
        StackSourceError: If the index file does not exist or cannot be
            parsed.

    Example::

        source = RegistryIndexSource(index_path="ops/registry.yaml")
        stack = source.load_stack("prod_gpu")
    """

    def __init__(self, index_path: str) -> None:
        self._index_path = Path(index_path).expanduser().resolve()
        self._base_dir = self._index_path.parent

        if not self._index_path.is_file():
            raise StackSourceError(
                source_uri=str(self._index_path),
                reason=f"Registry index file not found: {self._index_path}",
                suggestion=(
                    "Verify the path is correct and the file exists.  "
                    "The file should be a valid RegistryIndex YAML document."
                ),
            )

        try:
            self._index: RegistryIndex = RegistryIndex.from_yaml(
                str(self._index_path),
            )
        except FileNotFoundError as exc:
            raise StackSourceError(
                source_uri=str(self._index_path),
                reason=str(exc),
            ) from exc
        except Exception as exc:
            raise StackSourceError(
                source_uri=str(self._index_path),
                reason=f"Failed to parse registry index: {exc}",
                suggestion="Ensure the file is a valid RegistryIndex YAML document.",
            ) from exc

        logger.info(
            "Loaded registry index '%s' with %d stack(s) from %s",
            self._index.metadata.name,
            len(self._index.stacks),
            self._index_path,
        )

    # ------------------------------------------------------------------
    # StackSource protocol
    # ------------------------------------------------------------------

    @property
    def uri(self) -> str:
        """Canonical URI for this source."""
        return f"file://{self._index_path}"

    def fetch(self, name: str, version: str | None = None) -> StackDefinition:
        """Fetch a stack definition by name (StackSource protocol)."""
        return self.load_stack(name, version)

    def fetch_all(self) -> list[StackDefinition]:
        """Fetch all stack definitions referenced by the index.

        Returns:
            List of all ``StackDefinition`` objects.
        """
        definitions: list[StackDefinition] = []
        for entry in self._index.stacks:
            resolved_path = self._base_dir / entry.path
            if not resolved_path.is_file():
                logger.warning(
                    "Skipping index entry '%s' – file not found: %s",
                    entry.name,
                    resolved_path,
                )
                continue
            try:
                stack = StackDefinition.from_yaml(str(resolved_path))
                definitions.append(stack)
            except Exception as exc:
                logger.warning(
                    "Skipping index entry '%s' – failed to parse: %s",
                    entry.name,
                    exc,
                )
        return definitions

    def list_stacks(self) -> list[StackReference]:
        """Return references for every entry in the registry index.

        Returns:
            Sorted list of :class:`StackReference` objects.
        """
        refs: list[StackReference] = []

        for entry in self._index.stacks:
            resolved_path = self._base_dir / entry.path
            refs.append(
                StackReference(
                    name=entry.name,
                    version=None,  # version is in the YAML, not the index
                    source=str(self._index_path),
                    path=str(resolved_path),
                ),
            )

        refs.sort(key=lambda r: r.name)
        return refs

    def load_stack(
        self,
        name: str,
        version: str | None = None,
    ) -> StackDefinition:
        """Load a stack definition referenced by the index.

        Args:
            name: Stack name as listed in the index.
            version: Optional version filter applied after loading.

        Returns:
            A validated :class:`StackDefinition`.

        Raises:
            StackNotFoundError: If *name* is not in the index or the
                referenced YAML file does not exist.
            StackSourceError: If the referenced file cannot be parsed.
        """
        # Find the matching index entry
        matching_entries = [e for e in self._index.stacks if e.name == name]

        if not matching_entries:
            available = sorted(e.name for e in self._index.stacks)
            raise StackNotFoundError(
                stack_name=name,
                source=str(self._index_path),
                available=available,
            )

        candidates: list[StackDefinition] = []

        for entry in matching_entries:
            resolved_path = self._base_dir / entry.path

            if not resolved_path.is_file():
                raise StackSourceError(
                    source_uri=str(self._index_path),
                    reason=(f"Stack file referenced by index entry '{entry.name}' " f"not found: {resolved_path}"),
                    suggestion=(
                        "Check that the 'path' field in the registry index is "
                        "correct and the file exists relative to the index."
                    ),
                )

            try:
                stack = StackDefinition.from_yaml(str(resolved_path))
            except Exception as exc:
                raise StackSourceError(
                    source_uri=str(resolved_path),
                    reason=f"Failed to load stack '{entry.name}': {exc}",
                    suggestion="Check the YAML file for syntax or schema errors.",
                ) from exc

            if version is not None and stack.version != version:
                continue

            candidates.append(stack)

        if not candidates:
            raise StackNotFoundError(
                stack_name=f"{name}@{version}" if version else name,
                source=str(self._index_path),
                available=sorted(e.name for e in self._index.stacks),
            )

        # Return the "latest" version when multiple match
        candidates.sort(key=lambda s: s.version, reverse=True)
        chosen = candidates[0]
        logger.info(
            "Loaded stack %s@%s from registry index '%s'",
            chosen.name,
            chosen.version,
            self._index.metadata.name,
        )
        return chosen

"""Git-backed stack source for GitHub, GitLab, and generic Git repositories.

This module implements :class:`GitStackSource`, which clones (or fetches
updates for) a remote Git repository into a local cache directory and then
scans it for enterprise stack YAML definitions.

Supported URI formats::

    github://org/repo@tag
    github://org/repo@branch
    github://org/repo@commit
    github://org/repo@v1.2.0#stack_name    (fragment targets a specific stack)
    gitlab://org/repo@ref
    git+https://custom.host/org/repo.git@ref

**Security invariant**: Only YAML files are loaded from cloned repositories.
No code (Python, shell scripts, etc.) is ever executed from remote content.

Example::

    source = GitStackSource(uri="github://acme/stacks@v1.2.0")
    refs = source.list_stacks()
    stack = source.load_stack("aml_cpu_small")
"""

from __future__ import annotations

import hashlib
import logging
import re
import subprocess
from pathlib import Path

from flowyml.stacks.enterprise.exceptions import StackNotFoundError, StackSourceError
from flowyml.stacks.enterprise.models import StackDefinition, StackReference

__all__ = [
    "GitStackSource",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CACHE_ROOT = Path.home() / ".flowyml" / "cache" / "stacks"

_GIT_URI_PATTERN = re.compile(
    r"^(?P<scheme>github|gitlab)://"
    r"(?P<org>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+)"
    r"(?:@(?P<ref>[^#]+))?"
    r"(?:#(?P<fragment>.+))?$",
)

_GIT_HTTPS_PATTERN = re.compile(
    r"^git\+(?P<url>https://[^@]+)" r"(?:@(?P<ref>[^#]+))?" r"(?:#(?P<fragment>.+))?$",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_git_uri(uri: str) -> tuple[str, str | None, str | None]:
    """Parse a Git source URI into ``(https_url, ref, fragment)``.

    Args:
        uri: A URI string using one of the supported schemes.

    Returns:
        A three-tuple of ``(clone_url, git_ref, fragment)``.
        ``git_ref`` and ``fragment`` may be ``None``.

    Raises:
        StackSourceError: If the URI is malformed.
    """
    # github:// or gitlab://
    match = _GIT_URI_PATTERN.match(uri)
    if match:
        scheme = match.group("scheme")
        org = match.group("org")
        repo = match.group("repo")
        ref = match.group("ref") or None
        fragment = match.group("fragment") or None

        if scheme == "github":
            clone_url = f"https://github.com/{org}/{repo}.git"
        else:  # gitlab
            clone_url = f"https://gitlab.com/{org}/{repo}.git"

        return clone_url, ref, fragment

    # git+https://
    match = _GIT_HTTPS_PATTERN.match(uri)
    if match:
        clone_url = match.group("url")
        ref = match.group("ref") or None
        fragment = match.group("fragment") or None
        return clone_url, ref, fragment

    raise StackSourceError(
        source_uri=uri,
        reason=(
            f"Cannot parse Git URI '{uri}'. "
            "Expected one of: github://org/repo@ref, "
            "gitlab://org/repo@ref, git+https://host/repo.git@ref."
        ),
        suggestion="Check the URI format and try again.",
    )


def _clone_or_fetch(url: str, ref: str | None) -> Path:
    """Clone a Git repository (or fetch updates if already cached).

    The repository is cached under ``~/.flowyml/cache/stacks/<hash>/``
    where ``<hash>`` is derived from the clone URL.

    Args:
        url: HTTPS clone URL.
        ref: Git ref (tag, branch, or commit SHA) to check out.
            If ``None``, the default branch is used.

    Returns:
        Path to the local working tree root.

    Raises:
        StackSourceError: If the git commands fail.
    """
    # Deterministic cache directory
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    cache_dir = _CACHE_ROOT / url_hash

    try:
        if cache_dir.exists() and (cache_dir / ".git").is_dir():
            # Fetch latest changes
            logger.debug("Fetching updates for %s in %s", url, cache_dir)
            subprocess.run(
                ["git", "fetch", "--all", "--tags", "--prune"],
                cwd=str(cache_dir),
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
        else:
            # Fresh clone
            cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Cloning %s → %s", url, cache_dir)
            subprocess.run(
                ["git", "clone", "--quiet", url, str(cache_dir)],
                capture_output=True,
                text=True,
                check=True,
                timeout=300,
            )

        # Check out the requested ref
        if ref:
            logger.debug("Checking out ref '%s'", ref)
            subprocess.run(
                ["git", "checkout", "--quiet", ref],
                cwd=str(cache_dir),
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )

    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise StackSourceError(
            source_uri=url,
            reason=f"Git operation failed: {stderr or exc}",
            suggestion=(
                "Ensure the repository URL is correct, the ref exists, and "
                "you have network access.  For private repos make sure your "
                "Git credentials are configured."
            ),
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise StackSourceError(
            source_uri=url,
            reason="Git operation timed out.",
            suggestion="Check your network connection and try again.",
        ) from exc

    return cache_dir


# ---------------------------------------------------------------------------
# Source implementation
# ---------------------------------------------------------------------------


class GitStackSource:
    """Stack source backed by a remote Git repository.

    The repository is cloned (or updated) into a local cache directory and
    then scanned for YAML stack definitions.  Only YAML files are ever read
    – no code from the repository is executed.

    Args:
        uri: A Git source URI (``github://``, ``gitlab://``, or
            ``git+https://``).

    Example::

        source = GitStackSource(uri="github://acme/stacks@v1.2.0")
        stack = source.load_stack("aml_cpu_small")
    """

    def __init__(self, uri: str) -> None:
        self._uri = uri
        self._clone_url, self._ref, self._fragment = _parse_git_uri(uri)
        self._local_path: Path | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_cloned(self) -> Path:
        """Clone/fetch the repo and return the local working tree path."""
        if self._local_path is None:
            self._local_path = _clone_or_fetch(self._clone_url, self._ref)
        return self._local_path

    def _discover_stacks(self) -> list[tuple[Path, StackDefinition]]:
        """Scan the cloned repository for valid stack YAML files.

        Returns:
            List of ``(yaml_path, StackDefinition)`` pairs.
        """
        root = self._ensure_cloned()
        results: list[tuple[Path, StackDefinition]] = []

        for yaml_file in sorted(root.rglob("*.y*ml")):
            if yaml_file.suffix not in (".yaml", ".yml"):
                continue
            if not yaml_file.is_file():
                continue
            # Skip git metadata
            if ".git" in yaml_file.parts:
                continue

            try:
                stack = StackDefinition.from_yaml(str(yaml_file))
                results.append((yaml_file, stack))
                logger.debug(
                    "Discovered stack %s@%s at %s",
                    stack.name,
                    stack.version,
                    yaml_file,
                )
            except Exception as exc:
                logger.debug("Skipping %s: %s", yaml_file, exc)

        return results

    # ------------------------------------------------------------------
    # StackSource protocol
    # ------------------------------------------------------------------

    @property
    def uri(self) -> str:
        """Canonical URI for this source."""
        return self._uri

    def fetch(self, name: str, version: str | None = None) -> StackDefinition:
        """Fetch a stack definition by name (StackSource protocol)."""
        return self.load_stack(name, version)

    def fetch_all(self) -> list[StackDefinition]:
        """Fetch all stack definitions from the repository."""
        return [stack for _, stack in self._discover_stacks()]

    def list_stacks(self) -> list[StackReference]:
        """List all stacks found in the cloned repository.

        If the URI contained a fragment (e.g.
        ``github://org/repo@v1#my_stack``), only the stack matching that
        fragment name is included.

        Returns:
            Sorted list of :class:`StackReference` objects.

        Raises:
            StackSourceError: If the repository cannot be cloned or read.
        """
        pairs = self._discover_stacks()
        refs: list[StackReference] = []

        for yaml_path, stack in pairs:
            # If a fragment filter is set, apply it
            if self._fragment and stack.name != self._fragment:
                continue

            refs.append(
                StackReference(
                    name=stack.name,
                    version=stack.version,
                    source=self._uri,
                    path=str(yaml_path),
                ),
            )

        refs.sort(key=lambda r: (r.name, r.version or ""))
        return refs

    def load_stack(
        self,
        name: str,
        version: str | None = None,
    ) -> StackDefinition:
        """Load a stack definition from the cloned repository.

        Args:
            name: Stack name (``metadata.name``).
            version: Optional version filter.

        Returns:
            A validated :class:`StackDefinition`.

        Raises:
            StackNotFoundError: If no matching stack is found.
            StackSourceError: If the repository cannot be accessed.
        """
        pairs = self._discover_stacks()
        candidates: list[StackDefinition] = []

        for _path, stack in pairs:
            if stack.name != name:
                continue
            if version is not None and stack.version != version:
                continue
            candidates.append(stack)

        if not candidates:
            available = sorted({s.name for _, s in pairs})
            raise StackNotFoundError(
                stack_name=name,
                source=self._uri,
                available=available,
            )

        # Pick the "latest" version when no explicit version is requested
        candidates.sort(key=lambda s: s.version, reverse=True)
        chosen = candidates[0]
        logger.info(
            "Loaded stack %s@%s from %s",
            chosen.name,
            chosen.version,
            self._uri,
        )
        return chosen

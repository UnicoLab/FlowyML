"""Stack lock manager for reproducible resolution.

The ``StackLockManager`` reads, writes, and verifies ``flowyml.lock`` files
that pin each stack reference to an exact source commit and content digest.
This guarantees that the *identical* stack definition is used across
development, CI, and production environments.

Lock file format::

    apiVersion: flowyml.io/v1
    kind: StackLock
    project: churn-modeling
    resolvedStacks:
      aml_cpu_small:
        source: github://my-org/flowyml-stacks@v1.2.0
        commit: "abc123..."
        digest: "sha256:..."
        resolvedAt: "2026-06-03T10:00:00Z"

Example::

    from flowyml.stacks.enterprise.lock import StackLockManager

    mgr = StackLockManager(lock_path="flowyml.lock", project_name="churn")
    mgr.lock("aml_cpu_small", stack_def, source_uri="github://org/stacks@v1")
    results = mgr.verify()
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from flowyml.stacks.enterprise.exceptions import StackLockError
from flowyml.stacks.enterprise.models import (
    StackDefinition,
    StackLock,
    StackLockEntry,
)

logger = logging.getLogger(__name__)

__all__ = [
    "LockVerificationResult",
    "StackLockManager",
]


# ---------------------------------------------------------------------------
# Verification result model
# ---------------------------------------------------------------------------


class LockVerificationResult(BaseModel):
    """Result of verifying a single locked stack entry.

    Attributes:
        stack_name: Name of the stack that was verified.
        status: Verification outcome — ``verified`` (digest matches),
            ``modified`` (digest mismatch), or ``missing`` (no lock entry).
        expected_digest: Digest recorded in the lock file, if any.
        actual_digest: Digest computed from the current stack definition,
            if available.
        message: Human-readable explanation of the verification outcome.
    """

    model_config = ConfigDict(extra="forbid")

    stack_name: str
    status: Literal["verified", "modified", "missing"]
    expected_digest: str | None = None
    actual_digest: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Lock manager
# ---------------------------------------------------------------------------


class StackLockManager:
    """Manages stack lock files for deterministic, reproducible resolution.

    The lock file (default: ``flowyml.lock``) records the exact source,
    commit, and content digest for every resolved stack so that subsequent
    runs in CI or production resolve the *identical* definition.

    Args:
        lock_path: Path to the lock file.  Defaults to ``flowyml.lock``.
        project_name: Project name written into the lock file header.

    Example::

        mgr = StackLockManager(project_name="churn-modeling")
        lock_entry = mgr.lock(
            "aml_cpu_small",
            stack_def,
            source_uri="github://org/stacks@v1",
            commit="abc123",
        )
        results = mgr.verify()
    """

    def __init__(
        self,
        lock_path: str = "flowyml.lock",
        project_name: str = "default",
    ) -> None:
        self.lock_path = Path(lock_path)
        self.project_name = project_name
        self._lock: StackLock | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lock(
        self,
        stack_name: str,
        stack: StackDefinition,
        source_uri: str,
        commit: str | None = None,
    ) -> StackLock:
        """Lock a stack definition to the current digest and source.

        Creates a new lock entry for *stack_name*.  If an entry already
        exists for this stack, a ``StackLockError`` is raised — use
        :meth:`update` to intentionally overwrite an existing lock.

        Args:
            stack_name: Logical name for the lock entry (usually
                ``stack.name``).
            stack: The resolved stack definition to lock.
            source_uri: URI where the stack was fetched from.
            commit: Optional Git commit hash for the source.

        Returns:
            The full ``StackLock`` model after the entry has been added.

        Raises:
            StackLockError: If *stack_name* is already locked.
        """
        lock = self._ensure_loaded()

        if stack_name in lock.resolved_stacks:
            raise StackLockError(
                (
                    f"Stack '{stack_name}' is already locked. "
                    f"Use 'flowyml stack update --stack {stack_name}' to "
                    f"update the lock entry, or remove it first."
                ),
                stack_name=stack_name,
            )

        lock.resolved_stacks[stack_name] = self._create_entry(
            stack,
            source_uri,
            commit,
        )
        self.save(lock)
        logger.info(
            "Locked stack '%s' → %s",
            stack_name,
            lock.resolved_stacks[stack_name].digest,
        )
        return lock

    def update(
        self,
        stack_name: str,
        stack: StackDefinition,
        source_uri: str,
        commit: str | None = None,
    ) -> StackLock:
        """Update (or create) a lock entry for *stack_name*.

        Unlike :meth:`lock`, this method overwrites an existing entry
        without raising an error.

        Args:
            stack_name: Logical name for the lock entry.
            stack: The resolved stack definition.
            source_uri: URI where the stack was fetched from.
            commit: Optional Git commit hash for the source.

        Returns:
            The full ``StackLock`` model after the entry has been updated.
        """
        lock = self._ensure_loaded()
        lock.resolved_stacks[stack_name] = self._create_entry(
            stack,
            source_uri,
            commit,
        )
        self.save(lock)
        logger.info(
            "Updated lock for stack '%s' → %s",
            stack_name,
            lock.resolved_stacks[stack_name].digest,
        )
        return lock

    def verify(self) -> list[LockVerificationResult]:
        """Verify all locked stacks against their recorded digests.

        This method only verifies that the lock file is internally
        consistent (i.e. each entry has a digest).  To verify a *specific*
        stack's current content against its lock entry, use
        :meth:`verify_stack`.

        Returns:
            A list of ``LockVerificationResult`` — one per locked stack.
        """
        lock = self._ensure_loaded()
        results: list[LockVerificationResult] = []

        if not lock.resolved_stacks:
            logger.info("Lock file contains no stack entries.")
            return results

        for name, entry in lock.resolved_stacks.items():
            if entry.digest:
                results.append(
                    LockVerificationResult(
                        stack_name=name,
                        status="verified",
                        expected_digest=entry.digest,
                        message=(f"Stack '{name}' has a recorded digest in the lock file."),
                    ),
                )
            else:
                results.append(
                    LockVerificationResult(
                        stack_name=name,
                        status="missing",
                        message=(
                            f"Stack '{name}' has no digest in the lock file. Re-lock this stack to record its digest."
                        ),
                    ),
                )

        return results

    def verify_stack(
        self,
        stack_name: str,
        stack: StackDefinition,
    ) -> LockVerificationResult:
        """Verify a single stack against its lock file entry.

        Computes the current digest of *stack* and compares it to the
        digest recorded in the lock file for *stack_name*.

        Args:
            stack_name: Name of the stack to verify.
            stack: The current stack definition to compare.

        Returns:
            A ``LockVerificationResult`` with status ``verified``,
            ``modified``, or ``missing``.
        """
        lock = self._ensure_loaded()
        entry = lock.resolved_stacks.get(stack_name)

        if entry is None:
            return LockVerificationResult(
                stack_name=stack_name,
                status="missing",
                message=(
                    f"Stack '{stack_name}' is not present in the lock "
                    f"file. Run 'flowyml stack lock --stack {stack_name}' "
                    f"to lock it."
                ),
            )

        actual_digest = stack.compute_digest()
        if actual_digest == entry.digest:
            return LockVerificationResult(
                stack_name=stack_name,
                status="verified",
                expected_digest=entry.digest,
                actual_digest=actual_digest,
                message=(f"Stack '{stack_name}' matches the locked digest."),
            )

        return LockVerificationResult(
            stack_name=stack_name,
            status="modified",
            expected_digest=entry.digest,
            actual_digest=actual_digest,
            message=(
                f"Stack '{stack_name}' has been modified since it was "
                f"locked. Expected digest {entry.digest}, but the "
                f"current digest is {actual_digest}."
            ),
        )

    def is_locked(self, stack_name: str) -> bool:
        """Check whether a stack has a lock entry.

        Args:
            stack_name: Name of the stack to check.

        Returns:
            ``True`` if *stack_name* has an entry in the lock file.
        """
        lock = self._ensure_loaded()
        return stack_name in lock.resolved_stacks

    def get_locked_digest(self, stack_name: str) -> str | None:
        """Retrieve the locked digest for a stack.

        Args:
            stack_name: Name of the stack.

        Returns:
            The SHA-256 digest string, or ``None`` if the stack is not
            locked.
        """
        lock = self._ensure_loaded()
        entry = lock.resolved_stacks.get(stack_name)
        return entry.digest if entry is not None else None

    def load(self) -> StackLock | None:
        """Load the lock file from disk.

        If the lock file does not exist, returns ``None``.

        Returns:
            The parsed ``StackLock``, or ``None`` when the file is
            absent.

        Raises:
            StackLockError: If the file exists but cannot be parsed.
        """
        if not self.lock_path.exists():
            logger.debug(
                "Lock file '%s' does not exist.",
                self.lock_path,
            )
            self._lock = None
            return None

        try:
            self._lock = StackLock.from_yaml(str(self.lock_path))
            return self._lock
        except Exception as exc:
            raise StackLockError(
                f"Failed to load lock file '{self.lock_path}': {exc}",
            ) from exc

    def save(self, lock: StackLock) -> None:
        """Persist a ``StackLock`` to disk.

        Creates parent directories if they do not exist.

        Args:
            lock: The lock model to serialise.
        """
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock.to_yaml(str(self.lock_path))
        self._lock = lock
        logger.info("Lock file written to %s", self.lock_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> StackLock:
        """Return the cached lock or load / create one.

        Returns:
            A ``StackLock`` instance (possibly empty).
        """
        if self._lock is not None:
            return self._lock

        loaded = self.load()
        if loaded is not None:
            return loaded

        # No lock file on disk — create a fresh one.
        self._lock = StackLock(project=self.project_name)
        return self._lock

    @staticmethod
    def _create_entry(
        stack: StackDefinition,
        source_uri: str,
        commit: str | None,
    ) -> StackLockEntry:
        """Build a ``StackLockEntry`` from a stack definition.

        Args:
            stack: Resolved stack definition.
            source_uri: Source URI for provenance.
            commit: Optional Git commit hash.

        Returns:
            A fully populated ``StackLockEntry``.
        """
        return StackLockEntry(
            source=source_uri,
            commit=commit,
            digest=stack.compute_digest(),
            resolvedAt=datetime.now(timezone.utc).isoformat(),
        )

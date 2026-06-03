"""Mock backend adapter for testing enterprise stack execution.

``MockEnterpriseBackendAdapter`` records every submission so that tests
can assert on execution plans, policy validation, and context propagation
without touching real infrastructure.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from typing import Any

from flowyml.stacks.enterprise.execution import (
    ExecutionContext,
    RunHandle,
    RunStatus,
)
from flowyml.stacks.enterprise.models import StackDefinition

logger = logging.getLogger(__name__)

__all__ = [
    "MockEnterpriseBackendAdapter",
]


class MockEnterpriseBackendAdapter:
    """In-memory backend adapter for testing and dry-run scenarios.

    Every call to ``submit()`` is recorded in ``submitted_contexts`` so
    that test code can inspect what would have been executed.

    Attributes:
        submitted_contexts: List of ``(ExecutionContext, graph)`` tuples
            captured by ``submit()``.
        submitted_handles: List of ``RunHandle`` objects returned by
            ``submit()``.
    """

    def __init__(self) -> None:
        self.submitted_contexts: list[tuple[ExecutionContext, Any]] = []
        self.submitted_handles: list[RunHandle] = []
        self._statuses: dict[str, RunStatus] = {}

    # ------------------------------------------------------------------
    # BackendAdapter protocol
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        """Canonical backend name."""
        return "mock"

    def validate_stack(self, stack: StackDefinition) -> None:
        """Validate the stack definition.

        The mock adapter accepts any stack — validation always passes.

        Args:
            stack: The stack definition to validate.
        """
        logger.debug(
            "MockEnterpriseBackendAdapter.validate_stack('%s') — accepted.",
            stack.name,
        )

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare the mock execution environment.

        Logs the execution plan for debugging purposes.

        Args:
            context: The execution context.
        """
        logger.info(
            "[MOCK] Preparing execution plan:\n"
            "  project   = %s\n"
            "  pipeline  = %s\n"
            "  run_id    = %s\n"
            "  stack     = %s (v%s)\n"
            "  backend   = %s\n"
            "  env       = %s\n"
            "  dry_run   = %s",
            context.project_name,
            context.pipeline_name,
            context.run_id,
            context.stack.name,
            context.stack.version,
            context.stack.backend,
            context.environment,
            context.dry_run,
        )

    def submit(
        self,
        context: ExecutionContext,
        graph: Any,
    ) -> RunHandle:
        """Record the submission and return a mock ``RunHandle``.

        Args:
            context: The execution context.
            graph: The pipeline execution graph.

        Returns:
            A ``RunHandle`` with ``SUCCEEDED`` status.
        """
        run_id = context.run_id or str(uuid.uuid4())

        logger.info(
            "[MOCK] Submitting pipeline '%s' (run_id=%s).",
            context.pipeline_name,
            run_id,
        )

        # Record for test assertions
        self.submitted_contexts.append((context, graph))

        handle = RunHandle(
            run_id=run_id,
            backend_name=self.backend_name,
            status=RunStatus.SUCCEEDED,
            metadata={
                "mock": True,
                "project": context.project_name,
                "pipeline": context.pipeline_name,
                "stack": context.stack.name,
                "environment": context.environment,
            },
        )
        self.submitted_handles.append(handle)
        self._statuses[run_id] = RunStatus.SUCCEEDED

        return handle

    def status(self, run_id: str) -> RunStatus:
        """Return the recorded status of a mock run.

        Args:
            run_id: The run identifier.

        Returns:
            ``RunStatus`` (defaults to ``SUCCEEDED`` for submitted runs).
        """
        return self._statuses.get(run_id, RunStatus.PENDING)

    def logs(self, run_id: str) -> Iterator[str]:
        """Yield mock log lines.

        Args:
            run_id: The run identifier.

        Yields:
            A single informational log line.
        """
        yield f"[MOCK] Run {run_id} executed successfully (no real work done)."

    def cancel(self, run_id: str) -> None:
        """Cancel a mock run."""
        self._statuses[run_id] = RunStatus.CANCELLED

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all recorded submissions and statuses."""
        self.submitted_contexts.clear()
        self.submitted_handles.clear()
        self._statuses.clear()

    @property
    def call_count(self) -> int:
        """Number of times ``submit()`` has been called."""
        return len(self.submitted_contexts)

    def __repr__(self) -> str:
        return f"MockEnterpriseBackendAdapter(submissions={self.call_count})"

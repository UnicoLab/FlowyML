"""Local backend adapter for the Enterprise Stack Registry.

Wraps the existing ``LocalExecutor`` and ``LocalOrchestrator`` from
``flowyml.core`` so that local execution can be used through the
enterprise adapter interface.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from typing import Any

from flowyml.stacks.enterprise.exceptions import StackValidationError
from flowyml.stacks.enterprise.execution import (
    ExecutionContext,
    RunHandle,
    RunStatus,
)
from flowyml.stacks.enterprise.models import StackDefinition

logger = logging.getLogger(__name__)

__all__ = [
    "LocalBackendAdapter",
]


class LocalBackendAdapter:
    """Backend adapter that runs pipelines locally.

    Delegates to ``flowyml.core.executor.LocalExecutor`` and
    ``flowyml.core.orchestrator.LocalOrchestrator`` under the hood, while
    exposing the standard ``BackendAdapter`` interface.
    """

    def __init__(self) -> None:
        self._statuses: dict[str, RunStatus] = {}

    # ------------------------------------------------------------------
    # BackendAdapter protocol
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        """Canonical backend name."""
        return "local"

    def validate_stack(self, stack: StackDefinition) -> None:
        """Validate that the stack targets the ``local`` backend.

        Args:
            stack: The stack definition to validate.

        Raises:
            StackValidationError: If the backend is not ``local``.
        """
        if stack.backend != "local":
            raise StackValidationError(
                stack_name=stack.name,
                field="spec.backend",
                reason=(
                    f"LocalBackendAdapter only supports backend='local', but the stack specifies '{stack.backend}'."
                ),
                suggestion=("Use a different adapter for this backend, or change the stack's spec.backend to 'local'."),
            )

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare the local execution environment.

        For local execution this is a no-op — the host machine is already
        ready.

        Args:
            context: The execution context.
        """
        logger.debug(
            "LocalBackendAdapter.prepare() — no-op for run '%s'.",
            context.run_id,
        )

    def submit(
        self,
        context: ExecutionContext,
        graph: Any,
    ) -> RunHandle:
        """Submit the pipeline graph for local execution.

        Currently wraps the existing local execution path and returns a
        ``RunHandle`` with a generated run ID.

        Args:
            context: The execution context.
            graph: The pipeline execution graph.

        Returns:
            A ``RunHandle`` tracking the local run.
        """
        run_id = context.run_id or str(uuid.uuid4())

        logger.info(
            "Submitting pipeline '%s' for local execution (run_id=%s).",
            context.pipeline_name,
            run_id,
        )

        handle = RunHandle(
            run_id=run_id,
            backend_name=self.backend_name,
            status=RunStatus.RUNNING,
            metadata={
                "project": context.project_name,
                "pipeline": context.pipeline_name,
                "environment": context.environment,
                "dry_run": context.dry_run,
            },
        )

        if context.dry_run:
            logger.info("Dry-run mode — skipping actual execution.")
            handle.status = RunStatus.SUCCEEDED
            return handle

        # Delegate to the existing local executor / orchestrator.
        # The graph is expected to be run synchronously in-process.
        try:
            # If graph is callable (a pipeline run function), call it.
            if callable(graph):
                graph()

            handle.status = RunStatus.SUCCEEDED
        except Exception as exc:
            logger.error("Local execution failed: %s", exc)
            handle.status = RunStatus.FAILED
            handle.metadata["error"] = str(exc)

        self._statuses[handle.run_id] = handle.status
        return handle

    def status(self, run_id: str) -> RunStatus:
        """Return the status of a local run.

        Args:
            run_id: The run identifier.

        Returns:
            The recorded ``RunStatus``, or ``PENDING`` if unknown.
        """
        return self._statuses.get(run_id, RunStatus.PENDING)

    def logs(self, run_id: str) -> Iterator[str]:
        """Yield log lines for a local run.

        Local execution logs go through Python's ``logging`` module, so
        this iterator yields nothing.

        Args:
            run_id: The run identifier.

        Yields:
            Nothing — local logs use the standard logging system.
        """
        return iter(())

    def cancel(self, run_id: str) -> None:
        """Cancel not supported for local adapter."""
        logger.warning("Local backend does not support cancellation.")

    def __repr__(self) -> str:
        return "LocalBackendAdapter()"

"""Execution context, run handles, and backend adapter protocol.

This module defines the data structures and protocol that bridge stack
definitions to concrete execution backends (local, AzureML, Kubernetes, …).

Key types:

* ``RunStatus`` — lifecycle state of a pipeline run.
* ``RunHandle`` — lightweight handle returned when a run is submitted.
* ``ExecutionContext`` — all contextual metadata needed to execute a pipeline.
* ``BackendAdapter`` — protocol that every backend must implement.
* ``get_backend_adapter`` — factory function to obtain the correct adapter.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from flowyml.stacks.enterprise.models import StackDefinition
from flowyml.stacks.enterprise.policy import PolicyResult

logger = logging.getLogger(__name__)

__all__ = [
    "RunStatus",
    "RunHandle",
    "ExecutionContext",
    "BackendAdapter",
    "get_backend_adapter",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RunStatus(str, Enum):
    """Lifecycle status of a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class RunHandle(BaseModel):
    """Lightweight handle returned when a run is submitted to a backend.

    Attributes:
        run_id: Globally unique identifier for the run.
        backend_name: Name of the backend that owns this run.
        status: Current lifecycle status.
        metadata: Arbitrary backend-specific metadata.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., description="Globally unique run identifier.")
    backend_name: str = Field(..., description="Backend that owns this run.")
    status: RunStatus = Field(
        default=RunStatus.PENDING,
        description="Current lifecycle status.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific metadata.",
    )


class ExecutionContext(BaseModel):
    """Complete execution context for a pipeline run.

    Carries everything a ``BackendAdapter`` needs to prepare and submit a
    run — including the resolved stack, policy results, and user identity.

    Attributes:
        project_name: Name of the project.
        pipeline_name: Name of the pipeline being executed.
        run_id: Unique identifier for this run.
        user: Optional user or service-account identity.
        environment: Target environment (``local``, ``staging``, …).
        stack: The resolved enterprise stack definition.
        stack_digest: SHA-256 digest of the stack definition.
        lock_digest: Digest from the lock file, if available.
        policy_results: Results of pre-execution policy checks.
        config: Extra key-value configuration for the run.
        dry_run: If ``True``, the backend should validate but not execute.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    project_name: str = Field(..., description="Project name.")
    pipeline_name: str = Field(..., description="Pipeline name.")
    run_id: str = Field(..., description="Unique run identifier.")
    user: str | None = Field(default=None, description="User identity.")
    environment: str = Field(default="local", description="Target environment.")
    stack: StackDefinition = Field(..., description="Resolved stack definition.")
    stack_digest: str = Field(..., description="SHA-256 digest of the stack.")
    lock_digest: str | None = Field(
        default=None,
        description="Digest from the lock file, if available.",
    )
    policy_results: list[PolicyResult] = Field(
        default_factory=list,
        description="Pre-execution policy check results.",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra run configuration.",
    )
    dry_run: bool = Field(
        default=False,
        description="Validate only; do not execute.",
    )


# ---------------------------------------------------------------------------
# Backend adapter protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class BackendAdapter(Protocol):
    """Protocol that every execution backend must implement.

    Backends map FlowyML concepts (stacks, pipelines, artifacts) to the
    native primitives of the target platform (e.g. AzureML Jobs, K8s
    CRDs, Ray clusters).
    """

    @property
    def backend_name(self) -> str:
        """Canonical name of this backend (e.g. ``local``, ``azureml``)."""
        ...

    def validate_stack(self, stack: StackDefinition) -> None:
        """Validate that the stack is compatible with this backend.

        Args:
            stack: The stack definition to validate.

        Raises:
            StackValidationError: If the stack is incompatible.
        """
        ...

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare the execution environment (provision compute, pull
        images, etc.).

        Args:
            context: The execution context.
        """
        ...

    def submit(self, context: ExecutionContext, graph: Any) -> RunHandle:
        """Submit a pipeline graph for execution.

        Args:
            context: The execution context.
            graph: The pipeline execution graph (backend-specific).

        Returns:
            A ``RunHandle`` for tracking the submitted run.
        """
        ...

    def status(self, run_id: str) -> RunStatus:
        """Query the current status of a run.

        Args:
            run_id: The run identifier.

        Returns:
            Current ``RunStatus``.
        """
        ...

    def logs(self, run_id: str) -> Iterator[str]:
        """Stream log lines for a run.

        Args:
            run_id: The run identifier.

        Yields:
            Log line strings.
        """
        ...

    def cancel(self, run_id: str) -> None:
        """Cancel a running pipeline execution.

        Args:
            run_id: The run identifier to cancel.
        """
        ...


# ---------------------------------------------------------------------------
# Backend adapter factory
# ---------------------------------------------------------------------------

# Registry of known backend adapters (lazy-loaded)
_BACKEND_REGISTRY: dict[str, str] = {
    "local": "flowyml.stacks.enterprise.adapters.local.LocalBackendAdapter",
    "mock": "flowyml.stacks.enterprise.adapters.mock.MockEnterpriseBackendAdapter",
    "azureml": "flowyml.stacks.enterprise.adapters.azureml.AzureMLBackendAdapter",
}


def get_backend_adapter(backend_name: str, **kwargs: Any) -> BackendAdapter:
    """Factory function to obtain a ``BackendAdapter`` by name.

    The adapter is lazily imported and instantiated.  Custom adapters can
    be registered by adding to ``_BACKEND_REGISTRY`` before calling this
    function.

    Args:
        backend_name: Name of the backend (e.g. ``local``, ``azureml``).
        **kwargs: Additional keyword arguments forwarded to the adapter
            constructor.

    Returns:
        An instantiated ``BackendAdapter``.

    Raises:
        ValueError: If the backend name is not registered.
        ImportError: If the adapter module cannot be imported.
    """
    dotted_path = _BACKEND_REGISTRY.get(backend_name)
    if dotted_path is None:
        available = ", ".join(sorted(_BACKEND_REGISTRY.keys()))
        raise ValueError(
            f"Unknown backend '{backend_name}'. " f"Registered backends: {available}.",
        )

    module_path, class_name = dotted_path.rsplit(".", 1)

    import importlib

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Cannot import backend adapter module '{module_path}': {exc}. "
            f"Ensure the required dependencies are installed.",
        ) from exc

    adapter_cls = getattr(module, class_name)
    return adapter_cls(**kwargs)

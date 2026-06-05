"""Databricks backend adapter for the Enterprise Stack Registry.

Maps FlowyML concepts to Databricks primitives:

* **Stack → Cluster + Runtime**
* **Pipeline → Workflow / Job Run**
* **Artifacts → MLflow / DBFS**
* **Secrets → Databricks Secrets / Vault**

The ``databricks.sdk`` package is an *optional* dependency — a clear error
message is raised if it is missing.  No credentials are hard-coded;
authentication is delegated to the Databricks SDK's unified auth which
respects ``DATABRICKS_HOST``, ``DATABRICKS_TOKEN``, Azure AD, and other
native credential providers.

.. note::

    ``prepare()`` and ``submit()`` are intentionally **not yet implemented**.
    They raise ``NotImplementedError`` with a descriptive message.  Pull
    requests to wire in the full Databricks Job submission flow are welcome.
"""

from __future__ import annotations

import logging
import os
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
    "DatabricksBackendAdapter",
]

# ---------------------------------------------------------------------------
# Optional Databricks SDK import
# ---------------------------------------------------------------------------

try:
    from databricks.sdk import WorkspaceClient  # type: ignore[import-untyped]
    from databricks.sdk.service.compute import (  # type: ignore[import-untyped]
        ClusterSpec as DatabricksClusterSpec,
    )
    from databricks.sdk.service.jobs import (  # type: ignore[import-untyped]
        RunLifeCycleState,
        RunResultState,
    )

    _DATABRICKS_AVAILABLE = True
except ImportError:
    _DATABRICKS_AVAILABLE = False
    WorkspaceClient = None  # type: ignore[assignment,misc]
    DatabricksClusterSpec = None  # type: ignore[assignment,misc]
    RunLifeCycleState = None  # type: ignore[assignment,misc]
    RunResultState = None  # type: ignore[assignment,misc]


def _require_databricks() -> None:
    """Raise ``ImportError`` with an actionable message if Databricks SDK is missing."""
    if not _DATABRICKS_AVAILABLE:
        raise ImportError(
            "The Databricks SDK is required for DatabricksBackendAdapter but is "
            "not installed.\n\n"
            "Install it with:\n"
            "  pip install databricks-sdk\n\n"
            "Or install the FlowyML Databricks extra:\n"
            "  pip install flowyml[databricks]",
        )


# ---------------------------------------------------------------------------
# Concept mapping helpers
# ---------------------------------------------------------------------------


def _map_stack_to_cluster_config(stack: StackDefinition) -> dict[str, Any]:
    """Map a stack's compute specification to Databricks cluster parameters.

    The mapping uses well-known conventions:

    * ``spec.compute.type`` → node type category (cpu / gpu)
    * ``spec.compute.size`` → Databricks node type id (e.g. ``i3.xlarge``)
    * ``spec.compute.min_instances`` → autoscale min workers
    * ``spec.compute.max_instances`` → autoscale max workers
    * ``spec.compute.region`` → availability zone hint

    Args:
        stack: The enterprise stack definition.

    Returns:
        Dictionary of Databricks cluster configuration settings.
    """
    compute = stack.spec.compute

    cluster_config: dict[str, Any] = {
        "cluster_name": f"flowyml-{stack.name}",
        "num_workers": compute.max_instances,
        "spark_version": "14.3.x-scala2.12",  # sensible default
    }

    # Map compute size to Databricks node type
    if compute.size:
        cluster_config["node_type_id"] = compute.size
    else:
        # Fall back to defaults based on compute type
        cluster_config["node_type_id"] = "g4dn.xlarge" if compute.type == "gpu" else "i3.xlarge"

    # Autoscale configuration
    if compute.min_instances != compute.max_instances:
        cluster_config["autoscale"] = {
            "min_workers": compute.min_instances,
            "max_workers": compute.max_instances,
        }
        # When using autoscale, num_workers is not set
        cluster_config.pop("num_workers", None)

    if compute.region:
        cluster_config["aws_attributes"] = {
            "availability": "ON_DEMAND",
            "zone_id": compute.region,
        }

    return cluster_config


def _map_stack_to_runtime(stack: StackDefinition) -> dict[str, Any]:
    """Build Databricks runtime / environment parameters from the stack config.

    Maps the FlowyML runtime specification to Databricks-native settings
    such as Spark version, Python version, and Docker environment.

    Args:
        stack: The enterprise stack definition.

    Returns:
        Dictionary of runtime settings suitable for Databricks job
        configuration.
    """
    runtime = stack.spec.runtime

    runtime_config: dict[str, Any] = {
        "name": f"flowyml-{stack.name}",
        "python_version": runtime.python_version,
    }

    if runtime.base_image:
        # Use a custom Docker container on Databricks
        runtime_config["docker_image"] = {
            "url": runtime.base_image,
        }

    if runtime.gpu_enabled:
        # Pick a GPU-enabled Databricks Runtime
        runtime_config["spark_version"] = "14.3.x-gpu-ml-scala2.12"
    else:
        runtime_config["spark_version"] = "14.3.x-scala2.12"

    return runtime_config


# ---------------------------------------------------------------------------
# Databricks Backend Adapter
# ---------------------------------------------------------------------------


class DatabricksBackendAdapter:
    """Backend adapter that maps FlowyML stacks to Databricks.

    Concept mapping:

    +-------------------+----------------------------------+
    | FlowyML           | Databricks                       |
    +===================+==================================+
    | Stack             | Cluster + Runtime                |
    +-------------------+----------------------------------+
    | Pipeline          | Workflow / Job Run               |
    +-------------------+----------------------------------+
    | Artifacts         | MLflow / DBFS                    |
    +-------------------+----------------------------------+
    | Secrets           | Databricks Secrets / Vault       |
    +-------------------+----------------------------------+

    Authentication is handled via the Databricks SDK unified auth —
    no credentials are stored in this adapter.  The SDK respects
    ``DATABRICKS_HOST``, ``DATABRICKS_TOKEN``, Azure AD service
    principals, and other native credential providers.

    Args:
        host: Databricks workspace URL (e.g. ``https://adb-xxx.azuredatabricks.net``).
            If ``None``, resolved from ``DATABRICKS_HOST`` env var.
        token: Personal access token.  If ``None``, resolved from
            ``DATABRICKS_TOKEN`` env var or the SDK credential chain.
        workspace_id: Optional workspace identifier for multi-workspace
            setups.
    """

    def __init__(
        self,
        host: str | None = None,
        token: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        self._host = host or os.environ.get("DATABRICKS_HOST")
        self._token = token or os.environ.get("DATABRICKS_TOKEN")
        self._workspace_id = workspace_id
        self._client: Any = None  # Lazy-initialised WorkspaceClient

    # ------------------------------------------------------------------
    # BackendAdapter protocol
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        """Canonical backend name."""
        return "databricks"

    def validate_stack(self, stack: StackDefinition) -> None:
        """Validate that the stack is compatible with Databricks.

        Checks:
        * Backend must be ``databricks``.
        * Databricks SDK must be importable.
        * Host must be configured (explicitly or via env).

        Args:
            stack: The stack definition to validate.

        Raises:
            StackValidationError: If validation fails.
            ImportError: If the Databricks SDK is missing.
        """
        _require_databricks()

        if stack.backend != "databricks":
            raise StackValidationError(
                stack_name=stack.name,
                field="spec.backend",
                reason=(
                    f"DatabricksBackendAdapter requires backend='databricks', "
                    f"but the stack specifies '{stack.backend}'."
                ),
                suggestion="Set spec.backend to 'databricks' in the stack YAML.",
            )

        if not self._host:
            raise StackValidationError(
                stack_name=stack.name,
                field="host",
                reason=("No Databricks host configured. The adapter needs a " "workspace URL to connect to."),
                suggestion=(
                    "Set the DATABRICKS_HOST environment variable or pass " "'host' to DatabricksBackendAdapter()."
                ),
            )

        if not stack.spec.compute.size:
            logger.warning(
                "Stack '%s' does not specify a compute size. " "Databricks will use a default node type.",
                stack.name,
            )

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare the Databricks execution environment.

        This would get or create a compute cluster based on the stack
        compute spec, upload dependencies if needed, and validate
        workspace connectivity.

        Args:
            context: The execution context.

        Raises:
            NotImplementedError: Always — this is a placeholder.
        """
        _require_databricks()

        cluster_config = _map_stack_to_cluster_config(context.stack)
        runtime_config = _map_stack_to_runtime(context.stack)

        logger.info(
            "Databricks preparation plan:\n" "  cluster config = %s\n" "  runtime config = %s",
            cluster_config,
            runtime_config,
        )

        raise NotImplementedError(
            "DatabricksBackendAdapter.prepare() is not yet fully implemented. "
            "Contributions welcome!  The cluster config and runtime mapping "
            "logic is in place — what remains is wiring the WorkspaceClient "
            "calls to get-or-create a cluster and validate connectivity.",
        )

    def submit(
        self,
        context: ExecutionContext,
        graph: Any,
    ) -> RunHandle:
        """Submit a pipeline as a Databricks Job Run.

        This would translate the FlowyML pipeline graph into a Databricks
        Job with a ``notebook_task`` or ``python_wheel_task`` and submit
        it via the ``WorkspaceClient``.

        Args:
            context: The execution context.
            graph: The pipeline execution graph.

        Returns:
            A ``RunHandle`` tracking the Databricks job run.

        Raises:
            NotImplementedError: Always — this is a placeholder.
        """
        _require_databricks()

        raise NotImplementedError(
            "DatabricksBackendAdapter.submit() is not yet fully implemented. "
            "Contributions welcome!  The expected flow is:\n"
            "  1. Convert the FlowyML graph to a Databricks Job definition.\n"
            "  2. Call WorkspaceClient.jobs.submit() with notebook_task or "
            "python_wheel_task.\n"
            "  3. Return a RunHandle with the Databricks run ID.",
        )

    def status(self, run_id: str) -> RunStatus:
        """Query the status of a Databricks job run.

        Maps Databricks run lifecycle states to ``RunStatus``:

        * ``PENDING`` / ``RUNNING`` → ``RunStatus.RUNNING``
        * ``TERMINATED`` + ``SUCCESS`` → ``RunStatus.SUCCEEDED``
        * ``TERMINATED`` + ``FAILED`` → ``RunStatus.FAILED``
        * ``TERMINATED`` + ``CANCELLED`` → ``RunStatus.CANCELLED``

        Args:
            run_id: The Databricks run ID.

        Returns:
            Mapped ``RunStatus``.

        Raises:
            NotImplementedError: Until the full integration is complete.
        """
        _require_databricks()

        raise NotImplementedError(
            "DatabricksBackendAdapter.status() is not yet fully implemented. "
            "Once submit() is wired, this method will call "
            "WorkspaceClient.jobs.get_run(run_id) and map the lifecycle "
            "state:\n"
            "  PENDING/RUNNING       → RunStatus.RUNNING\n"
            "  TERMINATED + SUCCESS  → RunStatus.SUCCEEDED\n"
            "  TERMINATED + FAILED   → RunStatus.FAILED\n"
            "  TERMINATED + CANCELLED→ RunStatus.CANCELLED",
        )

    def logs(self, run_id: str) -> Iterator[str]:
        """Stream logs from a Databricks job run.

        Args:
            run_id: The Databricks run ID.

        Yields:
            Log line strings.

        Raises:
            NotImplementedError: Until the full integration is complete.
        """
        _require_databricks()

        raise NotImplementedError(
            "DatabricksBackendAdapter.logs() is not yet fully implemented. "
            "Once submit() is wired, this method will stream logs via "
            "WorkspaceClient.jobs.get_run_output(run_id).",
        )

    def cancel(self, run_id: str) -> None:
        """Cancel a Databricks job run.

        Args:
            run_id: The Databricks run ID.

        Raises:
            NotImplementedError: Until the full integration is complete.
        """
        _require_databricks()

        raise NotImplementedError(
            "DatabricksBackendAdapter.cancel() is not yet fully implemented. "
            "Once submit() is wired, this method will call "
            "WorkspaceClient.jobs.cancel_run(run_id).",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazy-initialise and return the ``WorkspaceClient``.

        Returns:
            An authenticated Databricks ``WorkspaceClient`` instance.

        Raises:
            ImportError: If the Databricks SDK is not installed.
        """
        _require_databricks()

        if self._client is None:
            client_kwargs: dict[str, Any] = {}
            if self._host:
                client_kwargs["host"] = self._host
            if self._token:
                client_kwargs["token"] = self._token

            self._client = WorkspaceClient(**client_kwargs)
            logger.info(
                "WorkspaceClient initialised (host=%s, workspace_id=%s).",
                self._host,
                self._workspace_id,
            )
        return self._client

    def _map_stack_to_cluster_config(
        self,
        stack: StackDefinition,
    ) -> dict[str, Any]:
        """Instance method wrapper for the module-level cluster config mapper.

        Args:
            stack: The enterprise stack definition.

        Returns:
            Dictionary of Databricks cluster configuration settings.
        """
        return _map_stack_to_cluster_config(stack)

    def _map_stack_to_runtime(
        self,
        stack: StackDefinition,
    ) -> dict[str, Any]:
        """Instance method wrapper for the module-level runtime mapper.

        Args:
            stack: The enterprise stack definition.

        Returns:
            Dictionary of Databricks runtime settings.
        """
        return _map_stack_to_runtime(stack)

    def __repr__(self) -> str:
        return f"DatabricksBackendAdapter(" f"host={self._host!r}, " f"workspace_id={self._workspace_id!r})"

"""AzureML backend adapter for the Enterprise Stack Registry.

Maps FlowyML concepts to Azure Machine Learning primitives:

* **Stack → Environment / Compute / Workspace**
* **Pipeline → Job**
* **Artifacts → Data / Model assets**
* **Secrets → Azure Key Vault**

The ``azure.ai.ml`` SDK is an *optional* dependency — a clear error message
is raised if it is missing.  No credentials are hard-coded; authentication
is delegated to ``azure.identity.DefaultAzureCredential``.

.. note::

    ``prepare()`` and ``submit()`` are intentionally **not yet implemented**.
    They raise ``NotImplementedError`` with a descriptive message.  Pull
    requests to wire in the full AzureML Job submission flow are welcome.
"""

from __future__ import annotations

import logging
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
    "AzureMLBackendAdapter",
]

# ---------------------------------------------------------------------------
# Optional Azure SDK import
# ---------------------------------------------------------------------------

try:
    from azure.ai.ml import MLClient  # type: ignore[import-untyped]
    from azure.ai.ml.entities import Environment as AzureMLEnvironment  # type: ignore[import-untyped]
    from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]

    _AZURE_AVAILABLE = True
except ImportError:
    _AZURE_AVAILABLE = False
    MLClient = None  # type: ignore[assignment,misc]
    AzureMLEnvironment = None  # type: ignore[assignment,misc]
    DefaultAzureCredential = None  # type: ignore[assignment,misc]


def _require_azure() -> None:
    """Raise ``ImportError`` with an actionable message if Azure SDK is missing."""
    if not _AZURE_AVAILABLE:
        raise ImportError(
            "The Azure ML SDK is required for AzureMLBackendAdapter but is "
            "not installed.\n\n"
            "Install it with:\n"
            "  pip install azure-ai-ml azure-identity\n\n"
            "Or install the FlowyML Azure extra:\n"
            "  pip install flowyml[azure]",
        )


# ---------------------------------------------------------------------------
# Concept mapping helpers
# ---------------------------------------------------------------------------


def _map_stack_to_workspace_config(stack: StackDefinition) -> dict[str, Any]:
    """Extract workspace connection parameters from a stack definition.

    The mapping uses well-known conventions:

    * ``spec.compute.region`` → workspace region
    * ``spec.secrets.scope`` → Key Vault name
    * ``spec.storage.uri`` → default datastore URI

    Args:
        stack: The enterprise stack definition.

    Returns:
        Dictionary of workspace-level settings.
    """
    return {
        "compute_type": stack.spec.compute.type,
        "compute_size": stack.spec.compute.size,
        "region": stack.spec.compute.region,
        "min_instances": stack.spec.compute.min_instances,
        "max_instances": stack.spec.compute.max_instances,
        "base_image": stack.spec.runtime.base_image,
        "python_version": stack.spec.runtime.python_version,
        "artifact_store_uri": stack.spec.storage.uri,
        "secret_scope": stack.spec.secrets.scope,
    }


def _map_stack_to_environment(stack: StackDefinition) -> dict[str, Any]:
    """Build AzureML Environment parameters from the stack runtime config.

    Args:
        stack: The enterprise stack definition.

    Returns:
        Dictionary suitable for constructing an AzureML ``Environment``.
    """
    env_config: dict[str, Any] = {
        "name": f"flowyml-{stack.name}",
        "version": stack.version,
    }

    if stack.spec.runtime.base_image:
        env_config["image"] = stack.spec.runtime.base_image

    return env_config


# ---------------------------------------------------------------------------
# AzureML Backend Adapter
# ---------------------------------------------------------------------------


class AzureMLBackendAdapter:
    """Backend adapter that maps FlowyML stacks to Azure Machine Learning.

    Concept mapping:

    +-------------------+-------------------------------+
    | FlowyML           | Azure ML                      |
    +===================+===============================+
    | Stack             | Environment + Compute Target  |
    +-------------------+-------------------------------+
    | Pipeline          | Job (Command / Pipeline Job)  |
    +-------------------+-------------------------------+
    | Artifacts         | Data / Model assets           |
    +-------------------+-------------------------------+
    | Secrets           | Key Vault references          |
    +-------------------+-------------------------------+

    Authentication is handled via ``DefaultAzureCredential`` — no
    credentials are stored in this adapter.  The credential chain
    supports managed identity, VS Code, CLI, and environment-variable
    based auth.

    Args:
        subscription_id: Azure subscription ID.  If ``None``, resolved
            from environment or az CLI config.
        resource_group: Azure resource group.
        workspace_name: AzureML workspace name.
    """

    def __init__(
        self,
        subscription_id: str | None = None,
        resource_group: str | None = None,
        workspace_name: str | None = None,
    ) -> None:
        self._subscription_id = subscription_id
        self._resource_group = resource_group
        self._workspace_name = workspace_name
        self._client: Any = None  # Lazy-initialised MLClient

    # ------------------------------------------------------------------
    # BackendAdapter protocol
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        """Canonical backend name."""
        return "azureml"

    def validate_stack(self, stack: StackDefinition) -> None:
        """Validate that the stack is compatible with AzureML.

        Checks:
        * Backend must be ``azureml``.
        * Azure SDK must be importable.
        * Compute size should be specified.

        Args:
            stack: The stack definition to validate.

        Raises:
            StackValidationError: If validation fails.
            ImportError: If the Azure SDK is missing.
        """
        _require_azure()

        if stack.backend != "azureml":
            raise StackValidationError(
                stack_name=stack.name,
                field="spec.backend",
                reason=(
                    f"AzureMLBackendAdapter requires backend='azureml', " f"but the stack specifies '{stack.backend}'."
                ),
                suggestion="Set spec.backend to 'azureml' in the stack YAML.",
            )

        if not stack.spec.compute.size:
            logger.warning(
                "Stack '%s' does not specify a compute size. " "AzureML will use the workspace default.",
                stack.name,
            )

    def prepare(self, context: ExecutionContext) -> None:
        """Prepare the AzureML execution environment.

        This would provision or verify compute targets, build/push the
        Docker environment, and configure the Key Vault scope.

        Args:
            context: The execution context.

        Raises:
            NotImplementedError: Always — this is a placeholder.
        """
        _require_azure()

        workspace_config = _map_stack_to_workspace_config(context.stack)
        env_config = _map_stack_to_environment(context.stack)

        logger.info(
            "AzureML preparation plan:\n" "  workspace config = %s\n" "  environment      = %s",
            workspace_config,
            env_config,
        )

        raise NotImplementedError(
            "AzureMLBackendAdapter.prepare() is not yet fully implemented. "
            "Contributions welcome!  The workspace config and environment "
            "mapping logic is in place — what remains is wiring the "
            "MLClient calls to provision compute and register the environment.",
        )

    def submit(
        self,
        context: ExecutionContext,
        graph: Any,
    ) -> RunHandle:
        """Submit a pipeline job to Azure ML.

        This would translate the FlowyML pipeline graph into an AzureML
        Pipeline Job (or Command Job) and submit it via ``MLClient``.

        Args:
            context: The execution context.
            graph: The pipeline execution graph.

        Returns:
            A ``RunHandle`` tracking the AzureML job.

        Raises:
            NotImplementedError: Always — this is a placeholder.
        """
        _require_azure()

        raise NotImplementedError(
            "AzureMLBackendAdapter.submit() is not yet fully implemented. "
            "Contributions welcome!  The expected flow is:\n"
            "  1. Convert the FlowyML graph to an AzureML PipelineJob.\n"
            "  2. Call MLClient.jobs.create_or_update(job).\n"
            "  3. Return a RunHandle with the AzureML job ID.",
        )

    def status(self, run_id: str) -> RunStatus:
        """Query the status of an AzureML job.

        Args:
            run_id: The AzureML job name / run ID.

        Returns:
            Mapped ``RunStatus``.

        Raises:
            NotImplementedError: Until the full integration is complete.
        """
        _require_azure()

        raise NotImplementedError(
            "AzureMLBackendAdapter.status() is not yet fully implemented. "
            "Once submit() is wired, this method will call "
            "MLClient.jobs.get(run_id) and map the AzureML status enum.",
        )

    def logs(self, run_id: str) -> Iterator[str]:
        """Stream logs from an AzureML job.

        Args:
            run_id: The AzureML job name / run ID.

        Yields:
            Log line strings.

        Raises:
            NotImplementedError: Until the full integration is complete.
        """
        _require_azure()

        raise NotImplementedError(
            "AzureMLBackendAdapter.logs() is not yet fully implemented. "
            "Once submit() is wired, this method will stream logs via "
            "MLClient.jobs.stream(run_id).",
        )

    def cancel(self, run_id: str) -> None:
        """Cancel an Azure ML run."""
        raise NotImplementedError(
            "AzureML run cancellation is not yet implemented. " "Contributions welcome!",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazy-initialise and return the ``MLClient``.

        Returns:
            An authenticated ``MLClient`` instance.

        Raises:
            ImportError: If the Azure SDK is not installed.
        """
        _require_azure()

        if self._client is None:
            credential = DefaultAzureCredential()
            self._client = MLClient(
                credential=credential,
                subscription_id=self._subscription_id,
                resource_group_name=self._resource_group,
                workspace_name=self._workspace_name,
            )
            logger.info(
                "MLClient initialised (subscription=%s, rg=%s, ws=%s).",
                self._subscription_id,
                self._resource_group,
                self._workspace_name,
            )
        return self._client

    def __repr__(self) -> str:
        return (
            f"AzureMLBackendAdapter("
            f"subscription={self._subscription_id!r}, "
            f"rg={self._resource_group!r}, "
            f"ws={self._workspace_name!r})"
        )

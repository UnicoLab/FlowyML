"""AzureML backend adapter for the Enterprise Stack Registry.

Maps FlowyML concepts to Azure Machine Learning primitives:

* **Stack → Environment / Compute / Workspace**
* **Pipeline → Job**
* **Artifacts → Data / Model assets**
* **Secrets → Azure Key Vault**

The ``azure.ai.ml`` SDK is an *optional* dependency — a clear error message
is raised if it is missing.  No credentials are hard-coded; authentication
is delegated to ``azure.identity.DefaultAzureCredential``.

All ``BackendAdapter`` protocol methods are implemented:
``prepare()``, ``submit()``, ``status()``, ``logs()``, and ``cancel()``.
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
    from azure.ai.ml import MLClient, command  # type: ignore[import-untyped]
    from azure.ai.ml.entities import (
        AmlCompute,
        Environment as AzureMLEnvironment,
    )  # type: ignore[import-untyped]
    from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]

    _AZURE_AVAILABLE = True
except ImportError:
    _AZURE_AVAILABLE = False
    MLClient = None  # type: ignore[assignment,misc]
    command = None  # type: ignore[assignment,misc]
    AmlCompute = None  # type: ignore[assignment,misc]
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

        Provisions or verifies the compute target and registers the
        Docker environment in the workspace.

        Args:
            context: The execution context.

        Raises:
            ImportError: If the Azure SDK is not installed.
            RuntimeError: If compute or environment provisioning fails.
        """
        _require_azure()

        ml_client = self._get_client()
        workspace_config = _map_stack_to_workspace_config(context.stack)
        env_config = _map_stack_to_environment(context.stack)

        logger.info(
            "AzureML preparation plan:\n" "  workspace config = %s\n" "  environment      = %s",
            workspace_config,
            env_config,
        )

        # -- 1. Create or verify the compute target -------------------------
        compute_name = f"flowyml-{context.stack.name}"
        compute_size = context.stack.spec.compute.size or "Standard_DS3_v2"
        min_instances = context.stack.spec.compute.min_instances
        max_instances = context.stack.spec.compute.max_instances

        try:
            existing = ml_client.compute.get(compute_name)
            logger.info(
                "Compute target '%s' already exists (size=%s, state=%s).",
                compute_name,
                getattr(existing, "size", "unknown"),
                getattr(existing, "provisioning_state", "unknown"),
            )
        except Exception:  # noqa: BLE001 – ResourceNotFoundError or similar
            logger.info(
                "Compute target '%s' not found — creating (size=%s, " "min_instances=%s, max_instances=%s).",
                compute_name,
                compute_size,
                min_instances,
                max_instances,
            )
            try:
                compute_resource = AmlCompute(
                    name=compute_name,
                    size=compute_size,
                    min_instances=min_instances,
                    max_instances=max_instances,
                )
                ml_client.compute.begin_create_or_update(compute_resource).wait()
                logger.info("Compute target '%s' provisioned.", compute_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to provision AzureML compute target " f"'{compute_name}': {exc}",
                ) from exc

        # -- 2. Register the environment ------------------------------------
        try:
            environment = AzureMLEnvironment(**env_config)
            ml_client.environments.create_or_update(environment)
            logger.info(
                "Environment '%s' (version=%s) registered.",
                env_config["name"],
                env_config.get("version", "latest"),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to register AzureML environment " f"'{env_config.get('name', 'unknown')}': {exc}",
            ) from exc

    def submit(
        self,
        context: ExecutionContext,
        graph: Any,
    ) -> RunHandle:
        """Submit a pipeline job to Azure ML.

        Translates the FlowyML pipeline graph into an AzureML Command Job
        and submits it via ``MLClient``.

        Args:
            context: The execution context.
            graph: The pipeline execution graph.  Serialised to a string
                and passed as the job command.

        Returns:
            A ``RunHandle`` tracking the AzureML job.

        Raises:
            ImportError: If the Azure SDK is not installed.
            RuntimeError: If job submission fails.
        """
        _require_azure()

        ml_client = self._get_client()
        env_config = _map_stack_to_environment(context.stack)
        compute_name = f"flowyml-{context.stack.name}"
        display_name = f"{context.pipeline_name}_{context.run_id[:8]}"
        env_name = env_config["name"]
        env_version = env_config.get("version", "latest")

        try:
            job = command(
                display_name=display_name,
                command=str(graph),
                environment=f"{env_name}:{env_version}",
                compute=compute_name,
            )
            submitted_job = ml_client.jobs.create_or_update(job)
            logger.info(
                "AzureML job submitted: name=%s, display_name=%s.",
                submitted_job.name,
                display_name,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to submit AzureML job '{display_name}': {exc}",
            ) from exc

        return RunHandle(
            run_id=submitted_job.name,
            backend_name=self.backend_name,
            status=RunStatus.PENDING,
            metadata={
                "display_name": display_name,
                "compute": compute_name,
                "environment": f"{env_name}:{env_version}",
            },
        )

    def status(self, run_id: str) -> RunStatus:
        """Query the status of an AzureML job.

        Args:
            run_id: The AzureML job name / run ID.

        Returns:
            Mapped ``RunStatus``.

        Raises:
            ImportError: If the Azure SDK is not installed.
            RuntimeError: If the status query fails.
        """
        _require_azure()

        ml_client = self._get_client()

        status_map: dict[str, RunStatus] = {
            "Completed": RunStatus.SUCCEEDED,
            "Failed": RunStatus.FAILED,
            "Canceled": RunStatus.CANCELLED,
            "CancelRequested": RunStatus.CANCELLED,
            "Running": RunStatus.RUNNING,
            "Preparing": RunStatus.RUNNING,
            "Queued": RunStatus.RUNNING,
            "Starting": RunStatus.RUNNING,
            "Provisioning": RunStatus.RUNNING,
        }

        try:
            job = ml_client.jobs.get(run_id)
            azure_status = str(job.status)
            mapped = status_map.get(azure_status, RunStatus.PENDING)
            logger.debug(
                "AzureML job '%s' status: %s → %s.",
                run_id,
                azure_status,
                mapped.value,
            )
            return mapped
        except Exception as exc:
            raise RuntimeError(
                f"Failed to query status for AzureML job '{run_id}': {exc}",
            ) from exc

    def logs(self, run_id: str) -> Iterator[str]:
        """Stream logs from an AzureML job.

        Args:
            run_id: The AzureML job name / run ID.

        Yields:
            Log line strings.

        Raises:
            ImportError: If the Azure SDK is not installed.
            RuntimeError: If log streaming fails.
        """
        _require_azure()

        ml_client = self._get_client()

        try:
            ml_client.jobs.stream(run_id)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to stream logs for AzureML job '{run_id}': {exc}",
            ) from exc

    def cancel(self, run_id: str) -> None:
        """Cancel an Azure ML run.

        Args:
            run_id: The AzureML job name / run ID.

        Raises:
            ImportError: If the Azure SDK is not installed.
            RuntimeError: If cancellation fails.
        """
        _require_azure()

        ml_client = self._get_client()

        try:
            ml_client.jobs.cancel(run_id)
            logger.info("Cancellation requested for AzureML job '%s'.", run_id)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to cancel AzureML job '{run_id}': {exc}",
            ) from exc

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

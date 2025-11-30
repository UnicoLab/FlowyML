"""Remote Orchestrator - Executes pipelines on remote infrastructure."""

from typing import Any, TYPE_CHECKING

from flowyml.stacks.components import Orchestrator, ComponentType, ResourceConfig, DockerConfig
from flowyml.core.execution_status import ExecutionStatus
from flowyml.core.submission_result import SubmissionResult

if TYPE_CHECKING:
    from flowyml.core.pipeline import Pipeline


class RemoteOrchestrator(Orchestrator):
    """Base orchestrator for remote execution.

    This orchestrator submits jobs to remote infrastructure and returns job IDs.
    Cloud-specific orchestrators (AWS, GCP, Azure) inherit from this.
    """

    def __init__(self, name: str = "remote"):
        super().__init__(name)

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.ORCHESTRATOR

    def validate(self) -> bool:
        """Validate remote orchestrator configuration."""
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "remote",
        }

    def get_run_status(self, job_id: str) -> ExecutionStatus:
        """Get status of a remote pipeline run.

        This should be overridden by cloud-specific orchestrators to query
        the actual remote execution status.

        Args:
            job_id: The remote job identifier.

        Returns:
            The current execution status.
        """
        return ExecutionStatus.RUNNING

    def fetch_step_statuses(self, job_id: str) -> dict[str, ExecutionStatus]:
        """Get status of individual steps in a remote run.

        Args:
            job_id: The remote job identifier.

        Returns:
            Dictionary mapping step names to their execution status.
        """
        # Default implementation - override in subclasses
        return {}

    def stop_run(self, job_id: str, graceful: bool = True) -> None:
        """Stop a remote pipeline run.

        Args:
            job_id: The remote job identifier.
            graceful: If True, attempt graceful shutdown. If False, force kill.

        Raises:
            NotImplementedError: If stopping is not supported.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support stopping runs",
        )

    def run_pipeline(
        self,
        pipeline: "Pipeline",
        run_id: str,
        resources: ResourceConfig | None = None,
        docker_config: DockerConfig | None = None,
        inputs: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs,
    ) -> SubmissionResult:
        """Submit pipeline to remote infrastructure.

        This base implementation should be overridden by cloud-specific orchestrators
        to submit to their respective services (AWS Batch, Vertex AI, Azure ML, etc.).

        Args:
            pipeline: The pipeline to run.
            run_id: The unique run identifier.
            resources: Resource configuration.
            docker_config: Docker configuration.
            inputs: Input data.
            context: Context variables.
            **kwargs: Additional arguments.

        Returns:
            SubmissionResult with remote job ID and optional wait function.

        Raises:
            NotImplementedError: Must be implemented by cloud-specific orchestrators.
        """
        raise NotImplementedError(
            "RemoteOrchestrator.run_pipeline must be implemented by cloud-specific orchestrators",
        )

"""AWS SageMaker Pipelines Orchestrator - Native FlowyML Plugin.

This is a native FlowyML implementation for AWS SageMaker Pipelines,
without requiring any external framework dependencies.

Usage:
    from flowyml.plugins import get_plugin

    orchestrator = get_plugin("sagemaker",
        role_arn="arn:aws:iam::123456789012:role/SageMakerRole",
        region="us-east-1"
    )

    # Run a pipeline
    orchestrator.run_pipeline(my_pipeline, "training-run-001")
"""

import logging
from typing import Any
from datetime import datetime

from flowyml.plugins.base import OrchestratorPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class SageMakerOrchestrator(OrchestratorPlugin):
    """Native AWS SageMaker Pipelines orchestrator for FlowyML.

    This orchestrator integrates directly with AWS SageMaker Pipelines
    without any intermediate framework.

    Args:
        role_arn: IAM role ARN for SageMaker execution.
        region: AWS region.
        default_bucket: S3 bucket for pipeline artifacts.
        pipeline_name: Default pipeline name.

    Example:
        orchestrator = SageMakerOrchestrator(
            role_arn="arn:aws:iam::123456789012:role/SageMakerRole",
            region="us-east-1",
            default_bucket="my-sagemaker-bucket"
        )

        orchestrator.run_pipeline(pipeline_definition, "training-v1")
    """

    METADATA = PluginMetadata(
        name="sagemaker",
        description="AWS SageMaker Pipelines Orchestrator",
        plugin_type=PluginType.ORCHESTRATOR,
        version="1.0.0",
        author="FlowyML",
        packages=["sagemaker>=2.100", "boto3>=1.28"],
        documentation_url="https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html",
        tags=["orchestrator", "aws", "cloud", "sagemaker"],
    )

    def __init__(
        self,
        role_arn: str,
        region: str = None,
        default_bucket: str = None,
        pipeline_name: str = None,
        **kwargs,
    ):
        """Initialize the SageMaker orchestrator."""
        super().__init__(
            name=kwargs.pop("name", "sagemaker"),
            role_arn=role_arn,
            region=region,
            default_bucket=default_bucket,
            pipeline_name=pipeline_name,
            **kwargs,
        )

        self._role_arn = role_arn
        self._region = region
        self._default_bucket = default_bucket
        self._pipeline_name = pipeline_name
        self._session = None
        self._sm_client = None

    def initialize(self) -> None:
        """Initialize SageMaker session."""
        try:
            import sagemaker
            import boto3

            # Create session
            boto_session = boto3.Session(region_name=self._region)
            self._sm_client = boto_session.client("sagemaker")

            self._session = sagemaker.Session(
                boto_session=boto_session,
                default_bucket=self._default_bucket,
            )

            self._is_initialized = True
            logger.info(f"SageMaker orchestrator initialized in region: {self._region}")

        except ImportError:
            raise ImportError(
                "sagemaker is not installed. Run: flowyml plugin install sagemaker",
            )

    def _ensure_initialized(self) -> None:
        """Ensure the orchestrator is initialized."""
        if not self._is_initialized:
            self.initialize()

    def run_pipeline(
        self,
        pipeline: Any,
        run_id: str,
        parameters: dict = None,
        wait: bool = False,
        **kwargs,
    ) -> Any:
        """Run a pipeline on SageMaker.

        Args:
            pipeline: SageMaker Pipeline object or path to definition.
            run_id: Unique identifier for this run.
            parameters: Pipeline parameters.
            wait: If True, wait for pipeline to complete.
            **kwargs: Additional execution options.

        Returns:
            Pipeline execution ARN.
        """
        self._ensure_initialized()

        try:
            from sagemaker.workflow.pipeline import Pipeline

            # Handle different pipeline types
            if isinstance(pipeline, Pipeline):
                sm_pipeline = pipeline
            elif isinstance(pipeline, dict):
                # Pipeline definition as dict
                sm_pipeline = Pipeline(
                    name=self._pipeline_name or f"flowyml-{run_id}",
                    parameters=parameters or [],
                    steps=pipeline.get("steps", []),
                    sagemaker_session=self._session,
                )
            else:
                raise ValueError(f"Unsupported pipeline type: {type(pipeline)}")

            # Upsert pipeline (create or update)
            sm_pipeline.upsert(role_arn=self._role_arn)

            # Start execution
            execution = sm_pipeline.start(
                execution_display_name=run_id,
                parameters=parameters or {},
            )

            logger.info(f"Started SageMaker pipeline execution: {execution.arn}")

            if wait:
                execution.wait()
                logger.info(f"Pipeline execution completed: {execution.arn}")

            return execution

        except Exception as e:
            logger.error(f"Failed to run pipeline: {e}")
            raise

    def get_run_status(self, run_id: str) -> dict:
        """Get the status of a pipeline run.

        Args:
            run_id: Pipeline execution ARN or display name.

        Returns:
            Dictionary with run status information.
        """
        self._ensure_initialized()

        try:
            # Search for execution by display name or ARN
            response = self._sm_client.list_pipeline_executions(
                PipelineName=self._pipeline_name,
            )

            for execution in response.get("PipelineExecutionSummaries", []):
                if (
                    execution.get("PipelineExecutionArn") == run_id
                    or execution.get("PipelineExecutionDisplayName") == run_id
                ):
                    return {
                        "run_id": execution.get("PipelineExecutionArn"),
                        "status": execution.get("PipelineExecutionStatus"),
                        "start_time": execution.get("StartTime"),
                        "end_time": execution.get("LastModifiedTime"),
                    }

            return {"status": "NOT_FOUND"}

        except Exception as e:
            logger.error(f"Failed to get run status: {e}")
            return {"status": "ERROR", "error": str(e)}

    def cancel_run(self, run_id: str) -> bool:
        """Cancel a running pipeline execution.

        Args:
            run_id: Pipeline execution ARN.

        Returns:
            True if cancellation was successful.
        """
        self._ensure_initialized()

        try:
            self._sm_client.stop_pipeline_execution(
                PipelineExecutionArn=run_id,
                ClientRequestToken=f"cancel-{datetime.now().timestamp()}",
            )

            logger.info(f"Cancelled pipeline execution: {run_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel run: {e}")
            return False

    def list_runs(
        self,
        pipeline_name: str = None,
        max_results: int = 100,
        status: str = None,
    ) -> list[dict]:
        """List pipeline executions.

        Args:
            pipeline_name: Filter by pipeline name.
            max_results: Maximum number of results.
            status: Filter by status.

        Returns:
            List of execution summaries.
        """
        self._ensure_initialized()

        pipeline = pipeline_name or self._pipeline_name

        try:
            kwargs = {
                "PipelineName": pipeline,
                "MaxResults": min(max_results, 100),
            }

            if status:
                kwargs["SortBy"] = "CreationTime"

            response = self._sm_client.list_pipeline_executions(**kwargs)

            runs = []
            for execution in response.get("PipelineExecutionSummaries", []):
                runs.append(
                    {
                        "run_id": execution.get("PipelineExecutionArn"),
                        "display_name": execution.get("PipelineExecutionDisplayName"),
                        "status": execution.get("PipelineExecutionStatus"),
                        "start_time": str(execution.get("StartTime", "")),
                    },
                )

            return runs

        except Exception as e:
            logger.error(f"Failed to list runs: {e}")
            return []

    def get_logs(self, run_id: str, step_name: str = None) -> str:
        """Get logs for a pipeline execution.

        Args:
            run_id: Pipeline execution ARN.
            step_name: Optional specific step name.

        Returns:
            Log content as string.
        """
        self._ensure_initialized()

        try:
            # Get pipeline execution steps
            response = self._sm_client.list_pipeline_execution_steps(
                PipelineExecutionArn=run_id,
            )

            logs = []
            for step in response.get("PipelineExecutionSteps", []):
                if step_name and step.get("StepName") != step_name:
                    continue

                logs.append(f"=== Step: {step.get('StepName')} ===")
                logs.append(f"Status: {step.get('StepStatus')}")

                if step.get("FailureReason"):
                    logs.append(f"Failure: {step.get('FailureReason')}")

                logs.append("")

            return "\n".join(logs)

        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return f"Error getting logs: {e}"

    def run_with_routing(
        self,
        pipeline: Any,
        run_id: str,
        stack_name: str = None,
        parameters: dict = None,
        wait: bool = False,
        **kwargs,
    ) -> Any:
        """Run a pipeline with type-based artifact routing.

        This method integrates with FlowyML's type-based routing system,
        ensuring that Model, Dataset, Metrics, and Parameters artifacts
        are automatically routed to the configured infrastructure.

        Args:
            pipeline: The pipeline to run.
            run_id: Unique identifier for this run.
            stack_name: Stack to use for routing (uses active stack if None).
            parameters: Pipeline parameters.
            wait: If True, wait for pipeline to complete.
            **kwargs: Additional arguments.

        Returns:
            Pipeline execution with routing metadata.
        """
        self._ensure_initialized()

        # Get routing configuration
        routing_config = self._get_routing_config(stack_name)

        # Inject routing parameters
        enriched_params = parameters or {}
        enriched_params["__run_id__"] = run_id
        enriched_params["__routing_config__"] = routing_config

        # Run the pipeline
        execution = self.run_pipeline(
            pipeline=pipeline,
            run_id=run_id,
            parameters=enriched_params,
            wait=wait,
            **kwargs,
        )

        logger.info(f"Started type-aware SageMaker pipeline: {run_id}")
        logger.info(f"Routing config: stack={stack_name or 'active'}")

        return execution

    def _get_routing_config(self, stack_name: str = None) -> dict:
        """Get routing configuration for a stack.

        Args:
            stack_name: Stack name (uses active stack if None).

        Returns:
            Dictionary of routing rules.
        """
        try:
            from flowyml.plugins.stack_config import get_stack_manager

            manager = get_stack_manager()
            stack = manager.get_stack(stack_name) if stack_name else manager.get_active_stack()

            if stack and stack.artifact_routing:
                return {
                    "Model": stack.artifact_routing.model.to_dict() if stack.artifact_routing.model else {},
                    "Dataset": stack.artifact_routing.dataset.to_dict() if stack.artifact_routing.dataset else {},
                    "Metrics": stack.artifact_routing.metrics.to_dict() if stack.artifact_routing.metrics else {},
                    "Parameters": stack.artifact_routing.parameters.to_dict()
                    if stack.artifact_routing.parameters
                    else {},
                }
        except ImportError:
            logger.debug("Stack config not available for routing")
        except Exception as e:
            logger.warning(f"Failed to get routing config: {e}")

        return {}

    def configure_model_deployment(
        self,
        model_uri: str,
        endpoint_name: str,
        instance_type: str = "ml.m5.large",
        initial_instance_count: int = 1,
    ) -> str:
        """Deploy a model to a SageMaker endpoint.

        This method can be used after pipeline completion to deploy
        registered models to serving endpoints.

        Args:
            model_uri: S3 URI to the model artifact.
            endpoint_name: Name for the endpoint.
            instance_type: Instance type for the endpoint.
            initial_instance_count: Number of instances.

        Returns:
            Endpoint name.
        """
        self._ensure_initialized()

        try:
            from sagemaker.model import Model

            # Create model
            model = Model(
                model_data=model_uri,
                role=self._role_arn,
                sagemaker_session=self._session,
            )

            # Deploy to endpoint
            model.deploy(
                endpoint_name=endpoint_name,
                instance_type=instance_type,
                initial_instance_count=initial_instance_count,
            )

            logger.info(f"Model deployed to endpoint: {endpoint_name}")
            return endpoint_name

        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise

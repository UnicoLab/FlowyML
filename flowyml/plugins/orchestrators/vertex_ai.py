"""Vertex AI Orchestrator - Native FlowyML Plugin.

This is a native FlowyML implementation for Google Cloud Vertex AI Pipelines,
without requiring any external framework dependencies.

Usage:
    from flowyml.plugins import get_plugin

    orchestrator = get_plugin("vertex_ai",
        project="my-gcp-project",
        location="us-central1"
    )

    # Run a pipeline
    orchestrator.run_pipeline(my_pipeline, run_id="run-001")
"""

import logging
from typing import Any

from flowyml.plugins.base import OrchestratorPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class VertexAIOrchestrator(OrchestratorPlugin):
    """Native Vertex AI Pipelines orchestrator for FlowyML.

    This orchestrator integrates directly with Vertex AI Pipelines
    without any intermediate framework.

    Args:
        project: GCP project ID.
        location: GCP region (e.g., "us-central1").
        staging_bucket: GCS bucket for staging artifacts.
        service_account: Service account email for pipeline execution.
        network: VPC network for pipeline execution.

    Example:
        orchestrator = VertexAIOrchestrator(
            project="my-gcp-project",
            location="us-central1",
            staging_bucket="gs://my-staging-bucket"
        )

        result = orchestrator.run_pipeline(
            pipeline=my_pipeline,
            run_id="training-run-001"
        )
    """

    METADATA = PluginMetadata(
        name="vertex_ai",
        description="Google Cloud Vertex AI Pipelines orchestration",
        plugin_type=PluginType.ORCHESTRATOR,
        version="1.0.0",
        author="FlowyML",
        packages=["google-cloud-aiplatform>=1.25", "kfp>=2.0"],
        documentation_url="https://cloud.google.com/vertex-ai/docs/pipelines",
        tags=["orchestrator", "gcp", "vertex-ai", "cloud"],
    )

    def __init__(
        self,
        project: str,
        location: str,
        staging_bucket: str = None,
        service_account: str = None,
        network: str = None,
        **kwargs,
    ):
        """Initialize the Vertex AI orchestrator."""
        super().__init__(
            name=kwargs.pop("name", "vertex_ai"),
            project=project,
            location=location,
            staging_bucket=staging_bucket,
            service_account=service_account,
            network=network,
            **kwargs,
        )

        self._project = project
        self._location = location
        self._staging_bucket = staging_bucket
        self._aiplatform = None

    def initialize(self) -> None:
        """Initialize Vertex AI connection."""
        try:
            from google.cloud import aiplatform

            aiplatform.init(
                project=self._project,
                location=self._location,
                staging_bucket=self._staging_bucket,
            )

            self._aiplatform = aiplatform
            self._is_initialized = True
            logger.info(f"Vertex AI orchestrator initialized: {self._project}/{self._location}")

        except ImportError:
            raise ImportError(
                "google-cloud-aiplatform is not installed. Run: flowyml plugin install vertex_ai",
            )

    def _ensure_initialized(self) -> None:
        """Ensure Vertex AI is initialized."""
        if not self._is_initialized:
            self.initialize()

    def run_pipeline(
        self,
        pipeline: Any,
        run_id: str,
        context: dict[str, Any] = None,
        parameters: dict[str, Any] = None,
        enable_caching: bool = True,
        **kwargs,
    ) -> Any:
        """Run a pipeline on Vertex AI.

        Args:
            pipeline: The pipeline to run. Can be:
                - A compiled KFP pipeline (JSON/YAML path)
                - A FlowyML pipeline object
            run_id: Unique identifier for this run.
            context: Optional context dictionary.
            parameters: Pipeline parameters.
            enable_caching: Whether to enable step caching.
            **kwargs: Additional Vertex AI-specific arguments.

        Returns:
            PipelineJob object.
        """
        self._ensure_initialized()

        # Handle different pipeline types
        if isinstance(pipeline, str):
            # Assume it's a path to compiled pipeline
            template_path = pipeline
        elif hasattr(pipeline, "to_vertex_pipeline"):
            # FlowyML pipeline with Vertex conversion
            template_path = pipeline.to_vertex_pipeline()
        elif callable(pipeline):
            # KFP pipeline function - compile it
            template_path = self._compile_kfp_pipeline(pipeline, run_id)
        else:
            raise ValueError(
                f"Unsupported pipeline type: {type(pipeline)}. "
                "Provide a path to compiled pipeline or a KFP pipeline function.",
            )

        # Create and run the pipeline job
        job = self._aiplatform.PipelineJob(
            display_name=run_id,
            template_path=template_path,
            pipeline_root=self._staging_bucket,
            parameter_values=parameters or {},
            enable_caching=enable_caching,
        )

        # Configure service account if provided
        service_account = self._config.get("service_account")
        network = self._config.get("network")

        job.run(
            service_account=service_account,
            network=network,
            sync=False,  # Run asynchronously
        )

        logger.info(f"Started Vertex AI pipeline job: {job.display_name}")
        logger.info(f"Job resource name: {job.resource_name}")

        return job

    def _compile_kfp_pipeline(self, pipeline_func: Any, run_id: str) -> str:
        """Compile a KFP pipeline function to a template.

        Args:
            pipeline_func: KFP pipeline function.
            run_id: Run ID for naming the compiled file.

        Returns:
            Path to compiled pipeline template.
        """
        try:
            from kfp import compiler
            import tempfile
            import os

            # Compile to a temporary file
            temp_dir = tempfile.mkdtemp()
            template_path = os.path.join(temp_dir, f"{run_id}_pipeline.yaml")

            compiler.Compiler().compile(
                pipeline_func=pipeline_func,
                package_path=template_path,
            )

            return template_path

        except ImportError:
            raise ImportError(
                "kfp is not installed. Run: flowyml plugin install vertex_ai",
            )

    def get_run_status(self, run_id: str) -> str:
        """Get the status of a pipeline run.

        Args:
            run_id: The run identifier (job resource name).

        Returns:
            Run status string.
        """
        self._ensure_initialized()

        try:
            job = self._aiplatform.PipelineJob.get(run_id)
            return job.state.name
        except Exception as e:
            logger.error(f"Failed to get run status: {e}")
            return "unknown"

    def cancel_run(self, run_id: str) -> bool:
        """Cancel a running pipeline.

        Args:
            run_id: The run identifier (job resource name).

        Returns:
            True if cancellation was successful.
        """
        self._ensure_initialized()

        try:
            job = self._aiplatform.PipelineJob.get(run_id)
            job.cancel()
            logger.info(f"Cancelled pipeline job: {run_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel run: {e}")
            return False

    def list_runs(self, pipeline_name: str = None, limit: int = 100) -> list[dict]:
        """List pipeline runs.

        Args:
            pipeline_name: Optional filter by pipeline name.
            limit: Maximum number of runs to return.

        Returns:
            List of run dictionaries.
        """
        self._ensure_initialized()

        try:
            filter_str = None
            if pipeline_name:
                filter_str = f'display_name="{pipeline_name}"'

            jobs = self._aiplatform.PipelineJob.list(
                filter=filter_str,
            )

            runs = []
            for job in jobs[:limit]:
                runs.append(
                    {
                        "run_id": job.resource_name,
                        "display_name": job.display_name,
                        "state": job.state.name,
                        "create_time": str(job.create_time),
                        "start_time": str(job.start_time) if job.start_time else None,
                        "end_time": str(job.end_time) if job.end_time else None,
                    },
                )

            return runs

        except Exception as e:
            logger.error(f"Failed to list runs: {e}")
            return []

    def wait_for_completion(self, job: Any, timeout: int = 3600) -> str:
        """Wait for a pipeline job to complete.

        Args:
            job: PipelineJob object from run_pipeline.
            timeout: Maximum wait time in seconds.

        Returns:
            Final job state.
        """
        self._ensure_initialized()

        job.wait()
        return job.state.name

    def run_with_routing(
        self,
        pipeline: Any,
        run_id: str,
        stack_name: str = None,
        context: dict[str, Any] = None,
        parameters: dict[str, Any] = None,
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
            context: Optional context dictionary.
            parameters: Pipeline parameters.
            **kwargs: Additional arguments.

        Returns:
            PipelineJob object with routing metadata.
        """
        self._ensure_initialized()

        # Get routing configuration
        routing_config = self._get_routing_config(stack_name)

        # Inject routing configuration into pipeline context
        enriched_context = context or {}
        enriched_context["__flowyml_routing__"] = {
            "run_id": run_id,
            "stack": stack_name or "default",
            "routing_rules": routing_config,
            "artifact_store": self._config.get("artifact_store_uri"),
            "model_registry": self._config.get("model_registry"),
            "experiment_tracker": self._config.get("experiment_tracker"),
        }

        # Add routing parameters to pipeline
        enriched_params = parameters or {}
        enriched_params["__run_id__"] = run_id

        # Run the pipeline
        job = self.run_pipeline(
            pipeline=pipeline,
            run_id=run_id,
            context=enriched_context,
            parameters=enriched_params,
            **kwargs,
        )

        logger.info(f"Started type-aware pipeline: {run_id}")
        logger.info(f"Routing config: stack={stack_name or 'active'}")

        return job

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
        machine_type: str = "n1-standard-4",
        min_replica_count: int = 1,
        max_replica_count: int = 1,
        accelerator_type: str = None,
        accelerator_count: int = 0,
    ) -> str:
        """Deploy a model to a Vertex AI endpoint.

        This method can be used after pipeline completion to deploy
        registered models to serving endpoints.

        Args:
            model_uri: URI to the model in Vertex AI Model Registry.
            endpoint_name: Name for the endpoint.
            machine_type: Compute machine type.
            min_replica_count: Minimum replicas.
            max_replica_count: Maximum replicas.
            accelerator_type: GPU type if needed.
            accelerator_count: Number of GPUs.

        Returns:
            Endpoint URI.
        """
        self._ensure_initialized()

        try:
            # Get or create endpoint
            endpoints = self._aiplatform.Endpoint.list(
                filter=f'display_name="{endpoint_name}"',
            )

            if endpoints:
                endpoint = endpoints[0]
                logger.info(f"Using existing endpoint: {endpoint_name}")
            else:
                endpoint = self._aiplatform.Endpoint.create(
                    display_name=endpoint_name,
                )
                logger.info(f"Created new endpoint: {endpoint_name}")

            # Get model
            model = self._aiplatform.Model(model_uri)

            # Deploy
            machine_config = {"machine_type": machine_type}
            if accelerator_type and accelerator_count > 0:
                machine_config["accelerator_type"] = accelerator_type
                machine_config["accelerator_count"] = accelerator_count

            model.deploy(
                endpoint=endpoint,
                deployed_model_display_name=f"{endpoint_name}-model",
                min_replica_count=min_replica_count,
                max_replica_count=max_replica_count,
                **machine_config,
            )

            endpoint_uri = endpoint.resource_name
            logger.info(f"Model deployed to endpoint: {endpoint_uri}")
            return endpoint_uri

        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise

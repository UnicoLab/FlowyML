"""Vertex AI Endpoint Deployer - Native FlowyML Plugin.

This plugin provides direct integration with Google Cloud Vertex AI
endpoints for model serving and inference.

Usage:
    from flowyml.plugins import get_plugin

    deployer = get_plugin("vertex_endpoint", project="my-project")
    endpoint = deployer.deploy(
        model_name="my-model",
        endpoint_name="my-endpoint",
        machine_type="n1-standard-4"
    )
"""

import logging

from flowyml.plugins.base import ModelDeployerPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class VertexEndpointDeployer(ModelDeployerPlugin):
    """Native Vertex AI Endpoint deployer for FlowyML.

    This plugin deploys models to Vertex AI Endpoints for real-time inference.

    Args:
        project: GCP project ID.
        location: GCP region (default: us-central1).
        staging_bucket: GCS bucket for staging artifacts.
    """

    metadata = PluginMetadata(
        name="vertex_endpoint",
        version="1.0.0",
        description="Google Cloud Vertex AI Endpoint Deployer",
        author="FlowyML Team",
        plugin_type=PluginType.CUSTOM,
    )

    def __init__(
        self,
        project: str,
        location: str = "us-central1",
        staging_bucket: str = None,
        **kwargs,
    ):
        """Initialize the Vertex Endpoint deployer.

        Args:
            project: GCP project ID.
            location: GCP region.
            staging_bucket: GCS bucket for artifacts.
            **kwargs: Additional plugin arguments.
        """
        super().__init__(**kwargs)
        self.project = project
        self.location = location
        self.staging_bucket = staging_bucket
        self._aiplatform = None
        self._initialized = False

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.CUSTOM

    def initialize(self) -> None:
        """Initialize connection to Vertex AI."""
        if self._initialized:
            return

        try:
            from google.cloud import aiplatform

            aiplatform.init(
                project=self.project,
                location=self.location,
                staging_bucket=self.staging_bucket,
            )
            self._aiplatform = aiplatform
            self._initialized = True
            logger.info(f"Vertex Endpoint Deployer initialized for project {self.project}")
        except ImportError:
            raise ImportError(
                "google-cloud-aiplatform is required. Install with: pip install google-cloud-aiplatform",
            )

    def _ensure_initialized(self) -> None:
        """Ensure Vertex AI is initialized."""
        if not self._initialized:
            self.initialize()

    def deploy(
        self,
        model_uri: str,
        endpoint_name: str,
        machine_type: str = "n1-standard-4",
        min_replica_count: int = 1,
        max_replica_count: int = 1,
        accelerator_type: str = None,
        accelerator_count: int = 0,
        service_account: str = None,
        **kwargs,
    ) -> str:
        """Deploy a model to a Vertex AI endpoint.

        Args:
            model_uri: Model resource name or GCS URI.
            endpoint_name: Name for the endpoint.
            machine_type: Machine type (e.g., n1-standard-4).
            min_replica_count: Minimum replicas.
            max_replica_count: Maximum replicas.
            accelerator_type: GPU type (NVIDIA_TESLA_T4, etc.).
            accelerator_count: Number of GPUs.
            service_account: Service account for endpoint.
            **kwargs: Additional deployment arguments.

        Returns:
            Endpoint resource name.
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
                logger.info(f"Created endpoint: {endpoint_name}")

            # Get the model
            if model_uri.startswith("projects/"):
                model = self._aiplatform.Model(model_name=model_uri)
            else:
                # Search by display name
                models = self._aiplatform.Model.list(
                    filter=f'display_name="{model_uri}"',
                    order_by="create_time desc",
                )
                if not models:
                    raise ValueError(f"Model '{model_uri}' not found")
                model = models[0]

            # Build deployment config
            deploy_config = {
                "machine_type": machine_type,
                "min_replica_count": min_replica_count,
                "max_replica_count": max_replica_count,
            }

            if accelerator_type and accelerator_count > 0:
                deploy_config["accelerator_type"] = accelerator_type
                deploy_config["accelerator_count"] = accelerator_count

            if service_account:
                deploy_config["service_account"] = service_account

            # Deploy model to endpoint
            model.deploy(endpoint=endpoint, **deploy_config)

            logger.info(f"Deployed model to endpoint: {endpoint.resource_name}")
            return endpoint.resource_name

        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise

    def undeploy(
        self,
        endpoint_name: str,
        deployed_model_id: str = None,
    ) -> bool:
        """Undeploy a model from an endpoint.

        Args:
            endpoint_name: Endpoint name or resource name.
            deployed_model_id: Specific deployed model ID (undeployes all if None).

        Returns:
            True if successful.
        """
        self._ensure_initialized()

        try:
            if endpoint_name.startswith("projects/"):
                endpoint = self._aiplatform.Endpoint(endpoint_name=endpoint_name)
            else:
                endpoints = self._aiplatform.Endpoint.list(
                    filter=f'display_name="{endpoint_name}"',
                )
                if not endpoints:
                    logger.warning(f"Endpoint '{endpoint_name}' not found")
                    return False
                endpoint = endpoints[0]

            if deployed_model_id:
                endpoint.undeploy(deployed_model_id=deployed_model_id)
            else:
                endpoint.undeploy_all()

            logger.info(f"Undeployed model(s) from endpoint: {endpoint_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to undeploy: {e}")
            return False

    def get_endpoint(
        self,
        endpoint_name: str,
    ) -> dict | None:
        """Get endpoint details.

        Args:
            endpoint_name: Endpoint name or resource name.

        Returns:
            Endpoint details dictionary.
        """
        self._ensure_initialized()

        try:
            if endpoint_name.startswith("projects/"):
                endpoint = self._aiplatform.Endpoint(endpoint_name=endpoint_name)
            else:
                endpoints = self._aiplatform.Endpoint.list(
                    filter=f'display_name="{endpoint_name}"',
                )
                if not endpoints:
                    return None
                endpoint = endpoints[0]

            return {
                "name": endpoint.display_name,
                "resource_name": endpoint.resource_name,
                "deployed_models": [
                    {
                        "id": dm.id,
                        "model": dm.model,
                    }
                    for dm in endpoint.deployed_models
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get endpoint: {e}")
            return None

    def predict(
        self,
        endpoint_name: str,
        instances: list[dict],
    ) -> list[dict]:
        """Make predictions using a deployed endpoint.

        Args:
            endpoint_name: Endpoint name or resource name.
            instances: List of input instances.

        Returns:
            List of predictions.
        """
        self._ensure_initialized()

        try:
            if endpoint_name.startswith("projects/"):
                endpoint = self._aiplatform.Endpoint(endpoint_name=endpoint_name)
            else:
                endpoints = self._aiplatform.Endpoint.list(
                    filter=f'display_name="{endpoint_name}"',
                )
                if not endpoints:
                    raise ValueError(f"Endpoint '{endpoint_name}' not found")
                endpoint = endpoints[0]

            response = endpoint.predict(instances=instances)
            return response.predictions

        except Exception as e:
            logger.error(f"Failed to predict: {e}")
            raise

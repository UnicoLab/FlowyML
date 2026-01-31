"""Vertex AI Model Registry - Native FlowyML Plugin.

This plugin provides direct integration with Google Cloud Vertex AI
Model Registry for model versioning, cataloging, and deployment.

Usage:
    from flowyml.plugins import get_plugin

    registry = get_plugin("vertex_model_registry", project="my-project")
    registry.register_model(
        name="my-model",
        model_uri="gs://bucket/model/",
        version="1.0.0",
        metadata={"framework": "tensorflow", "accuracy": 0.95}
    )

    # Deploy to endpoint
    endpoint = registry.deploy_model(
        model_name="my-model",
        endpoint_name="my-endpoint",
        machine_type="n1-standard-4"
    )
"""

import logging
from typing import Any
from datetime import datetime

from flowyml.plugins.base import ModelRegistryPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class VertexModelRegistry(ModelRegistryPlugin):
    """Native Vertex AI Model Registry plugin for FlowyML.

    This plugin integrates directly with Vertex AI Model Registry
    for registering, versioning, and deploying ML models.

    Args:
        project: GCP project ID.
        location: GCP region (default: us-central1).
        staging_bucket: GCS bucket for model staging.
    """

    metadata = PluginMetadata(
        name="vertex_model_registry",
        version="1.0.0",
        description="Google Cloud Vertex AI Model Registry",
        author="FlowyML Team",
        plugin_type=PluginType.CUSTOM,
    )

    def __init__(
        self,
        project: str,
        location: str = "us-central1",
        staging_bucket: str = None,
        labels: dict[str, str] = None,
        **kwargs,
    ):
        """Initialize the Vertex AI Model Registry plugin.

        Args:
            project: GCP project ID.
            location: GCP region.
            staging_bucket: GCS bucket for model artifacts.
            labels: Default labels to apply to models.
            **kwargs: Additional plugin arguments.
        """
        super().__init__(**kwargs)
        self.project = project
        self.location = location
        self.staging_bucket = staging_bucket
        self.labels = labels or {}
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
            logger.info(f"Vertex AI Model Registry initialized for project {self.project}")
        except ImportError:
            raise ImportError(
                "google-cloud-aiplatform is required. " "Install with: pip install google-cloud-aiplatform",
            )

    def _ensure_initialized(self) -> None:
        """Ensure Vertex AI is initialized."""
        if not self._initialized:
            self.initialize()

    def register_model(
        self,
        name: str,
        model_uri: str,
        version: str = None,
        metadata: dict = None,
        serving_container_image_uri: str = None,
        description: str = None,
        labels: dict[str, str] = None,
        **kwargs,
    ) -> str:
        """Register a model in Vertex AI Model Registry.

        Args:
            name: Display name for the model.
            model_uri: GCS URI to model artifacts.
            version: Model version string.
            metadata: Model metadata dictionary.
            serving_container_image_uri: Docker image for serving.
            description: Model description.
            labels: Labels to attach to the model.
            **kwargs: Additional registration arguments.

        Returns:
            Model resource name.
        """
        self._ensure_initialized()

        try:
            all_labels = {**self.labels, **(labels or {})}
            if version:
                all_labels["version"] = version

            # Determine serving container if not provided
            if not serving_container_image_uri:
                # Auto-detect based on metadata
                framework = (metadata or {}).get("framework", "").lower()
                if framework == "tensorflow":
                    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/prediction/" "tf2-cpu.2-13:latest"
                elif framework == "pytorch":
                    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/prediction/" "pytorch-cpu.2-0:latest"
                elif framework == "sklearn" or framework == "scikit-learn":
                    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/prediction/" "sklearn-cpu.1-3:latest"
                elif framework == "xgboost":
                    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/prediction/" "xgboost-cpu.1-7:latest"
                else:
                    # Default to custom container
                    serving_container_image_uri = "us-docker.pkg.dev/vertex-ai/prediction/" "sklearn-cpu.1-3:latest"

            model = self._aiplatform.Model.upload(
                display_name=name,
                artifact_uri=model_uri,
                serving_container_image_uri=serving_container_image_uri,
                description=description or f"Model registered via FlowyML at {datetime.now().isoformat()}",
                labels=all_labels,
            )

            logger.info(f"Registered model '{name}' with resource: {model.resource_name}")
            return model.resource_name

        except Exception as e:
            logger.error(f"Failed to register model '{name}': {e}")
            raise

    def get_model(
        self,
        name: str,
        version: str = None,
    ) -> Any:
        """Get a model from the registry.

        Args:
            name: Model display name or resource name.
            version: Specific version to retrieve.

        Returns:
            Model object from Vertex AI.
        """
        self._ensure_initialized()

        try:
            # If it's a resource name, get directly
            if name.startswith("projects/"):
                return self._aiplatform.Model(model_name=name)

            # Otherwise, search by display name
            models = self._aiplatform.Model.list(
                filter=f'display_name="{name}"',
                order_by="create_time desc",
            )

            if not models:
                logger.warning(f"Model '{name}' not found")
                return None

            if version:
                # Find specific version
                for model in models:
                    if model.labels.get("version") == version:
                        return model
                logger.warning(f"Model '{name}' version '{version}' not found")
                return None

            # Return latest
            return models[0]

        except Exception as e:
            logger.error(f"Failed to get model '{name}': {e}")
            raise

    def list_models(
        self,
        filter_expr: str = None,
        limit: int = 100,
    ) -> list[dict]:
        """List models in the registry.

        Args:
            filter_expr: Filter expression for listing.
            limit: Maximum number of models to return.

        Returns:
            List of model dictionaries.
        """
        self._ensure_initialized()

        try:
            models = self._aiplatform.Model.list(
                filter=filter_expr,
                order_by="create_time desc",
            )

            result = []
            for model in models[:limit]:
                result.append(
                    {
                        "name": model.display_name,
                        "resource_name": model.resource_name,
                        "created": str(model.create_time),
                        "labels": model.labels,
                        "description": model.description,
                    },
                )

            return result

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise

    def transition_model_stage(
        self,
        name: str,
        stage: str,
        version: str = None,
    ) -> bool:
        """Transition model to a stage (via labels).

        Args:
            name: Model name.
            stage: Target stage (e.g., "staging", "production").
            version: Specific version.

        Returns:
            True if successful.
        """
        self._ensure_initialized()

        try:
            model = self.get_model(name, version)
            if not model:
                return False

            # Update labels to reflect stage
            labels = dict(model.labels)
            labels["stage"] = stage
            model.update(labels=labels)

            logger.info(f"Transitioned model '{name}' to stage '{stage}'")
            return True

        except Exception as e:
            logger.error(f"Failed to transition model: {e}")
            return False

    def deploy_model(
        self,
        model_name: str,
        endpoint_name: str,
        machine_type: str = "n1-standard-4",
        min_replica_count: int = 1,
        max_replica_count: int = 1,
        **kwargs,
    ) -> str:
        """Deploy a model to a Vertex AI endpoint.

        Args:
            model_name: Model display name or resource name.
            endpoint_name: Name for the endpoint.
            machine_type: Machine type for deployment.
            min_replica_count: Minimum replicas.
            max_replica_count: Maximum replicas.
            **kwargs: Additional deployment arguments.

        Returns:
            Endpoint resource name.
        """
        self._ensure_initialized()

        try:
            # Get the model
            model = self.get_model(model_name)
            if not model:
                raise ValueError(f"Model '{model_name}' not found")

            # Create or get endpoint
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

            # Deploy model to endpoint
            model.deploy(
                endpoint=endpoint,
                machine_type=machine_type,
                min_replica_count=min_replica_count,
                max_replica_count=max_replica_count,
                **kwargs,
            )

            logger.info(f"Deployed model '{model_name}' to endpoint '{endpoint_name}'")
            return endpoint.resource_name

        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise

    def predict(
        self,
        endpoint_name: str,
        instances: list[dict],
    ) -> list[dict]:
        """Make predictions using a deployed model.

        Args:
            endpoint_name: Endpoint display name or resource name.
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

            predictions = endpoint.predict(instances=instances)
            return predictions.predictions

        except Exception as e:
            logger.error(f"Failed to make prediction: {e}")
            raise

"""SageMaker Model Registry - Native FlowyML Plugin.

This plugin provides direct integration with AWS SageMaker Model Registry
for model versioning, cataloging, and deployment.

Usage:
    from flowyml.plugins import get_plugin

    registry = get_plugin("sagemaker_model_registry", region="us-east-1")
    registry.register_model(
        name="my-model",
        model_uri="s3://bucket/model/",
        version="1.0.0",
        metadata={"framework": "pytorch", "accuracy": 0.95}
    )

    # Deploy to endpoint
    endpoint = registry.deploy_model(
        model_name="my-model",
        endpoint_name="my-endpoint",
        instance_type="ml.m5.large"
    )
"""

import logging
from typing import Any
from datetime import datetime

from flowyml.plugins.base import ModelRegistryPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class SageMakerModelRegistry(ModelRegistryPlugin):
    """Native SageMaker Model Registry plugin for FlowyML.

    This plugin integrates directly with SageMaker Model Registry
    for registering, versioning, and deploying ML models.

    Args:
        region: AWS region.
        role_arn: IAM role ARN for SageMaker.
        model_package_group_arn: Optional model package group ARN.
    """

    metadata = PluginMetadata(
        name="sagemaker_model_registry",
        version="1.0.0",
        description="AWS SageMaker Model Registry",
        author="FlowyML Team",
        plugin_type=PluginType.CUSTOM,
    )

    def __init__(
        self,
        region: str = None,
        role_arn: str = None,
        model_package_group_name: str = "flowyml-models",
        **kwargs,
    ):
        """Initialize the SageMaker Model Registry plugin.

        Args:
            region: AWS region (uses default if not specified).
            role_arn: IAM role ARN for SageMaker operations.
            model_package_group_name: Model package group for organizing models.
            **kwargs: Additional plugin arguments.
        """
        super().__init__(**kwargs)
        self.region = region
        self.role_arn = role_arn
        self.model_package_group_name = model_package_group_name
        self._sagemaker = None
        self._boto_session = None
        self._initialized = False

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.CUSTOM

    def initialize(self) -> None:
        """Initialize connection to SageMaker."""
        if self._initialized:
            return

        try:
            import boto3
            import sagemaker

            self._boto_session = boto3.Session(region_name=self.region)
            self._sm_client = self._boto_session.client("sagemaker")
            self._sagemaker = sagemaker

            # Ensure model package group exists
            self._ensure_model_package_group()

            self._initialized = True
            logger.info(f"SageMaker Model Registry initialized in region {self.region}")
        except ImportError:
            raise ImportError(
                "boto3 and sagemaker are required. Install with: pip install boto3 sagemaker",
            )

    def _ensure_initialized(self) -> None:
        """Ensure SageMaker is initialized."""
        if not self._initialized:
            self.initialize()

    def _ensure_model_package_group(self) -> None:
        """Ensure the model package group exists."""
        try:
            self._sm_client.describe_model_package_group(
                ModelPackageGroupName=self.model_package_group_name,
            )
        except self._sm_client.exceptions.ResourceNotFoundException:
            self._sm_client.create_model_package_group(
                ModelPackageGroupName=self.model_package_group_name,
                ModelPackageGroupDescription="FlowyML Model Registry",
            )
            logger.info(f"Created model package group: {self.model_package_group_name}")

    def register_model(
        self,
        name: str,
        model_uri: str,
        version: str = None,
        metadata: dict = None,
        inference_image_uri: str = None,
        content_types: list[str] = None,
        response_types: list[str] = None,
        description: str = None,
        **kwargs,
    ) -> str:
        """Register a model in SageMaker Model Registry.

        Args:
            name: Model name.
            model_uri: S3 URI to model artifacts.
            version: Model version string.
            metadata: Model metadata dictionary.
            inference_image_uri: Docker image for inference.
            content_types: Supported input content types.
            response_types: Supported output content types.
            description: Model description.
            **kwargs: Additional registration arguments.

        Returns:
            Model package ARN.
        """
        self._ensure_initialized()

        try:
            metadata = metadata or {}
            content_types = content_types or ["application/json"]
            response_types = response_types or ["application/json"]

            # Determine inference image if not provided
            if not inference_image_uri:
                framework = metadata.get("framework", "").lower()
                region = self.region or self._boto_session.region_name

                # Use SageMaker pre-built images
                account_map = {
                    "us-east-1": "763104351884",
                    "us-west-2": "763104351884",
                    "eu-west-1": "763104351884",
                    # Add more regions as needed
                }
                account = account_map.get(region, "763104351884")

                if framework == "pytorch":
                    inference_image_uri = f"{account}.dkr.ecr.{region}.amazonaws.com/pytorch-inference:2.0.0-cpu-py310"
                elif framework == "tensorflow":
                    inference_image_uri = f"{account}.dkr.ecr.{region}.amazonaws.com/tensorflow-inference:2.13-cpu"
                elif framework == "sklearn" or framework == "scikit-learn":
                    inference_image_uri = (
                        f"{account}.dkr.ecr.{region}.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py310"
                    )
                elif framework == "xgboost":
                    inference_image_uri = f"{account}.dkr.ecr.{region}.amazonaws.com/sagemaker-xgboost:1.7-1-cpu-py310"
                else:
                    # Default to sklearn
                    inference_image_uri = (
                        f"{account}.dkr.ecr.{region}.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py310"
                    )

            # Build model package spec
            model_spec = {
                "ModelPackageGroupName": self.model_package_group_name,
                "ModelPackageDescription": description or f"{name} registered via FlowyML",
                "InferenceSpecification": {
                    "Containers": [
                        {
                            "Image": inference_image_uri,
                            "ModelDataUrl": model_uri,
                        },
                    ],
                    "SupportedContentTypes": content_types,
                    "SupportedResponseMIMETypes": response_types,
                    "SupportedTransformInstanceTypes": ["ml.m5.large"],
                    "SupportedRealtimeInferenceInstanceTypes": ["ml.m5.large"],
                },
                "ModelApprovalStatus": "PendingManualApproval",
                "CustomerMetadataProperties": {
                    "name": name,
                    "version": version or "1.0.0",
                    "registered_at": datetime.now().isoformat(),
                    **{k: str(v) for k, v in metadata.items()},
                },
            }

            response = self._sm_client.create_model_package(**model_spec)
            model_package_arn = response["ModelPackageArn"]

            logger.info(f"Registered model '{name}' with ARN: {model_package_arn}")
            return model_package_arn

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
            name: Model name or package ARN.
            version: Specific version to retrieve.

        Returns:
            Model package details.
        """
        self._ensure_initialized()

        try:
            # If it's an ARN, get directly
            if name.startswith("arn:"):
                return self._sm_client.describe_model_package(
                    ModelPackageName=name,
                )

            # Otherwise, list and filter by name
            packages = self._sm_client.list_model_packages(
                ModelPackageGroupName=self.model_package_group_name,
                SortBy="CreationTime",
                SortOrder="Descending",
            )["ModelPackageSummaryList"]

            for pkg in packages:
                details = self._sm_client.describe_model_package(
                    ModelPackageName=pkg["ModelPackageArn"],
                )
                customer_meta = details.get("CustomerMetadataProperties", {})

                if customer_meta.get("name") == name:
                    if version and customer_meta.get("version") != version:
                        continue
                    return details

            logger.warning(f"Model '{name}' not found")
            return None

        except Exception as e:
            logger.error(f"Failed to get model '{name}': {e}")
            raise

    def list_models(
        self,
        limit: int = 100,
    ) -> list[dict]:
        """List models in the registry.

        Args:
            limit: Maximum number of models to return.

        Returns:
            List of model dictionaries.
        """
        self._ensure_initialized()

        try:
            packages = self._sm_client.list_model_packages(
                ModelPackageGroupName=self.model_package_group_name,
                MaxResults=min(limit, 100),
                SortBy="CreationTime",
                SortOrder="Descending",
            )["ModelPackageSummaryList"]

            result = []
            for pkg in packages:
                details = self._sm_client.describe_model_package(
                    ModelPackageName=pkg["ModelPackageArn"],
                )
                customer_meta = details.get("CustomerMetadataProperties", {})

                result.append(
                    {
                        "name": customer_meta.get("name", "unknown"),
                        "version": customer_meta.get("version", "1.0.0"),
                        "arn": pkg["ModelPackageArn"],
                        "status": details.get("ModelApprovalStatus", "Unknown"),
                        "created": str(pkg.get("CreationTime", "")),
                        "metadata": customer_meta,
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
        """Transition model approval status.

        Args:
            name: Model name.
            stage: Target stage ("Approved", "Rejected", "PendingManualApproval").
            version: Specific version.

        Returns:
            True if successful.
        """
        self._ensure_initialized()

        # Map friendly stage names to SageMaker statuses
        stage_map = {
            "production": "Approved",
            "staging": "Approved",
            "approved": "Approved",
            "rejected": "Rejected",
            "pending": "PendingManualApproval",
        }
        approval_status = stage_map.get(stage.lower(), stage)

        try:
            model = self.get_model(name, version)
            if not model:
                return False

            self._sm_client.update_model_package(
                ModelPackageArn=model["ModelPackageArn"],
                ModelApprovalStatus=approval_status,
            )

            logger.info(f"Transitioned model '{name}' to status '{approval_status}'")
            return True

        except Exception as e:
            logger.error(f"Failed to transition model: {e}")
            return False

    def deploy_model(
        self,
        model_name: str,
        endpoint_name: str,
        instance_type: str = "ml.m5.large",
        instance_count: int = 1,
        **kwargs,
    ) -> str:
        """Deploy a model to a SageMaker endpoint.

        Args:
            model_name: Model name or package ARN.
            endpoint_name: Name for the endpoint.
            instance_type: Instance type for deployment.
            instance_count: Number of instances.
            **kwargs: Additional deployment arguments.

        Returns:
            Endpoint ARN.
        """
        self._ensure_initialized()

        try:
            # Get model package
            model = self.get_model(model_name)
            if not model:
                raise ValueError(f"Model '{model_name}' not found")

            model_package_arn = model["ModelPackageArn"]

            # Create model from package
            sm_model_name = f"{endpoint_name}-model"

            try:
                self._sm_client.create_model(
                    ModelName=sm_model_name,
                    PrimaryContainer={
                        "ModelPackageName": model_package_arn,
                    },
                    ExecutionRoleArn=self.role_arn,
                )
            except self._sm_client.exceptions.ResourceInUse:
                logger.info(f"Model {sm_model_name} already exists")

            # Create endpoint config
            config_name = f"{endpoint_name}-config"

            try:
                self._sm_client.create_endpoint_config(
                    EndpointConfigName=config_name,
                    ProductionVariants=[
                        {
                            "VariantName": "primary",
                            "ModelName": sm_model_name,
                            "InstanceType": instance_type,
                            "InitialInstanceCount": instance_count,
                        },
                    ],
                )
            except self._sm_client.exceptions.ResourceInUse:
                logger.info(f"Endpoint config {config_name} already exists")

            # Create or update endpoint
            try:
                self._sm_client.create_endpoint(
                    EndpointName=endpoint_name,
                    EndpointConfigName=config_name,
                )
                logger.info(f"Creating endpoint: {endpoint_name}")
            except self._sm_client.exceptions.ResourceInUse:
                self._sm_client.update_endpoint(
                    EndpointName=endpoint_name,
                    EndpointConfigName=config_name,
                )
                logger.info(f"Updating endpoint: {endpoint_name}")

            # Get endpoint ARN
            endpoint_desc = self._sm_client.describe_endpoint(
                EndpointName=endpoint_name,
            )

            logger.info(f"Deployed model '{model_name}' to endpoint '{endpoint_name}'")
            return endpoint_desc["EndpointArn"]

        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise

    def predict(
        self,
        endpoint_name: str,
        data: Any,
        content_type: str = "application/json",
    ) -> Any:
        """Make predictions using a deployed model.

        Args:
            endpoint_name: Endpoint name.
            data: Input data (will be JSON serialized).
            content_type: Content type of the request.

        Returns:
            Prediction result.
        """
        self._ensure_initialized()

        try:
            import json

            runtime_client = self._boto_session.client("sagemaker-runtime")

            body = json.dumps(data) if isinstance(data, (dict, list)) else str(data)

            response = runtime_client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType=content_type,
                Body=body.encode("utf-8"),
            )

            result = json.loads(response["Body"].read().decode("utf-8"))
            return result

        except Exception as e:
            logger.error(f"Failed to make prediction: {e}")
            raise

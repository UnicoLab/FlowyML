"""SageMaker Endpoint Deployer - Native FlowyML Plugin.

This plugin provides direct integration with AWS SageMaker
endpoints for model serving and inference.

Usage:
    from flowyml.plugins import get_plugin

    deployer = get_plugin("sagemaker_endpoint", region="us-east-1")
    endpoint = deployer.deploy(
        model_name="my-model",
        endpoint_name="my-endpoint",
        instance_type="ml.m5.large"
    )
"""

from __future__ import annotations

import logging
from typing import Any
import time

from flowyml.plugins.base import ModelDeployerPlugin, PluginMetadata, PluginType
from flowyml.stacks.plugins import register_component

logger = logging.getLogger(__name__)


@register_component(name="sagemaker_endpoint")
class SageMakerEndpointDeployer(ModelDeployerPlugin):
    """Native SageMaker Endpoint deployer for FlowyML.

    This plugin deploys models to SageMaker Endpoints for real-time inference.

    Args:
        region: AWS region.
        role_arn: IAM role ARN for SageMaker.
    """

    metadata = PluginMetadata(
        name="sagemaker_endpoint",
        version="1.0.0",
        description="AWS SageMaker Endpoint Deployer",
        author="FlowyML Team",
        plugin_type=PluginType.CUSTOM,
    )

    def __init__(
        self,
        region: str = None,
        role_arn: str = None,
        **kwargs,
    ):
        """Initialize the SageMaker Endpoint deployer.

        Args:
            region: AWS region (uses default if not specified).
            role_arn: IAM role ARN for SageMaker operations.
            **kwargs: Additional plugin arguments.
        """
        super().__init__(**kwargs)
        self.region = region
        self.role_arn = role_arn
        self._boto_session = None
        self._sm_client = None
        self._runtime_client = None
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

            self._boto_session = boto3.Session(region_name=self.region)
            self._sm_client = self._boto_session.client("sagemaker")
            self._runtime_client = self._boto_session.client("sagemaker-runtime")

            self._initialized = True
            logger.info(f"SageMaker Endpoint Deployer initialized in region {self.region}")
        except ImportError:
            raise ImportError(
                "boto3 is required. Install with: pip install boto3",
            )

    def _ensure_initialized(self) -> None:
        """Ensure SageMaker is initialized."""
        if not self._initialized:
            self.initialize()

    def deploy(
        self,
        model_uri: str,
        endpoint_name: str,
        instance_type: str = "ml.m5.large",
        instance_count: int = 1,
        inference_image_uri: str = None,
        wait: bool = False,
        **kwargs,
    ) -> str:
        """Deploy a model to a SageMaker endpoint.

        Args:
            model_uri: S3 URI to model artifacts or model package ARN.
            endpoint_name: Name for the endpoint.
            instance_type: Instance type (e.g., ml.m5.large).
            instance_count: Number of instances.
            inference_image_uri: Docker image for inference.
            wait: Whether to wait for deployment to complete.
            **kwargs: Additional deployment arguments.

        Returns:
            Endpoint ARN.
        """
        self._ensure_initialized()

        try:
            model_name = f"{endpoint_name}-model"
            config_name = f"{endpoint_name}-config"

            # Create model (if model_uri is S3 path, need image)
            if model_uri.startswith("s3://"):
                if not inference_image_uri:
                    raise ValueError("inference_image_uri required for S3 model")

                try:
                    self._sm_client.create_model(
                        ModelName=model_name,
                        PrimaryContainer={
                            "Image": inference_image_uri,
                            "ModelDataUrl": model_uri,
                        },
                        ExecutionRoleArn=self.role_arn,
                    )
                except self._sm_client.exceptions.ResourceInUse:
                    logger.info(f"Model {model_name} already exists")
            elif model_uri.startswith("arn:"):
                # Model package ARN
                try:
                    self._sm_client.create_model(
                        ModelName=model_name,
                        PrimaryContainer={
                            "ModelPackageName": model_uri,
                        },
                        ExecutionRoleArn=self.role_arn,
                    )
                except self._sm_client.exceptions.ResourceInUse:
                    logger.info(f"Model {model_name} already exists")
            else:
                raise ValueError(f"Invalid model_uri format: {model_uri}")

            # Create endpoint config
            try:
                self._sm_client.create_endpoint_config(
                    EndpointConfigName=config_name,
                    ProductionVariants=[
                        {
                            "VariantName": "primary",
                            "ModelName": model_name,
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

            if wait:
                self._wait_for_endpoint(endpoint_name)

            # Get endpoint ARN
            endpoint_desc = self._sm_client.describe_endpoint(
                EndpointName=endpoint_name,
            )

            logger.info(f"Deployed to endpoint: {endpoint_name}")
            return endpoint_desc["EndpointArn"]

        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise

    def _wait_for_endpoint(self, endpoint_name: str, timeout: int = 600) -> None:
        """Wait for endpoint to be in service."""
        start = time.time()
        while time.time() - start < timeout:
            desc = self._sm_client.describe_endpoint(EndpointName=endpoint_name)
            status = desc["EndpointStatus"]

            if status == "InService":
                logger.info(f"Endpoint {endpoint_name} is InService")
                return
            elif status == "Failed":
                raise RuntimeError(f"Endpoint deployment failed: {desc.get('FailureReason')}")

            logger.debug(f"Waiting for endpoint, status: {status}")
            time.sleep(30)

        raise TimeoutError(f"Endpoint deployment timed out after {timeout}s")

    def undeploy(
        self,
        endpoint_name: str,
    ) -> bool:
        """Delete an endpoint.

        Args:
            endpoint_name: Endpoint name.

        Returns:
            True if successful.
        """
        self._ensure_initialized()

        try:
            self._sm_client.delete_endpoint(EndpointName=endpoint_name)
            logger.info(f"Deleted endpoint: {endpoint_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete endpoint: {e}")
            return False

    def get_endpoint(
        self,
        endpoint_name: str,
    ) -> dict | None:
        """Get endpoint details.

        Args:
            endpoint_name: Endpoint name.

        Returns:
            Endpoint details dictionary.
        """
        self._ensure_initialized()

        try:
            desc = self._sm_client.describe_endpoint(EndpointName=endpoint_name)

            return {
                "name": endpoint_name,
                "arn": desc["EndpointArn"],
                "status": desc["EndpointStatus"],
                "config_name": desc["EndpointConfigName"],
                "created": str(desc.get("CreationTime", "")),
                "last_modified": str(desc.get("LastModifiedTime", "")),
            }

        except self._sm_client.exceptions.ResourceNotFoundException:
            return None
        except Exception as e:
            logger.error(f"Failed to get endpoint: {e}")
            return None

    def predict(
        self,
        endpoint_name: str,
        data: Any,
        content_type: str = "application/json",
    ) -> Any:
        """Make predictions using a deployed endpoint.

        Args:
            endpoint_name: Endpoint name.
            data: Input data (will be JSON serialized if dict/list).
            content_type: Content type of the request.

        Returns:
            Prediction result.
        """
        self._ensure_initialized()

        try:
            import json

            body = json.dumps(data) if isinstance(data, (dict, list)) else str(data)

            response = self._runtime_client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType=content_type,
                Body=body.encode("utf-8"),
            )

            result = json.loads(response["Body"].read().decode("utf-8"))
            return result

        except Exception as e:
            logger.error(f"Failed to predict: {e}")
            raise

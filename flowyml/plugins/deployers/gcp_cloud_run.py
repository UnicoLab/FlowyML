"""GCP Cloud Run Deployer - Native FlowyML Plugin.

This plugin provides direct integration with Google Cloud Run
for serverless model serving.
"""

import logging
import subprocess
import json
from typing import Any
from flowyml.utils.observability import trace_execution

from flowyml.plugins.base import ModelDeployerPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


# import removed from here


class GCPCloudRunDeployer(ModelDeployerPlugin):
    """Native GCP Cloud Run deployer for FlowyML.

    This plugin deploys containerized models to Cloud Run.

    Args:
        project_id: GCP project ID.
        region: GCP region (default: us-central1).
    """

    metadata = PluginMetadata(
        name="gcp_cloud_run",
        version="1.0.0",
        description="Google Cloud Run Deployer",
        author="FlowyML Team",
        plugin_type=PluginType.MODEL_DEPLOYER,
    )

    def __init__(
        self,
        project_id: str,
        region: str = "us-central1",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.project_id = project_id
        self.region = region

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.MODEL_DEPLOYER

    def initialize(self) -> None:
        """Verify gcloud is installed."""
        try:
            subprocess.run(["gcloud", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ImportError(
                "gcloud CLI is required for GCP Cloud Run deployment. Please install the Google Cloud SDK.",
            )

    @trace_execution(operation_name="cloud_run_deploy")
    def deploy(
        self,
        model_uri: str,
        endpoint_name: str,
        image: str = None,
        memory: str = "512Mi",
        cpu: str = "1",
        min_instances: int = 0,
        max_instances: int = 10,
        allow_unauthenticated: bool = True,
        env_vars: dict[str, str] = None,
        **kwargs,
    ) -> str:
        """Deploy a container to Cloud Run.

        Args:
            model_uri: Not used directly for Cloud Run (uses image), but kept for interface compatibility.
            endpoint_name: Name of the Cloud Run service.
            image: Docker image to deploy (required).
            memory: Memory limit (e.g., 512Mi, 2Gi).
            cpu: CPU limit.
            min_instances: Minimum number of instances.
            max_instances: Maximum number of instances.
            allow_unauthenticated: Allow public access.
            env_vars: Environment variables.
            **kwargs: Additional arguments.

        Returns:
            Service URL.
        """
        if not image:
            raise ValueError("Docker image is required for Cloud Run deployment.")

        command = [
            "gcloud",
            "run",
            "deploy",
            endpoint_name,
            f"--image={image}",
            f"--region={self.region}",
            f"--project={self.project_id}",
            f"--memory={memory}",
            f"--cpu={cpu}",
            f"--min-instances={min_instances}",
            f"--max-instances={max_instances}",
            "--platform=managed",
        ]

        if allow_unauthenticated:
            command.append("--allow-unauthenticated")
        else:
            command.append("--no-allow-unauthenticated")

        if env_vars:
            env_list = [f"{k}={v}" for k, v in env_vars.items()]
            command.append(f"--set-env-vars={','.join(env_list)}")

        if model_uri:
            # Pass model URI as environment variable if provided
            command.append(f"--set-env-vars=MODEL_URI={model_uri}")

        try:
            logger.info(f"Deploying Cloud Run service: {endpoint_name}...")
            subprocess.run(command, check=True)

            # Get service URL
            url_cmd = [
                "gcloud",
                "run",
                "services",
                "describe",
                endpoint_name,
                f"--region={self.region}",
                f"--project={self.project_id}",
                "--format=value(status.url)",
            ]
            result = subprocess.run(url_cmd, check=True, capture_output=True, text=True)
            url = result.stdout.strip()

            logger.info(f"Deployed successfully to: {url}")
            return url

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to deploy to Cloud Run: {e}")
            raise

    def get_endpoint(self, endpoint_name: str) -> dict | None:
        """Get Cloud Run service details."""
        try:
            cmd = [
                "gcloud",
                "run",
                "services",
                "describe",
                endpoint_name,
                f"--region={self.region}",
                f"--project={self.project_id}",
                "--format=json",
            ]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError:
            return None

    @trace_execution(operation_name="cloud_run_undeploy")
    def undeploy(self, endpoint_name: str) -> bool:
        """Delete Cloud Run service."""
        try:
            cmd = [
                "gcloud",
                "run",
                "services",
                "delete",
                endpoint_name,
                f"--region={self.region}",
                f"--project={self.project_id}",
                "--quiet",
            ]
            subprocess.run(cmd, check=True)
            logger.info(f"Deleted Cloud Run service: {endpoint_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete service: {e}")
            return False

    @trace_execution(operation_name="cloud_run_predict")
    def predict(self, endpoint: str, data: Any) -> Any:
        """Make prediction (helper using curl/requests if desired, but usually done via HTTP client)."""
        # Simple implementation using requests if available, or just printing instructions
        import requests

        if isinstance(data, (dict, list)):
            resp = requests.post(endpoint, json=data)
        else:
            resp = requests.post(endpoint, data=data)

        resp.raise_for_status()
        return resp.json()

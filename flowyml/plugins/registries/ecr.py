"""AWS ECR Container Registry - Native FlowyML Plugin.

This is a native FlowyML implementation for AWS Elastic Container Registry,
without requiring any external framework dependencies.

Usage:
    from flowyml.plugins import get_plugin

    registry = get_plugin("ecr",
        repository="my-ml-images",
        region="us-east-1"
    )

    # Push an image
    uri = registry.push_image("ml-training", tag="v1.0")
"""

import subprocess
import logging

from flowyml.plugins.base import ContainerRegistryPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class ECRRegistry(ContainerRegistryPlugin):
    """Native AWS ECR container registry for FlowyML.

    This registry integrates directly with AWS ECR without any
    intermediate framework.

    Args:
        repository: ECR repository name.
        region: AWS region.
        account_id: AWS account ID (auto-detected if not provided).
        access_key: AWS access key (uses environment/credentials if not provided).
        secret_key: AWS secret key (uses environment/credentials if not provided).

    Example:
        registry = ECRRegistry(
            repository="ml-images",
            region="us-east-1"
        )

        uri = registry.push_image("classifier", tag="v1.0")
    """

    METADATA = PluginMetadata(
        name="ecr",
        description="AWS Elastic Container Registry",
        plugin_type=PluginType.CONTAINER_REGISTRY,
        version="1.0.0",
        author="FlowyML",
        packages=["boto3>=1.28"],
        documentation_url="https://docs.aws.amazon.com/ecr/",
        tags=["container-registry", "aws", "cloud"],
    )

    def __init__(
        self,
        repository: str,
        region: str = None,
        account_id: str = None,
        access_key: str = None,
        secret_key: str = None,
        **kwargs,
    ):
        """Initialize the ECR registry."""
        super().__init__(
            name=kwargs.pop("name", "ecr"),
            repository=repository,
            region=region,
            account_id=account_id,
            access_key=access_key,
            secret_key=secret_key,
            **kwargs,
        )

        self._repository = repository
        self._region = region
        self._account_id = account_id
        self._ecr_client = None

    def initialize(self) -> None:
        """Initialize ECR connection."""
        try:
            import boto3

            # Build client kwargs
            client_kwargs = {}

            if self._region:
                client_kwargs["region_name"] = self._region

            if self._config.get("access_key") and self._config.get("secret_key"):
                client_kwargs["aws_access_key_id"] = self._config["access_key"]
                client_kwargs["aws_secret_access_key"] = self._config["secret_key"]

            self._ecr_client = boto3.client("ecr", **client_kwargs)

            # Auto-detect account ID if not provided
            if not self._account_id:
                sts = boto3.client("sts", **client_kwargs)
                self._account_id = sts.get_caller_identity()["Account"]

            # Get Docker login credentials
            self._authenticate_docker()

            self._is_initialized = True
            logger.info(f"ECR registry initialized: {self.registry_uri}")

        except ImportError:
            raise ImportError(
                "boto3 is not installed. Run: flowyml plugin install ecr",
            )

    def _authenticate_docker(self) -> None:
        """Authenticate Docker with ECR."""
        try:
            # Get authorization token
            response = self._ecr_client.get_authorization_token()
            auth_data = response["authorizationData"][0]

            # Decode credentials
            import base64

            token = base64.b64decode(auth_data["authorizationToken"]).decode()
            username, password = token.split(":")
            registry_url = auth_data["proxyEndpoint"]

            # Login to Docker
            result = subprocess.run(
                ["docker", "login", "--username", username, "--password-stdin", registry_url],
                input=password.encode(),
                capture_output=True,
            )

            if result.returncode != 0:
                logger.warning(f"Docker login may have failed: {result.stderr.decode()}")
            else:
                logger.debug("Docker authenticated with ECR")

        except Exception as e:
            logger.warning(f"Failed to authenticate Docker with ECR: {e}")

    def _ensure_initialized(self) -> None:
        """Ensure the registry is initialized."""
        if not self._is_initialized:
            self.initialize()

    @property
    def registry_uri(self) -> str:
        """Get the base registry URI."""
        return f"{self._account_id}.dkr.ecr.{self._region}.amazonaws.com/{self._repository}"

    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        """Get the full URI for an image.

        Args:
            image_name: Name of the image.
            tag: Image tag.

        Returns:
            Full image URI.
        """
        return f"{self._account_id}.dkr.ecr.{self._region}.amazonaws.com/{self._repository}/{image_name}:{tag}"

    def push_image(self, image_name: str, tag: str = "latest", local_image: str = None) -> str:
        """Push an image to ECR.

        Args:
            image_name: Name for the image in the registry.
            tag: Image tag.
            local_image: Local image name to push.

        Returns:
            Full image URI.
        """
        self._ensure_initialized()

        remote_uri = self.get_image_uri(image_name, tag)

        try:
            import docker

            client = docker.from_env()

            if local_image:
                # Tag the local image with the remote URI
                image = client.images.get(local_image)
                image.tag(remote_uri)

            # Push the image
            logger.info(f"Pushing image to {remote_uri}...")

            for line in client.images.push(remote_uri, stream=True, decode=True):
                if "status" in line:
                    logger.debug(line["status"])
                if "error" in line:
                    raise RuntimeError(line["error"])

            logger.info(f"Successfully pushed {remote_uri}")
            return remote_uri

        except ImportError:
            # Fall back to Docker CLI
            logger.info("docker-py not available, using Docker CLI")

            if local_image:
                subprocess.run(
                    ["docker", "tag", local_image, remote_uri],
                    check=True,
                )

            result = subprocess.run(
                ["docker", "push", remote_uri],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to push image: {result.stderr}")

            logger.info(f"Successfully pushed {remote_uri}")
            return remote_uri

    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        """Pull an image from ECR."""
        self._ensure_initialized()

        remote_uri = self.get_image_uri(image_name, tag)

        try:
            import docker

            client = docker.from_env()

            logger.info(f"Pulling image {remote_uri}...")
            client.images.pull(remote_uri)
            logger.info(f"Successfully pulled {remote_uri}")

        except ImportError:
            result = subprocess.run(
                ["docker", "pull", remote_uri],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to pull image: {result.stderr}")

            logger.info(f"Successfully pulled {remote_uri}")

    def list_images(self) -> list[str]:
        """List images in the repository."""
        self._ensure_initialized()

        try:
            response = self._ecr_client.list_images(
                repositoryName=self._repository,
            )

            images = []
            for image_id in response.get("imageIds", []):
                if "imageTag" in image_id:
                    images.append(image_id["imageTag"])

            return images

        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []

    def delete_image(self, image_name: str, tag: str = None, digest: str = None) -> bool:
        """Delete an image from ECR."""
        self._ensure_initialized()

        try:
            image_ids = []
            if tag:
                image_ids.append({"imageTag": tag})
            elif digest:
                image_ids.append({"imageDigest": digest})
            else:
                raise ValueError("Either tag or digest must be provided")

            self._ecr_client.batch_delete_image(
                repositoryName=self._repository,
                imageIds=image_ids,
            )

            logger.info(f"Deleted image {image_name}:{tag or digest}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete image: {e}")
            return False

    def create_repository(self, repository_name: str = None) -> bool:
        """Create an ECR repository if it doesn't exist.

        Args:
            repository_name: Repository name. Uses configured name if not provided.

        Returns:
            True if created or already exists.
        """
        self._ensure_initialized()

        repo_name = repository_name or self._repository

        try:
            self._ecr_client.create_repository(repositoryName=repo_name)
            logger.info(f"Created ECR repository: {repo_name}")
            return True
        except self._ecr_client.exceptions.RepositoryAlreadyExistsException:
            logger.debug(f"Repository already exists: {repo_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create repository: {e}")
            return False

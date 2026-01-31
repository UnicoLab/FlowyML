"""GCR/Artifact Registry - Native FlowyML Plugin.

This is a native FlowyML implementation for Google Container Registry
and Google Artifact Registry, without requiring any external framework.

Usage:
    from flowyml.plugins import get_plugin

    registry = get_plugin("gcr",
        project="my-gcp-project",
        location="us-central1"
    )

    # Push an image
    uri = registry.push_image("my-ml-image", tag="v1.0")

    # Get image URI
    uri = registry.get_image_uri("my-ml-image", tag="latest")
"""

import subprocess
import logging

from flowyml.plugins.base import ContainerRegistryPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class GCRRegistry(ContainerRegistryPlugin):
    """Native Google Container Registry / Artifact Registry for FlowyML.

    This registry integrates directly with GCP container services
    without any intermediate framework.

    Supports both:
    - Google Container Registry (gcr.io)
    - Google Artifact Registry (recommended for new projects)

    Args:
        project: GCP project ID.
        location: Region for Artifact Registry (e.g., "us-central1").
                 If not provided, uses gcr.io.
        repository: Artifact Registry repository name (only for AR).
        use_artifact_registry: If True, use Artifact Registry.
                              If False, use classic GCR.

    Example:
        # Using Artifact Registry (recommended)
        registry = GCRRegistry(
            project="my-gcp-project",
            location="us-central1",
            repository="ml-images",
            use_artifact_registry=True
        )

        # Using classic GCR
        registry = GCRRegistry(
            project="my-gcp-project",
            use_artifact_registry=False
        )
    """

    METADATA = PluginMetadata(
        name="gcr",
        description="Google Container Registry / Artifact Registry",
        plugin_type=PluginType.CONTAINER_REGISTRY,
        version="1.0.0",
        author="FlowyML",
        packages=["google-cloud-artifact-registry>=1.0"],
        documentation_url="https://cloud.google.com/artifact-registry/docs",
        tags=["container-registry", "gcp", "cloud"],
    )

    def __init__(
        self,
        project: str,
        location: str = None,
        repository: str = None,
        use_artifact_registry: bool = True,
        **kwargs,
    ):
        """Initialize the GCR registry."""
        super().__init__(
            name=kwargs.pop("name", "gcr"),
            project=project,
            location=location,
            repository=repository,
            use_artifact_registry=use_artifact_registry,
            **kwargs,
        )

        self._project = project
        self._location = location
        self._repository = repository
        self._use_ar = use_artifact_registry

    def initialize(self) -> None:
        """Initialize GCR/Artifact Registry connection."""
        # Configure Docker to authenticate with GCR
        try:
            if self._use_ar:
                # Artifact Registry authentication
                result = subprocess.run(
                    ["gcloud", "auth", "configure-docker", f"{self._location}-docker.pkg.dev", "--quiet"],
                    capture_output=True,
                    text=True,
                )
            else:
                # Classic GCR authentication
                result = subprocess.run(
                    ["gcloud", "auth", "configure-docker", "--quiet"],
                    capture_output=True,
                    text=True,
                )

            if result.returncode != 0:
                logger.warning(f"Docker auth may not be configured: {result.stderr}")

            self._is_initialized = True
            logger.info(f"GCR registry initialized for project: {self._project}")

        except FileNotFoundError:
            logger.warning("gcloud CLI not found. Manual Docker authentication may be required.")
            self._is_initialized = True

    def _ensure_initialized(self) -> None:
        """Ensure the registry is initialized."""
        if not self._is_initialized:
            self.initialize()

    @property
    def registry_uri(self) -> str:
        """Get the base registry URI."""
        if self._use_ar:
            return f"{self._location}-docker.pkg.dev/{self._project}/{self._repository}"
        else:
            return f"gcr.io/{self._project}"

    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        """Get the full URI for an image.

        Args:
            image_name: Name of the image.
            tag: Image tag.

        Returns:
            Full image URI.
        """
        return f"{self.registry_uri}/{image_name}:{tag}"

    def push_image(self, image_name: str, tag: str = "latest", local_image: str = None) -> str:
        """Push an image to the registry.

        Args:
            image_name: Name for the image in the registry.
            tag: Image tag.
            local_image: Local image name to push. If not provided,
                        assumes the image is already tagged correctly.

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
        """Pull an image from the registry.

        Args:
            image_name: Name of the image.
            tag: Image tag.
        """
        self._ensure_initialized()

        remote_uri = self.get_image_uri(image_name, tag)

        try:
            import docker

            client = docker.from_env()

            logger.info(f"Pulling image {remote_uri}...")
            client.images.pull(remote_uri)
            logger.info(f"Successfully pulled {remote_uri}")

        except ImportError:
            # Fall back to Docker CLI
            result = subprocess.run(
                ["docker", "pull", remote_uri],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to pull image: {result.stderr}")

            logger.info(f"Successfully pulled {remote_uri}")

    def list_images(self) -> list[str]:
        """List images in the registry.

        Returns:
            List of image names.
        """
        self._ensure_initialized()

        if not self._use_ar:
            logger.warning("Image listing requires Artifact Registry")
            return []

        try:
            from google.cloud import artifactregistry_v1

            client = artifactregistry_v1.ArtifactRegistryClient()

            parent = f"projects/{self._project}/locations/{self._location}/repositories/{self._repository}"

            images = []
            for image in client.list_docker_images(parent=parent):
                # Extract image name from full path
                name = image.name.split("/")[-1]
                images.append(name)

            return images

        except ImportError:
            logger.warning("google-cloud-artifact-registry not installed")
            return []
        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []

    def delete_image(self, image_name: str, tag: str = None, digest: str = None) -> bool:
        """Delete an image from the registry.

        Args:
            image_name: Name of the image.
            tag: Image tag to delete.
            digest: Image digest to delete.

        Returns:
            True if deletion was successful.
        """
        self._ensure_initialized()

        if not self._use_ar:
            logger.warning("Image deletion via API requires Artifact Registry")
            return False

        try:
            from google.cloud import artifactregistry_v1

            client = artifactregistry_v1.ArtifactRegistryClient()

            if digest:
                name = f"projects/{self._project}/locations/{self._location}/repositories/{self._repository}/dockerImages/{image_name}@{digest}"
            elif tag:
                name = f"projects/{self._project}/locations/{self._location}/repositories/{self._repository}/dockerImages/{image_name}:{tag}"
            else:
                raise ValueError("Either tag or digest must be provided")

            client.delete_package(name=name)
            logger.info(f"Deleted image {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete image: {e}")
            return False

"""GCP Stack - Google Cloud Platform integration for flowyml.

This module provides GCP-specific implementations for running pipelines
on Google Cloud Platform using Vertex AI, Cloud Storage, and Container Registry.
"""

from typing import Any

from flowyml.stacks.base import Stack
from flowyml.stacks.components import (
    Orchestrator,
    ArtifactStore,
    ContainerRegistry,
    ResourceConfig,
    DockerConfig,
)


class VertexAIOrchestrator(Orchestrator):
    """Vertex AI orchestrator for running pipelines on Google Cloud.

    This orchestrator submits pipeline jobs to Vertex AI Pipelines,
    allowing for scalable, managed execution in the cloud.

    Example:
        ```python
        from flowyml.stacks.gcp import VertexAIOrchestrator

        orchestrator = VertexAIOrchestrator(
            project_id="my-gcp-project", region="us-central1", service_account="my-sa@my-project.iam.gserviceaccount.com"
        )
        ```
    """

    def __init__(
        self,
        name: str = "vertex_ai",
        project_id: str | None = None,
        region: str = "us-central1",
        service_account: str | None = None,
        network: str | None = None,
        encryption_key: str | None = None,
    ):
        """Initialize Vertex AI orchestrator.

        Args:
            name: Name of the orchestrator
            project_id: GCP project ID
            region: GCP region for Vertex AI
            service_account: Service account email for job execution
            network: VPC network for jobs
            encryption_key: Customer-managed encryption key
        """
        super().__init__(name)
        self.project_id = project_id
        self.region = region
        self.service_account = service_account
        self.network = network
        self.encryption_key = encryption_key

    def validate(self) -> bool:
        """Validate Vertex AI configuration."""
        if not self.project_id:
            raise ValueError("project_id is required for VertexAIOrchestrator")

        # Check if google-cloud-aiplatform is installed
        import importlib.util

        if importlib.util.find_spec("google.cloud.aiplatform") is not None:
            return True
        raise ImportError(
            "google-cloud-aiplatform is required for VertexAIOrchestrator. "
            "Install with: pip install google-cloud-aiplatform",
        )

    def run_pipeline(
        self,
        pipeline: Any,
        resources: ResourceConfig | None = None,
        docker_config: DockerConfig | None = None,
        **kwargs,
    ) -> str:
        """Run pipeline on Vertex AI.

        Args:
            pipeline: Pipeline to run
            resources: Resource configuration
            docker_config: Docker configuration
            **kwargs: Additional arguments

        Returns:
            Job ID
        """
        from google.cloud import aiplatform

        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.region)

        # Create custom job
        job_display_name = f"{pipeline.name}-{pipeline.run_id}"

        # Build worker pool specs
        worker_pool_specs = self._build_worker_pool_specs(
            docker_config=docker_config,
            resources=resources,
        )

        # Create and run custom job
        job = aiplatform.CustomJob(
            display_name=job_display_name,
            worker_pool_specs=worker_pool_specs,
            service_account=self.service_account,
            network=self.network,
            encryption_spec_key_name=self.encryption_key,
        )

        job.run(sync=False)

        return job.resource_name

    def get_run_status(self, run_id: str) -> str:
        """Get status of a Vertex AI job."""
        from google.cloud import aiplatform

        job = aiplatform.CustomJob(run_id)
        return job.state.name

    def _build_worker_pool_specs(
        self,
        docker_config: DockerConfig | None,
        resources: ResourceConfig | None,
    ) -> list[dict]:
        """Build worker pool specifications for Vertex AI."""
        # Default resources
        if resources is None:
            resources = ResourceConfig()

        machine_spec = {
            "machine_type": resources.machine_type or "n1-standard-4",
        }

        if resources.gpu:
            machine_spec["accelerator_type"] = resources.gpu
            machine_spec["accelerator_count"] = resources.gpu_count

        container_spec = {
            "image_uri": (docker_config.image if docker_config else "gcr.io/flowyml/flowyml:latest"),
            "command": ["python", "-m", "flowyml.cli.run"],
        }

        if docker_config and docker_config.env_vars:
            container_spec["env"] = [{"name": k, "value": v} for k, v in docker_config.env_vars.items()]

        return [
            {
                "replica_count": 1,
                "machine_spec": machine_spec,
                "container_spec": container_spec,
            },
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "vertex_ai",
            "project_id": self.project_id,
            "region": self.region,
            "service_account": self.service_account,
            "network": self.network,
        }


class GCSArtifactStore(ArtifactStore):
    """Google Cloud Storage artifact store.

    Stores pipeline artifacts in Google Cloud Storage buckets.

    Example:
        ```python
        from flowyml.stacks.gcp import GCSArtifactStore

        artifact_store = GCSArtifactStore(bucket_name="my-flowyml-artifacts", project_id="my-gcp-project")
        ```
    """

    def __init__(
        self,
        name: str = "gcs",
        bucket_name: str | None = None,
        project_id: str | None = None,
        prefix: str = "flowyml",
    ):
        """Initialize GCS artifact store.

        Args:
            name: Name of the artifact store
            bucket_name: GCS bucket name
            project_id: GCP project ID
            prefix: Prefix for all artifacts in bucket
        """
        super().__init__(name)
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.prefix = prefix

    def validate(self) -> bool:
        """Validate GCS configuration."""
        if not self.bucket_name:
            raise ValueError("bucket_name is required for GCSArtifactStore")

        # Check if google-cloud-storage is installed
        import importlib.util

        if importlib.util.find_spec("google.cloud.storage") is not None:
            return True
        raise ImportError(
            "google-cloud-storage is required for GCSArtifactStore. Install with: pip install google-cloud-storage",
        )

    def save(self, artifact: Any, path: str) -> str:
        """Save artifact to GCS."""
        from google.cloud import storage
        import pickle

        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)

        # Full path with prefix
        full_path = f"{self.prefix}/{path}"
        blob = bucket.blob(full_path)

        # Serialize and upload
        data = pickle.dumps(artifact)
        blob.upload_from_string(data)

        return f"gs://{self.bucket_name}/{full_path}"

    def load(self, path: str) -> Any:
        """Load artifact from GCS."""
        from google.cloud import storage
        import pickle

        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)

        # Handle both full gs:// URIs and relative paths
        if path.startswith("gs://"):
            # Extract bucket and path from URI
            parts = path.replace("gs://", "").split("/", 1)
            blob_path = parts[1] if len(parts) > 1 else ""
        else:
            blob_path = f"{self.prefix}/{path}"

        blob = bucket.blob(blob_path)
        data = blob.download_as_bytes()

        return pickle.loads(data)

    def exists(self, path: str) -> bool:
        """Check if artifact exists in GCS."""
        from google.cloud import storage

        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)

        full_path = f"{self.prefix}/{path}"
        blob = bucket.blob(full_path)

        return blob.exists()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "gcs",
            "bucket_name": self.bucket_name,
            "project_id": self.project_id,
            "prefix": self.prefix,
        }


class GCRContainerRegistry(ContainerRegistry):
    """Google Container Registry integration.

    Manages Docker images in Google Container Registry or Artifact Registry.

    Example:
        ```python
        from flowyml.stacks.gcp import GCRContainerRegistry

        registry = GCRContainerRegistry(project_id="my-gcp-project", registry_uri="gcr.io/my-gcp-project")
        ```
    """

    def __init__(
        self,
        name: str = "gcr",
        project_id: str | None = None,
        registry_uri: str | None = None,
        region: str | None = None,  # For Artifact Registry
    ):
        """Initialize GCR container registry.

        Args:
            name: Name of the registry
            project_id: GCP project ID
            registry_uri: Full registry URI (e.g., gcr.io/project-id)
            region: Region for Artifact Registry (e.g., us-central1)
        """
        super().__init__(name)
        self.project_id = project_id
        self.registry_uri = registry_uri or f"gcr.io/{project_id}"
        self.region = region

    def validate(self) -> bool:
        """Validate registry configuration."""
        if not self.project_id:
            raise ValueError("project_id is required for GCRContainerRegistry")
        return True

    def push_image(self, image_name: str, tag: str = "latest") -> str:
        """Push Docker image to GCR.

        Args:
            image_name: Name of the image
            tag: Image tag

        Returns:
            Full image URI
        """
        import subprocess

        full_uri = self.get_image_uri(image_name, tag)

        # Tag image
        subprocess.run(
            ["docker", "tag", f"{image_name}:{tag}", full_uri],
            check=True,
        )

        # Push to registry
        subprocess.run(
            ["docker", "push", full_uri],
            check=True,
        )

        return full_uri

    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        """Pull Docker image from GCR."""
        import subprocess

        full_uri = self.get_image_uri(image_name, tag)
        subprocess.run(
            ["docker", "pull", full_uri],
            check=True,
        )

    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        """Get full URI for an image."""
        return f"{self.registry_uri}/{image_name}:{tag}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "gcr",
            "project_id": self.project_id,
            "registry_uri": self.registry_uri,
            "region": self.region,
        }


class GCPStack(Stack):
    """Complete GCP stack for running flowyml pipelines on Google Cloud Platform.

    This stack integrates:
    - Vertex AI for orchestration
    - Google Cloud Storage for artifact storage
    - Google Container Registry for Docker images
    - Cloud SQL or Firestore for metadata storage

    Example:
        ```python
        from flowyml.stacks.gcp import GCPStack
        from flowyml.stacks.components import ResourceConfig, DockerConfig
        from flowyml import Pipeline, step

        # Create GCP stack
        stack = GCPStack(
            name="production",
            project_id="my-gcp-project",
            region="us-central1",
            bucket_name="my-flowyml-artifacts",
            registry_uri="gcr.io/my-gcp-project",
        )

        # Define resource requirements
        resources = ResourceConfig(cpu="4", memory="16Gi", gpu="nvidia-tesla-t4", gpu_count=1, machine_type="n1-highmem-4")

        # Define Docker configuration
        docker_config = DockerConfig(
            image="gcr.io/my-gcp-project/ml-pipeline:v1",
            requirements=["tensorflow>=2.12.0", "scikit-learn>=1.0.0"],
            env_vars={"PYTHONUNBUFFERED": "1"},
        )


        # Run pipeline on GCP
        @step
        def train_model():
            # Your training code
            pass


        pipeline = Pipeline("training", stack=stack)
        pipeline.add_step(train_model)

        result = pipeline.run(resources=resources, docker_config=docker_config)
        ```
    """

    def __init__(
        self,
        name: str = "gcp",
        project_id: str | None = None,
        region: str = "us-central1",
        bucket_name: str | None = None,
        registry_uri: str | None = None,
        service_account: str | None = None,
        metadata_store: Any | None = None,
    ):
        """Initialize GCP stack.

        Args:
            name: Stack name
            project_id: GCP project ID
            region: GCP region
            bucket_name: GCS bucket for artifacts
            registry_uri: Container registry URI
            service_account: Service account for job execution
            metadata_store: Metadata store (optional, defaults to local SQLite)
        """
        # Create GCP components
        orchestrator = VertexAIOrchestrator(
            project_id=project_id,
            region=region,
            service_account=service_account,
        )

        artifact_store = GCSArtifactStore(
            bucket_name=bucket_name,
            project_id=project_id,
        )

        container_registry = GCRContainerRegistry(
            project_id=project_id,
            registry_uri=registry_uri,
            region=region,
        )

        # Use local metadata store if not provided
        if metadata_store is None:
            from flowyml.storage.metadata import SQLiteMetadataStore

            metadata_store = SQLiteMetadataStore()

        # Initialize base stack
        super().__init__(
            name=name,
            executor=None,  # Vertex AI handles execution
            artifact_store=artifact_store,
            metadata_store=metadata_store,
            container_registry=container_registry,
            orchestrator=orchestrator,
        )

        self.project_id = project_id
        self.region = region

    def validate(self) -> bool:
        """Validate all GCP stack components."""
        self.orchestrator.validate()
        self.artifact_store.validate()
        self.container_registry.validate()
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert stack configuration to dictionary."""
        return {
            "name": self.name,
            "type": "gcp",
            "project_id": self.project_id,
            "region": self.region,
            "orchestrator": self.orchestrator.to_dict(),
            "artifact_store": self.artifact_store.to_dict(),
            "container_registry": self.container_registry.to_dict(),
        }

"""Azure Stack Components and Preset Stack."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path
from typing import Any

from flowyml.stacks.base import Stack
from flowyml.stacks.components import ArtifactStore, ContainerRegistry, Orchestrator, DockerConfig, ResourceConfig
from flowyml.stacks.plugins import register_component
from flowyml.storage.metadata import SQLiteMetadataStore


@register_component(name="azure_blob")
class AzureBlobArtifactStore(ArtifactStore):
    """Artifact store backed by Azure Blob Storage."""

    def __init__(
        self,
        name: str = "azure_blob",
        account_url: str | None = None,
        container_name: str | None = None,
        credential: Any | None = None,
    ):
        super().__init__(name)
        self.account_url = account_url
        self.container_name = container_name
        self.credential = credential

    def _client(self):
        from azure.storage.blob import BlobServiceClient

        credential = self.credential
        if credential is None:
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

        return BlobServiceClient(account_url=self.account_url, credential=credential)

    def validate(self) -> bool:
        if not self.account_url or not self.container_name:
            raise ValueError("account_url and container_name are required for AzureBlobArtifactStore")
        try:
            client = self._client()
            container_client = client.get_container_client(self.container_name)
            container_client.get_container_properties()
        except Exception as exc:
            raise ValueError(f"Unable to access container '{self.container_name}': {exc}") from exc
        return True

    def save(self, artifact: Any, path: str) -> str:
        blob_name = path.lstrip("/")
        client = self._client().get_container_client(self.container_name)
        if isinstance(artifact, (str, Path)) and Path(artifact).exists():
            with open(Path(artifact), "rb") as f:
                client.upload_blob(name=blob_name, data=f, overwrite=True)
        else:
            data = artifact if isinstance(artifact, bytes) else str(artifact).encode()
            client.upload_blob(name=blob_name, data=data, overwrite=True)
        return f"{self.account_url}/{self.container_name}/{blob_name}"

    def load(self, path: str) -> bytes:
        blob_name = path.lstrip("/")
        client = self._client().get_blob_client(self.container_name, blob_name)
        downloader = client.download_blob()
        return downloader.readall()

    def exists(self, path: str) -> bool:
        blob_name = path.lstrip("/")
        client = self._client().get_blob_client(self.container_name, blob_name)
        return client.exists()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "azure_blob",
            "account_url": self.account_url,
            "container_name": self.container_name,
        }


@register_component(name="acr")
class ACRContainerRegistry(ContainerRegistry):
    """Azure Container Registry integration."""

    def __init__(
        self,
        name: str = "acr",
        registry_name: str | None = None,
        login_server: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        super().__init__(name)
        self.registry_name = registry_name
        self.login_server = login_server or (f"{registry_name}.azurecr.io" if registry_name else None)
        self.username = username
        self.password = password

    def validate(self) -> bool:
        if not self.registry_name and not self.login_server:
            raise ValueError("registry_name or login_server is required for ACRContainerRegistry")
        return True

    def _login(self) -> None:
        if self.username and self.password:
            subprocess.run(
                ["docker", "login", self.login_server, "-u", self.username, "-p", self.password],
                check=True,
            )
        else:
            subprocess.run(["az", "acr", "login", "--name", self.registry_name], check=True)

    def push_image(self, image_name: str, tag: str = "latest") -> str:
        full_uri = self.get_image_uri(image_name, tag)
        self._login()
        subprocess.run(["docker", "tag", f"{image_name}:{tag}", full_uri], check=True)
        subprocess.run(["docker", "push", full_uri], check=True)
        return full_uri

    def pull_image(self, image_name: str, tag: str = "latest") -> None:
        full_uri = self.get_image_uri(image_name, tag)
        self._login()
        subprocess.run(["docker", "pull", full_uri], check=True)

    def get_image_uri(self, image_name: str, tag: str = "latest") -> str:
        return f"{self.login_server}/{image_name}:{tag}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "acr",
            "login_server": self.login_server,
            "registry_name": self.registry_name,
        }


@register_component(name="azure_ml")
class AzureMLOrchestrator(Orchestrator):
    """Submit pipeline runs to Azure ML managed compute."""

    def __init__(
        self,
        name: str = "azure_ml",
        subscription_id: str | None = None,
        resource_group: str | None = None,
        workspace_name: str | None = None,
        compute: str | None = None,
        experiment_name: str = "flowyml",
        credential: Any | None = None,
    ):
        super().__init__(name)
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.workspace_name = workspace_name
        self.compute = compute
        self.experiment_name = experiment_name
        self.credential = credential

    def _client(self):
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential

        credential = self.credential or DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        return MLClient(
            credential,
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group,
            workspace_name=self.workspace_name,
        )

    def validate(self) -> bool:
        if not all([self.subscription_id, self.resource_group, self.workspace_name, self.compute]):
            raise ValueError(
                "subscription_id, resource_group, workspace_name, and compute are required for AzureMLOrchestrator",
            )
        return True

    def run_pipeline(
        self,
        pipeline: Any,
        resources: ResourceConfig | None = None,
        docker_config: DockerConfig | None = None,
        **kwargs,
    ) -> str:
        from azure.ai.ml.entities import CommandJob, Environment

        client = self._client()
        run_id = getattr(pipeline, "run_id", uuid.uuid4().hex)
        job_name = kwargs.get("job_name") or f"{pipeline.name}-{run_id[:8]}"
        image = (
            docker_config.image
            if docker_config and docker_config.image
            else "mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04"
        )
        env = Environment(image=image, name=f"flowyml-{pipeline.name}")

        command = kwargs.get("command") or "python -m flowyml.cli.run"
        command_job = CommandJob(
            name=job_name,
            display_name=job_name,
            experiment_name=self.experiment_name,
            compute=self.compute,
            environment=env,
            command=command,
            description="FlowyML pipeline run",
        )

        submitted = client.jobs.create_or_update(command_job)
        return submitted.name

    def get_run_status(self, run_id: str) -> str:
        client = self._client()
        job = client.jobs.get(run_id)
        return job.status

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "azure_ml",
            "subscription_id": self.subscription_id,
            "resource_group": self.resource_group,
            "workspace_name": self.workspace_name,
            "compute": self.compute,
        }


class AzureMLStack(Stack):
    """Managed Azure ML stack built from AzureML orchestrator, Blob storage, and ACR."""

    def __init__(
        self,
        name: str = "azure",
        subscription_id: str | None = None,
        resource_group: str | None = None,
        workspace_name: str | None = None,
        compute: str | None = None,
        account_url: str | None = None,
        container_name: str | None = None,
        registry_name: str | None = None,
        login_server: str | None = None,
        metadata_store: Any | None = None,
    ):
        orchestrator = AzureMLOrchestrator(
            subscription_id=subscription_id,
            resource_group=resource_group,
            workspace_name=workspace_name,
            compute=compute,
        )
        artifact_store = AzureBlobArtifactStore(account_url=account_url, container_name=container_name)
        container_registry = ACRContainerRegistry(registry_name=registry_name, login_server=login_server)

        if metadata_store is None:
            metadata_store = SQLiteMetadataStore()

        super().__init__(
            name=name,
            executor=None,
            artifact_store=artifact_store,
            metadata_store=metadata_store,
            container_registry=container_registry,
            orchestrator=orchestrator,
        )

        self.subscription_id = subscription_id
        self.workspace_name = workspace_name

    def validate(self) -> bool:
        self.orchestrator.validate()
        self.artifact_store.validate()
        self.container_registry.validate()
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": "azure",
            "subscription_id": self.subscription_id,
            "workspace_name": self.workspace_name,
            "orchestrator": self.orchestrator.to_dict(),
            "artifact_store": self.artifact_store.to_dict(),
            "container_registry": self.container_registry.to_dict(),
        }

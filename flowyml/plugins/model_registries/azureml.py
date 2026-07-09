"""Azure ML Model Registry - Native FlowyML Plugin.

Registers, versions, and stages models in an Azure Machine Learning workspace
(or an Azure ML *registry* for cross-workspace sharing).  Azure ML has no
built-in stage concept like MLflow, so stages are represented as model tags
(``stage=production`` etc.), which is the common Azure ML convention.

Requires ``pip install flowyml[azure]`` (azure-ai-ml, azure-identity).
"""

from __future__ import annotations

import logging
from typing import Any

from flowyml.plugins.base import ModelRegistryPlugin, PluginMetadata, PluginType
from flowyml.stacks.plugins import register_component
from flowyml.utils.observability import trace_execution

logger = logging.getLogger(__name__)


@register_component(name="azureml_registry")
class AzureMLModelRegistry(ModelRegistryPlugin):
    """Azure ML Model Registry for FlowyML.

    Args:
        subscription_id: Azure subscription id.
        resource_group: Azure resource group.
        workspace_name: Azure ML workspace name (workspace-scoped registry).
        registry_name: Azure ML registry name (org-scoped, cross-workspace).
            When set, models are (de)registered from the registry instead of
            the workspace.
        credential: Optional azure credential (defaults to DefaultAzureCredential).
    """

    metadata = PluginMetadata(
        name="azureml_registry",
        version="1.0.0",
        description="Azure ML Model Registry",
        author="FlowyML Team",
        plugin_type=PluginType.MODEL_REGISTRY,
        tags=["model-registry", "azure", "azureml", "versioning"],
        packages=["azure-ai-ml>=1.0", "azure-identity>=1.12"],
    )

    def __init__(
        self,
        subscription_id: str | None = None,
        resource_group: str | None = None,
        workspace_name: str | None = None,
        registry_name: str | None = None,
        credential: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.workspace_name = workspace_name
        self.registry_name = registry_name
        self.credential = credential
        self._client = None

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.MODEL_REGISTRY

    def initialize(self) -> None:
        if self._client is not None:
            return
        try:
            from azure.ai.ml import MLClient
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:
            raise ImportError(
                "azure-ai-ml is required. Install with: pip install flowyml[azure]",
            ) from exc

        credential = self.credential or DefaultAzureCredential(
            exclude_shared_token_cache_credential=True,
        )
        kwargs: dict[str, Any] = {"credential": credential, "subscription_id": self.subscription_id}
        if self.registry_name:
            kwargs["registry_name"] = self.registry_name
        else:
            kwargs["resource_group_name"] = self.resource_group
            kwargs["workspace_name"] = self.workspace_name
        self._client = MLClient(**kwargs)
        logger.info(
            "Azure ML Model Registry initialized (%s)",
            self.registry_name or f"{self.resource_group}/{self.workspace_name}",
        )

    @trace_execution(operation_name="azureml_register_model")
    def register_model(
        self,
        name: str,
        model_uri: str,
        version: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Register a local path / URI as a new Azure ML model version.

        Args:
            name: Registered model name.
            model_uri: Local path or Azure ML datastore/job URI to the artifact.
            version: Optional explicit version (Azure ML auto-increments if omitted).
            metadata: Tags to attach (e.g. ``{"stage": "staging", "auc": "0.91"}``).

        Returns:
            The created model version as a string.
        """
        self.initialize()
        from azure.ai.ml.constants import AssetTypes
        from azure.ai.ml.entities import Model

        model_type = AssetTypes.CUSTOM_MODEL
        lowered = model_uri.lower()
        if lowered.rstrip("/").endswith("mlmodel") or "mlflow" in lowered:
            model_type = AssetTypes.MLFLOW_MODEL

        model = Model(
            path=model_uri,
            name=name,
            version=str(version) if version else None,
            type=model_type,
            tags={k: str(v) for k, v in (metadata or {}).items()},
            description=(metadata or {}).get("description", ""),
        )
        created = self._client.models.create_or_update(model)
        logger.info("Registered Azure ML model '%s' version %s", name, created.version)
        return str(created.version)

    @trace_execution(operation_name="azureml_get_model")
    def get_model(self, name: str, version: str | None = None) -> Any:
        """Return an Azure ML model entity (metadata handle)."""
        self.initialize()
        if version:
            return self._client.models.get(name=name, version=str(version))
        return self._client.models.get(name=name, label="latest")

    def download_model(self, name: str, version: str | None = None, download_path: str = ".") -> str:
        """Download the model artifacts to ``download_path``; returns the path."""
        self.initialize()
        model = self.get_model(name, version)
        self._client.models.download(
            name=name,
            version=str(model.version),
            download_path=download_path,
        )
        return download_path

    @trace_execution(operation_name="azureml_list_models")
    def list_models(self, name: str | None = None) -> list[dict]:
        self.initialize()
        if name:
            versions = self._client.models.list(name=name)
            return [{"name": name, "version": m.version, "tags": dict(m.tags or {})} for m in versions]
        models = self._client.models.list()
        return [{"name": m.name, "latest_version": getattr(m, "latest_version", None)} for m in models]

    @trace_execution(operation_name="azureml_transition_stage")
    def transition_model_stage(self, name: str, version: str, stage: str) -> None:
        """Set the ``stage`` tag on a model version (Azure ML has no native stages)."""
        self.initialize()
        model = self._client.models.get(name=name, version=str(version))
        tags = dict(model.tags or {})
        tags["stage"] = stage.lower()
        model.tags = tags
        self._client.models.create_or_update(model)
        logger.info("Set stage tag '%s' on Azure ML model %s v%s", stage.lower(), name, version)

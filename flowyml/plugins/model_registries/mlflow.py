"""MLflow Model Registry - Native FlowyML Plugin.

This plugin provides explicit Model Registry capabilities using MLflow,
allowing distinct management from Experiment Tracking.
"""

import logging
from typing import Any
from flowyml.utils.observability import trace_execution

from flowyml.plugins.base import ModelRegistryPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


# import removed from here


class MLflowModelRegistry(ModelRegistryPlugin):
    """Native MLflow Model Registry for FlowyML.

    Manage model lifecycles (registration, versioning, stage transition)
    directly through MLflow.

    Args:
        registry_uri: URI for the registry (e.g., sqlite:///, postgresql://).
    """

    metadata = PluginMetadata(
        name="mlflow_registry",
        version="1.0.0",
        description="MLflow Model Registry",
        author="FlowyML Team",
        plugin_type=PluginType.MODEL_REGISTRY,
        tags=["model-registry", "mlflow", "versioning"],
        packages=["mlflow>=2.0"],
    )

    def __init__(self, registry_uri: str = None, **kwargs):
        super().__init__(**kwargs)
        self.registry_uri = registry_uri
        self._client = None

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.MODEL_REGISTRY

    def initialize(self) -> None:
        """Initialize MLflow Client."""
        try:
            import mlflow
            from mlflow.tracking import MlflowClient

            if self.registry_uri:
                mlflow.set_registry_uri(self.registry_uri)

            self._client = MlflowClient(registry_uri=self.registry_uri)
            logger.info(
                f"MLflow Model Registry initialized (URI: {self.registry_uri or 'default'})",
            )

        except ImportError:
            raise ImportError(
                "mlflow is required. Install with: pip install mlflow",
            )

    @trace_execution(operation_name="mlflow_register_model")
    def register_model(
        self,
        name: str,
        model_uri: str,
        version: str = None,
        metadata: dict = None,
    ) -> str:
        """Register a model artifact as a new model version.

        Args:
            name: Name of the registered model.
            model_uri: Source URI of the model artifact (e.g., runs:/.../model).
            version: Ignored by MLflow (auto-incremented).
            metadata: Tags/Description to set.

        Returns:
            The new model version number.
        """
        self.initialize()

        # 1. Create registered model if it doesn't exist
        try:
            self._client.create_registered_model(name)
            logger.info(f"Created new registered model: {name}")
        except Exception:
            # Assume exists
            pass

        # 2. Create version
        mv = self._client.create_model_version(
            name=name,
            source=model_uri,
            run_id=None,  # Derive from source if possible
            tags=metadata,
        )

        logger.info(f"Registered model '{name}' version {mv.version}")
        return mv.version

    @trace_execution(operation_name="mlflow_get_model")
    def get_model(self, name: str, version: str = None) -> Any:
        """Get model version details (metadata).
        To load the actual model object, use ExperimentTracker.load_model or standard mlflow.load_model.
        """
        self.initialize()
        if version:
            return self._client.get_model_version(name, version)
        else:
            # Get latest
            # MLflow specific: get latest versions for all stages
            return self._client.get_latest_versions(name, stages=None)

    @trace_execution(operation_name="mlflow_list_models")
    def list_models(self, name: str = None) -> list[dict]:
        """List registered models."""
        self.initialize()
        filter_str = f"name = '{name}'" if name else None

        models = self._client.search_registered_models(filter_string=filter_str)
        return [
            {
                "name": m.name,
                "latest_versions": [v.version for v in m.latest_versions],
                "creation_timestamp": m.creation_timestamp,
            }
            for m in models
        ]

    @trace_execution(operation_name="mlflow_transition_stage")
    def transition_model_stage(
        self,
        name: str,
        version: str,
        stage: str,
    ) -> None:
        """Transition model to stage (Staging, Production, Archived)."""
        self.initialize()

        # Map generic stages to MLflow specific if needed, but they are usually compatible
        # MLflow: "Staging", "Production", "Archived", "None"

        valid_stages = ["Staging", "Production", "Archived", "None"]
        target_stage = stage.capitalize()

        if target_stage not in valid_stages:
            logger.warning(f"Stage '{stage}' might not be valid. Valid: {valid_stages}")

        self._client.transition_model_version_stage(
            name=name,
            version=version,
            stage=target_stage,
            archive_existing_versions=True,  # Standard practice
        )
        logger.info(f"Transitioned {name} v{version} to {target_stage}")

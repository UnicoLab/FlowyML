"""Model registry for version management and deployment.

This module provides SQL-backed model registry capabilities for managing
model versions, stages, and metadata in a production-safe manner.
"""

import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flowyml.assets.base import Asset


class ModelStage(str, Enum):
    """Model deployment stages."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


@dataclass
class ModelVersion:
    """Model version metadata."""

    name: str
    version: str
    stage: ModelStage
    created_at: str
    updated_at: str
    model_path: str
    framework: str
    metrics: dict[str, float] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    schema: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    author: str | None = None
    parent_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["stage"] = self.stage.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelVersion":
        """Create from dictionary."""
        data = data.copy()
        # Handle stage conversion
        if isinstance(data.get("stage"), str):
            data["stage"] = ModelStage(data["stage"])
        # Remove SQL-specific fields
        data.pop("id", None)
        return cls(**data)


class ModelRegistry:
    """Registry for managing model versions and deployments.

    This registry uses SQL storage for production-safe concurrent access.
    Model files are still stored on the filesystem, but metadata is in the database.

    Example:
        ```python
        from flowyml import ModelRegistry

        registry = ModelRegistry()

        # Register a new model
        registry.register(
            model=trained_model,
            name="sentiment_classifier",
            version="v1.0.0",
            framework="pytorch",
            metrics={"accuracy": 0.95, "f1": 0.94},
            tags={"task": "classification", "lang": "en"},
        )

        # Promote to production
        registry.promote("sentiment_classifier", "v1.0.0", ModelStage.PRODUCTION)

        # Load production model
        model = registry.load("sentiment_classifier", stage=ModelStage.PRODUCTION)

        # Compare versions
        comparison = registry.compare_versions("sentiment_classifier", ["v1.0.0", "v1.1.0"])
        ```
    """

    def __init__(
        self,
        registry_path: str = ".flowyml/model_registry",
        db_url: str | None = None,
    ):
        """Initialize model registry.

        Args:
            registry_path: Path to model file storage
            db_url: Database URL for metadata storage (uses env var if not provided)
        """
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)

        # Initialize SQL storage for metadata
        self._db_url = db_url or os.getenv("FLOWYML_DATABASE_URL")
        self._store = None

    @property
    def _metadata_store(self):
        """Lazy-load the metadata store."""
        if self._store is None:
            from flowyml.storage.sql import SQLMetadataStore

            self._store = SQLMetadataStore(db_url=self._db_url)
        return self._store

    def register(
        self,
        model: Any,
        name: str,
        version: str,
        framework: str,
        stage: ModelStage = ModelStage.DEVELOPMENT,
        metrics: dict[str, float] | None = None,
        tags: dict[str, str] | None = None,
        schema: dict[str, Any] | None = None,
        description: str = "",
        author: str | None = None,
        parent_version: str | None = None,
    ) -> ModelVersion:
        """Register a new model version.

        Args:
            model: Model object to register
            name: Model name
            version: Version string (e.g., "v1.0.0")
            framework: Framework name (pytorch, tensorflow, sklearn)
            stage: Deployment stage
            metrics: Model metrics
            tags: Model tags
            schema: Optional explicit schema (overrides introspection)
            description: Model description
            author: Model author
            parent_version: Parent version if this is an update

        Returns:
            ModelVersion instance

        Raises:
            ValueError: If version already exists
        """
        # Check if version already exists
        existing = self._metadata_store.get_model_version(name, version)
        if existing:
            raise ValueError(f"Version {version} already exists for model {name}")

        # Introspect model schema if not provided
        from flowyml.utils.model_introspection import introspect_model

        inferred_schema = introspect_model(model, framework)
        # Merge inferred schema with provided schema (provided takes precedence)
        final_schema = inferred_schema
        if schema:
            final_schema.update(schema)

        # Create model directory
        model_dir = self.registry_path / name / version
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save model using appropriate materializer
        model_path = model_dir / "model"
        self._save_model(model, model_path, framework)

        # Create version metadata
        now = datetime.now().isoformat()

        # Save to SQL database
        self._metadata_store.save_model_version(
            name=name,
            version=version,
            stage=stage.value,
            framework=framework,
            model_path=str(model_path),
            metrics=metrics,
            tags=tags,
            schema=final_schema,
            description=description,
            author=author,
            parent_version=parent_version,
        )

        return ModelVersion(
            name=name,
            version=version,
            stage=stage,
            created_at=now,
            updated_at=now,
            model_path=str(model_path),
            framework=framework,
            metrics=metrics or {},
            tags=tags or {},
            schema=final_schema,
            description=description,
            author=author,
            parent_version=parent_version,
        )

    def _save_model(self, model: Any, path: Path, framework: str) -> None:
        """Save model using appropriate method.

        Args:
            model: Model to save
            path: Path to save to
            framework: Framework name
        """
        from flowyml.storage.materializers.base import get_materializer

        # Try to get appropriate materializer
        materializer = get_materializer(model)

        if materializer:
            materializer.save(model, path)
        else:
            # Fallback to pickle
            import pickle

            with open(path, "wb") as f:
                pickle.dump(model, f)

    def _load_model(self, path: Path, framework: str) -> Any:
        """Load model from path.

        Args:
            path: Path to load from
            framework: Framework name

        Returns:
            Loaded model
        """
        # Try framework-specific loading
        if framework == "pytorch":
            from flowyml.storage.materializers.pytorch import PyTorchMaterializer

            return PyTorchMaterializer().load(path)
        elif framework == "tensorflow":
            from flowyml.storage.materializers.tensorflow import TensorFlowMaterializer

            return TensorFlowMaterializer().load(path)
        elif framework == "sklearn":
            from flowyml.storage.materializers.sklearn import SklearnMaterializer

            return SklearnMaterializer().load(path)
        else:
            # Fallback to pickle
            import pickle

            with open(path, "rb") as f:
                return pickle.load(f)  # noqa: S301

    def get_version(self, name: str, version: str) -> ModelVersion | None:
        """Get specific model version.

        Args:
            name: Model name
            version: Version string

        Returns:
            ModelVersion or None if not found
        """
        data = self._metadata_store.get_model_version(name, version)
        if data:
            return ModelVersion.from_dict(data)
        return None

    def list_versions(self, name: str) -> list[ModelVersion]:
        """List all versions of a model.

        Args:
            name: Model name

        Returns:
            List of ModelVersion instances
        """
        versions = self._metadata_store.list_model_versions(name=name)
        return [ModelVersion.from_dict(v) for v in versions]

    def list_models(self) -> list[str]:
        """List all registered models.

        Returns:
            List of model names
        """
        return self._metadata_store.list_registered_models()

    def get_latest_version(self, name: str, stage: ModelStage | None = None) -> ModelVersion | None:
        """Get latest version of a model.

        Args:
            name: Model name
            stage: Optional stage filter

        Returns:
            Latest ModelVersion or None
        """
        stage_str = stage.value if stage else None
        data = self._metadata_store.get_latest_model_version(name, stage=stage_str)
        if data:
            return ModelVersion.from_dict(data)
        return None

    def load(
        self,
        name: str,
        version: str | None = None,
        stage: ModelStage | None = None,
    ) -> Any:
        """Load a model from registry.

        Args:
            name: Model name
            version: Specific version (if None, loads latest)
            stage: Stage filter (if version is None)

        Returns:
            Loaded model

        Raises:
            ValueError: If model not found
        """
        model_version = self.get_version(name, version) if version else self.get_latest_version(name, stage)

        if not model_version:
            raise ValueError(f"Model {name} not found")

        return self._load_model(Path(model_version.model_path), model_version.framework)

    def promote(
        self,
        name: str,
        version: str,
        to_stage: ModelStage,
    ) -> ModelVersion:
        """Promote model to a different stage.

        Args:
            name: Model name
            version: Version to promote
            to_stage: Target stage

        Returns:
            Updated ModelVersion

        Raises:
            ValueError: If model not found
        """
        model_version = self.get_version(name, version)

        if not model_version:
            raise ValueError(f"Model {name} version {version} not found")

        # Update stage in database
        success = self._metadata_store.promote_model(name, version, to_stage.value)
        if not success:
            raise ValueError(f"Failed to promote model {name} version {version}")

        return self.get_version(name, version)

    def rollback(
        self,
        name: str,
        to_version: str,
        stage: ModelStage = ModelStage.PRODUCTION,
    ) -> ModelVersion:
        """Rollback to a previous version.

        Args:
            name: Model name
            to_version: Version to rollback to
            stage: Stage to set (default: production)

        Returns:
            Rolled back ModelVersion

        Raises:
            ValueError: If version not found
        """
        return self.promote(name, to_version, stage)

    def delete_version(self, name: str, version: str) -> None:
        """Delete a model version.

        Args:
            name: Model name
            version: Version to delete

        Raises:
            ValueError: If model not found or in production
        """
        model_version = self.get_version(name, version)

        if not model_version:
            raise ValueError(f"Model {name} version {version} not found")

        # Don't allow deleting production models
        if model_version.stage == ModelStage.PRODUCTION:
            raise ValueError("Cannot delete production model. Demote first.")

        # Delete from database
        self._metadata_store.delete_model_version(name, version)

        # Delete model files
        model_dir = Path(model_version.model_path).parent
        if model_dir.exists():
            shutil.rmtree(model_dir)

    def compare_versions(
        self,
        name: str,
        versions: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Compare multiple versions of a model.

        Args:
            name: Model name
            versions: List of versions to compare

        Returns:
            Dictionary with comparison data
        """
        comparison = {}

        for version in versions:
            model_version = self.get_version(name, version)
            if model_version:
                comparison[version] = {
                    "stage": model_version.stage.value,
                    "metrics": model_version.metrics,
                    "tags": model_version.tags,
                    "created_at": model_version.created_at,
                    "framework": model_version.framework,
                }

        return comparison

    def search(
        self,
        tags: dict[str, str] | None = None,
        stage: ModelStage | None = None,
        min_metrics: dict[str, float] | None = None,
    ) -> list[ModelVersion]:
        """Search for models by criteria.

        Args:
            tags: Tags to match
            stage: Stage to filter by
            min_metrics: Minimum metric values

        Returns:
            List of matching ModelVersion instances
        """
        stage_str = stage.value if stage else None
        all_versions = self._metadata_store.list_model_versions(stage=stage_str)

        results = []
        for version_dict in all_versions:
            version = ModelVersion.from_dict(version_dict)

            # Check tags
            if tags and not all(version.tags.get(k) == v for k, v in tags.items()):
                continue

            # Check metrics
            if min_metrics:
                if not all(version.metrics.get(k, float("-inf")) >= v for k, v in min_metrics.items()):
                    continue

            results.append(version)

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary with statistics
        """
        all_versions = self._metadata_store.list_model_versions()
        models = set()
        stage_counts = {stage.value: 0 for stage in ModelStage}

        for v in all_versions:
            models.add(v["name"])
            stage_counts[v["stage"]] += 1

        return {
            "total_models": len(models),
            "total_versions": len(all_versions),
            "by_stage": stage_counts,
        }

    # ========== Asset Integration Methods ==========

    def register_asset(
        self,
        model_asset: "Asset",
        version: str | None = None,
        stage: ModelStage = ModelStage.DEVELOPMENT,
        description: str = "",
        author: str | None = None,
        capture_environment: bool = False,
    ) -> ModelVersion:
        """Register a Model asset directly to the registry.

        This method leverages the auto-extracted metadata from Model assets,
        making registration simpler and more consistent.

        Args:
            model_asset: A Model asset (from flowyml.assets.model)
            version: Version string (defaults to asset's version)
            stage: Deployment stage
            description: Model description
            author: Model author
            capture_environment: Whether to capture Python environment

        Returns:
            ModelVersion instance

        Example:
            >>> from flowyml import Model, ModelRegistry
            >>> model_asset = Model.create(data=trained_model, name="classifier")
            >>> registry = ModelRegistry()
            >>> registry.register_asset(model_asset, version="v1.0.0")
        """
        # Get version from asset if not provided
        version = version or model_asset.version

        # Extract metadata from asset
        properties = model_asset.properties if hasattr(model_asset, "properties") else {}
        tags = model_asset.tags if hasattr(model_asset, "tags") else {}

        # Get framework from auto-extracted properties
        framework = properties.get("framework", "unknown")

        # Extract metrics from properties (common keys)
        metrics = {}
        for key in ["accuracy", "f1", "precision", "recall", "loss", "auc", "mse", "mae"]:
            if key in properties:
                metrics[key] = properties[key]

        # Capture environment if requested
        if capture_environment:
            from flowyml.registry.model_environment import ModelEnvironment

            env = ModelEnvironment.from_current()
            tags["python_version"] = env.python_version
            tags["platform"] = env.platform
            properties["environment"] = env.to_dict()

        return self.register(
            model=model_asset.data,
            name=model_asset.name,
            version=version,
            framework=framework,
            stage=stage,
            metrics=metrics,
            tags=tags,
            description=description or properties.get("description", ""),
            author=author,
            parent_version=None,
        )

    def to_asset(
        self,
        name: str,
        version: str | None = None,
        stage: ModelStage | None = None,
    ) -> "Asset":
        """Load a model version as a Model asset.

        This creates a Model asset with all the stored metadata,
        enabling seamless integration with FlowyML pipelines.

        Args:
            name: Model name
            version: Specific version (if None, loads latest)
            stage: Stage filter (if version is None)

        Returns:
            Model asset with loaded model and metadata

        Example:
            >>> registry = ModelRegistry()
            >>> model_asset = registry.to_asset("classifier", version="v1.0.0")
            >>> print(model_asset.properties)
        """
        from flowyml.assets.model import Model

        model_version = self.get_version(name, version) if version else self.get_latest_version(name, stage)

        if not model_version:
            raise ValueError(f"Model {name} not found")

        model_data = self.load(name, version or model_version.version)

        properties = {
            "framework": model_version.framework,
            "stage": model_version.stage.value,
            "created_at": model_version.created_at,
            "updated_at": model_version.updated_at,
            **model_version.metrics,
        }

        return Model(
            name=name,
            version=model_version.version,
            data=model_data,
            tags=model_version.tags,
            properties=properties,
        )

    def capture_environment(self) -> dict[str, Any]:
        """Capture current Python environment.

        Returns:
            Dictionary with environment info
        """
        from flowyml.registry.model_environment import ModelEnvironment

        return ModelEnvironment.from_current().to_dict()

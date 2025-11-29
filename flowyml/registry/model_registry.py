"""Model registry for version management and deployment."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import shutil


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
        data["stage"] = ModelStage(data["stage"])
        return cls(**data)


class ModelRegistry:
    """Registry for managing model versions and deployments.

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

    def __init__(self, registry_path: str = ".flowyml/model_registry"):
        """Initialize model registry.

        Args:
            registry_path: Path to registry storage
        """
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.registry_path / "registry.json"
        self._metadata: dict[str, list[dict]] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load registry metadata from disk."""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                self._metadata = json.load(f)
        else:
            self._metadata = {}

    def _save_metadata(self) -> None:
        """Save registry metadata to disk."""
        with open(self.metadata_file, "w") as f:
            json.dump(self._metadata, f, indent=2)

    def register(
        self,
        model: Any,
        name: str,
        version: str,
        framework: str,
        stage: ModelStage = ModelStage.DEVELOPMENT,
        metrics: dict[str, float] | None = None,
        tags: dict[str, str] | None = None,
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
            description: Model description
            author: Model author
            parent_version: Parent version if this is an update

        Returns:
            ModelVersion instance

        Raises:
            ValueError: If version already exists
        """
        # Check if version already exists
        if name in self._metadata:
            existing_versions = [v["version"] for v in self._metadata[name]]
            if version in existing_versions:
                raise ValueError(f"Version {version} already exists for model {name}")

        # Create model directory
        model_dir = self.registry_path / name / version
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save model using appropriate materializer
        model_path = model_dir / "model"
        self._save_model(model, model_path, framework)

        # Create version metadata
        now = datetime.now().isoformat()
        model_version = ModelVersion(
            name=name,
            version=version,
            stage=stage,
            created_at=now,
            updated_at=now,
            model_path=str(model_path),
            framework=framework,
            metrics=metrics or {},
            tags=tags or {},
            description=description,
            author=author,
            parent_version=parent_version,
        )

        # Add to metadata
        if name not in self._metadata:
            self._metadata[name] = []

        self._metadata[name].append(model_version.to_dict())
        self._save_metadata()

        return model_version

    def _save_model(self, model: Any, path: Path, framework: str) -> None:
        """Save model using appropriate method.

        Args:
            model: Model to save
            path: Path to save to
            framework: Framework name
        """
        from flowyml.storage.materializers import get_materializer

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
                return pickle.load(f)

    def get_version(self, name: str, version: str) -> ModelVersion | None:
        """Get specific model version.

        Args:
            name: Model name
            version: Version string

        Returns:
            ModelVersion or None if not found
        """
        if name not in self._metadata:
            return None

        for v in self._metadata[name]:
            if v["version"] == version:
                return ModelVersion.from_dict(v)

        return None

    def list_versions(self, name: str) -> list[ModelVersion]:
        """List all versions of a model.

        Args:
            name: Model name

        Returns:
            List of ModelVersion instances
        """
        if name not in self._metadata:
            return []

        return [ModelVersion.from_dict(v) for v in self._metadata[name]]

    def list_models(self) -> list[str]:
        """List all registered models.

        Returns:
            List of model names
        """
        return list(self._metadata.keys())

    def get_latest_version(self, name: str, stage: ModelStage | None = None) -> ModelVersion | None:
        """Get latest version of a model.

        Args:
            name: Model name
            stage: Optional stage filter

        Returns:
            Latest ModelVersion or None
        """
        versions = self.list_versions(name)

        if stage:
            versions = [v for v in versions if v.stage == stage]

        if not versions:
            return None

        # Sort by created_at
        versions.sort(key=lambda v: v.created_at, reverse=True)
        return versions[0]

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

        # Update stage in metadata
        for v in self._metadata[name]:
            if v["version"] == version:
                v["stage"] = to_stage.value
                v["updated_at"] = datetime.now().isoformat()
                break

        self._save_metadata()

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

        # Remove from metadata
        self._metadata[name] = [v for v in self._metadata[name] if v["version"] != version]

        # Delete model files
        model_dir = Path(model_version.model_path).parent
        if model_dir.exists():
            shutil.rmtree(model_dir)

        self._save_metadata()

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
        results = []

        for name in self._metadata:
            for version_dict in self._metadata[name]:
                version = ModelVersion.from_dict(version_dict)

                # Check stage
                if stage and version.stage != stage:
                    continue

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
        total_models = len(self._metadata)
        total_versions = sum(len(versions) for versions in self._metadata.values())

        stage_counts = {stage.value: 0 for stage in ModelStage}
        for versions in self._metadata.values():
            for v in versions:
                stage_counts[v["stage"]] += 1

        return {
            "total_models": total_models,
            "total_versions": total_versions,
            "by_stage": stage_counts,
        }

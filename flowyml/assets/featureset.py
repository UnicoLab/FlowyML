"""FeatureSet asset for feature engineering outputs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from flowyml.assets.base import Asset, AssetMetadata


@dataclass
class FeatureSetMetadata(AssetMetadata):
    """Metadata specific to FeatureSets."""

    feature_names: list[str] = field(default_factory=list)
    num_features: int = 0
    num_samples: int = 0
    feature_types: dict[str, str] = field(default_factory=dict)
    statistics: dict[str, dict[str, float]] = field(default_factory=dict)
    transformations: list[str] = field(default_factory=list)
    source_dataset: str | None = None


class FeatureSet(Asset):
    """Asset representing a set of engineered features.

    FeatureSets are created through feature engineering pipelines and contain
    transformed data ready for model training.

    Example:
        ```python
        from flowyml import FeatureSet

        # Create a feature set
        features = FeatureSet.create(
            data=feature_matrix,
            feature_names=["age_scaled", "income_log", "category_encoded"],
            num_samples=10000,
            transformations=["StandardScaler", "LogTransform", "OneHotEncoder"],
            source_dataset="customers_v1",
        )

        # Access feature information
        print(features.num_features)  # 3
        print(features.feature_names)
        print(features.statistics)
        ```
    """

    def __init__(
        self,
        name: str,
        data: Any = None,
        feature_names: list[str] | None = None,
        num_samples: int = 0,
        transformations: list[str] | None = None,
        source_dataset: str | None = None,
        **kwargs,
    ):
        """Initialize a FeatureSet.

        Args:
            name: Name of the feature set
            data: The feature matrix (DataFrame, array, etc.)
            feature_names: List of feature names
            num_samples: Number of samples in the feature set
            transformations: List of transformations applied
            source_dataset: Name of source dataset
            **kwargs: Additional metadata
        """
        # Initialize base asset
        metadata = FeatureSetMetadata(
            name=name,
            type="featureset",
            feature_names=feature_names or [],
            num_features=len(feature_names) if feature_names else 0,
            num_samples=num_samples,
            transformations=transformations or [],
            source_dataset=source_dataset,
            **kwargs,
        )

        super().__init__(name=name, type="featureset", metadata=metadata)
        self._data = data

        # Extract feature metadata if data provided
        if data is not None:
            self._extract_feature_metadata()

    def _extract_feature_metadata(self) -> None:
        """Extract feature metadata from data."""
        try:
            import pandas as pd

            if isinstance(self._data, pd.DataFrame):
                # Update feature names from DataFrame
                if not self.metadata.feature_names:
                    self.metadata.feature_names = self._data.columns.tolist()
                    self.metadata.num_features = len(self._data.columns)

                # Extract feature types
                self.metadata.feature_types = {col: str(dtype) for col, dtype in self._data.dtypes.items()}

                # Update num_samples
                if not self.metadata.num_samples:
                    self.metadata.num_samples = len(self._data)

                # Calculate statistics for numerical columns
                numerical_cols = self._data.select_dtypes(include=["number"]).columns
                for col in numerical_cols:
                    self.metadata.statistics[col] = {
                        "min": float(self._data[col].min()),
                        "max": float(self._data[col].max()),
                        "mean": float(self._data[col].mean()),
                        "std": float(self._data[col].std()),
                        "missing": int(self._data[col].isna().sum()),
                    }

        except ImportError:
            pass

        try:
            import numpy as np

            if isinstance(self._data, np.ndarray):
                # Update dimensions
                if self._data.ndim >= 2:
                    self.metadata.num_samples = self._data.shape[0]
                    self.metadata.num_features = self._data.shape[1]

                # Calculate statistics if numerical
                if np.issubdtype(self._data.dtype, np.number):
                    for i in range(min(self.metadata.num_features, 100)):  # Limit to 100 features
                        feature_name = (
                            self.metadata.feature_names[i] if i < len(self.metadata.feature_names) else f"feature_{i}"
                        )
                        self.metadata.statistics[feature_name] = {
                            "min": float(np.min(self._data[:, i])),
                            "max": float(np.max(self._data[:, i])),
                            "mean": float(np.mean(self._data[:, i])),
                            "std": float(np.std(self._data[:, i])),
                        }
        except ImportError:
            pass

    @property
    def data(self) -> Any:
        """Get the feature data."""
        return self._data

    @property
    def feature_names(self) -> list[str]:
        """Get feature names."""
        return self.metadata.feature_names

    @property
    def num_features(self) -> int:
        """Get number of features."""
        return self.metadata.num_features

    @property
    def num_samples(self) -> int:
        """Get number of samples."""
        return self.metadata.num_samples

    @property
    def feature_types(self) -> dict[str, str]:
        """Get feature types."""
        return self.metadata.feature_types

    @property
    def statistics(self) -> dict[str, dict[str, float]]:
        """Get feature statistics."""
        return self.metadata.statistics

    @property
    def transformations(self) -> list[str]:
        """Get list of transformations applied."""
        return self.metadata.transformations

    @property
    def source_dataset(self) -> str | None:
        """Get source dataset name."""
        return self.metadata.source_dataset

    @classmethod
    def create(
        cls,
        data: Any,
        name: str | None = None,
        feature_names: list[str] | None = None,
        transformations: list[str] | None = None,
        source_dataset: str | None = None,
        **kwargs,
    ) -> "FeatureSet":
        """Factory method to create a FeatureSet.

        Args:
            data: The feature matrix
            name: Name of the feature set (auto-generated if not provided)
            feature_names: List of feature names
            transformations: List of transformations applied
            source_dataset: Name of source dataset
            **kwargs: Additional metadata

        Returns:
            New FeatureSet instance
        """
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"features_{timestamp}"

        return cls(
            name=name,
            data=data,
            feature_names=feature_names,
            transformations=transformations,
            source_dataset=source_dataset,
            **kwargs,
        )

    def select_features(self, feature_names: list[str]) -> "FeatureSet":
        """Select a subset of features.

        Args:
            feature_names: List of feature names to select

        Returns:
            New FeatureSet with selected features
        """
        if self._data is None:
            raise ValueError("Cannot select features from FeatureSet without data")

        try:
            import pandas as pd

            if isinstance(self._data, pd.DataFrame):
                selected_data = self._data[feature_names]
                return FeatureSet.create(
                    data=selected_data,
                    name=f"{self.name}_selected",
                    feature_names=feature_names,
                    transformations=self.transformations,
                    source_dataset=self.name,
                )
        except ImportError:
            pass

        try:
            import numpy as np

            if isinstance(self._data, np.ndarray):
                # Map feature names to indices
                indices = [self.feature_names.index(fn) for fn in feature_names if fn in self.feature_names]
                selected_data = self._data[:, indices]
                return FeatureSet.create(
                    data=selected_data,
                    name=f"{self.name}_selected",
                    feature_names=feature_names,
                    transformations=self.transformations,
                    source_dataset=self.name,
                )
        except ImportError:
            pass

        raise TypeError("Unsupported data type for feature selection")

    def get_feature_statistics(self, feature_name: str) -> dict[str, float] | None:
        """Get statistics for a specific feature.

        Args:
            feature_name: Name of the feature

        Returns:
            Dictionary of statistics or None if not found
        """
        return self.statistics.get(feature_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert FeatureSet to dictionary.

        Returns:
            Dictionary representation (excluding data)
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "feature_names": self.feature_names,
            "num_features": self.num_features,
            "num_samples": self.num_samples,
            "feature_types": self.feature_types,
            "statistics": self.statistics,
            "transformations": self.transformations,
            "source_dataset": self.source_dataset,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "properties": self.properties,
        }

    def __repr__(self) -> str:
        return f"FeatureSet(name='{self.name}', num_features={self.num_features}, num_samples={self.num_samples})"

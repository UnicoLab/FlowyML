"""Dataset Asset - Represents ML datasets with automatic statistics extraction."""

from typing import Any
import logging

from flowyml.assets.base import Asset

logger = logging.getLogger(__name__)


class DatasetStats:
    """Utility class for computing dataset statistics from various data formats."""

    @staticmethod
    def detect_data_type(data: Any) -> str:
        """Detect the type of data structure.

        Returns one of: 'pandas', 'numpy', 'tensorflow', 'torch', 'dict', 'list', 'unknown'
        """
        if data is None:
            return "unknown"

        # Check class name to avoid importing heavy libraries
        type_name = type(data).__name__
        module_name = type(data).__module__

        # Pandas DataFrame
        if type_name == "DataFrame" and "pandas" in module_name:
            return "pandas"

        # Numpy array
        if type_name == "ndarray" and "numpy" in module_name:
            return "numpy"

        # TensorFlow Dataset
        if "tensorflow" in module_name or "tf" in module_name:
            if "Dataset" in type_name or "dataset" in module_name:
                return "tensorflow"

        # PyTorch Dataset/DataLoader
        if "torch" in module_name:
            if "Dataset" in type_name or "DataLoader" in type_name:
                return "torch"

        # Dictionary (common format for features/target)
        if isinstance(data, dict):
            return "dict"

        # List/Tuple
        if isinstance(data, (list, tuple)):
            return "list"

        return "unknown"

    @staticmethod
    def compute_numeric_stats(values: list) -> dict[str, Any]:
        """Compute statistics for a numeric column."""
        try:
            # Filter to numeric values only
            numeric_vals = [v for v in values if isinstance(v, (int, float)) and v == v]  # v == v filters NaN
            if not numeric_vals:
                return {}

            n = len(numeric_vals)
            sorted_vals = sorted(numeric_vals)

            mean = sum(numeric_vals) / n
            variance = sum((x - mean) ** 2 for x in numeric_vals) / n
            std = variance**0.5

            # Median
            mid = n // 2
            median = sorted_vals[mid] if n % 2 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2

            return {
                "mean": round(mean, 6),
                "std": round(std, 6),
                "min": round(min(numeric_vals), 6),
                "max": round(max(numeric_vals), 6),
                "median": round(median, 6),
                "count": n,
                "unique": len(set(numeric_vals)),
                "dtype": "numeric",
            }
        except Exception as e:
            logger.debug(f"Could not compute numeric stats: {e}")
            return {}

    @staticmethod
    def compute_categorical_stats(values: list) -> dict[str, Any]:
        """Compute statistics for a categorical column."""
        try:
            n = len(values)
            unique_vals = {str(v) for v in values if v is not None}

            return {
                "count": n,
                "unique": len(unique_vals),
                "dtype": "categorical",
                "top_values": list(unique_vals)[:5],  # Sample of unique values
            }
        except Exception as e:
            logger.debug(f"Could not compute categorical stats: {e}")
            return {}

    @staticmethod
    def extract_from_pandas(df: Any) -> dict[str, Any]:
        """Extract statistics from a pandas DataFrame."""
        try:
            columns = list(df.columns)
            n_samples = len(df)

            # Compute per-column stats
            column_stats = {}
            for col in columns:
                col_data = df[col].tolist()
                # Check if numeric
                if df[col].dtype.kind in ("i", "f", "u"):  # int, float, unsigned
                    column_stats[col] = DatasetStats.compute_numeric_stats(col_data)
                else:
                    column_stats[col] = DatasetStats.compute_categorical_stats(col_data)

            # Detect target column (common naming conventions)
            target_candidates = ["target", "label", "y", "class", "output"]
            target_col = next((c for c in columns if c.lower() in target_candidates), None)
            feature_cols = [c for c in columns if c != target_col] if target_col else columns

            return {
                "samples": n_samples,
                "num_features": len(feature_cols),
                "feature_columns": feature_cols,
                "label_column": target_col,
                "columns": columns,
                "column_stats": column_stats,
                "framework": "pandas",
                "_auto_extracted": True,
            }
        except Exception as e:
            logger.debug(f"Could not extract pandas stats: {e}")
            return {}

    @staticmethod
    def extract_from_numpy(arr: Any) -> dict[str, Any]:
        """Extract statistics from a numpy array."""
        try:
            shape = arr.shape
            dtype = str(arr.dtype)

            result = {
                "shape": list(shape),
                "dtype": dtype,
                "samples": shape[0] if len(shape) > 0 else 1,
                "num_features": shape[1] if len(shape) > 1 else 1,
                "framework": "numpy",
                "_auto_extracted": True,
            }

            # Compute stats if 1D or 2D numeric
            if arr.dtype.kind in ("i", "f", "u") and len(shape) <= 2:
                flat_data = arr.flatten().tolist()
                stats = DatasetStats.compute_numeric_stats(flat_data)
                result["stats"] = stats

            return result
        except Exception as e:
            logger.debug(f"Could not extract numpy stats: {e}")
            return {}

    @staticmethod
    def extract_from_dict(data: dict) -> dict[str, Any]:
        """Extract statistics from a dict of arrays (common format)."""
        try:
            # Check if it's a features/target format
            if "features" in data and isinstance(data["features"], dict):
                features = data["features"]
                target = data.get("target", [])

                columns = list(features.keys())
                if target:
                    columns.append("target")

                # Get sample count from first feature
                first_key = next(iter(features.keys()))
                n_samples = len(features[first_key]) if features else 0

                # Compute per-column stats
                column_stats = {}
                for col, values in features.items():
                    if values and isinstance(values[0], (int, float)):
                        column_stats[col] = DatasetStats.compute_numeric_stats(values)
                    else:
                        column_stats[col] = DatasetStats.compute_categorical_stats(values)

                if target:
                    if target and isinstance(target[0], (int, float)):
                        column_stats["target"] = DatasetStats.compute_numeric_stats(target)
                    else:
                        column_stats["target"] = DatasetStats.compute_categorical_stats(target)

                return {
                    "samples": n_samples,
                    "num_features": len(features),
                    "feature_columns": list(features.keys()),
                    "label_column": "target" if target else None,
                    "columns": columns,
                    "column_stats": column_stats,
                    "framework": "dict",
                    "_auto_extracted": True,
                }

            # Generic dict of arrays
            columns = list(data.keys())
            n_samples = 0
            column_stats = {}

            for col, values in data.items():
                if isinstance(values, (list, tuple)):
                    n_samples = max(n_samples, len(values))
                    if values and isinstance(values[0], (int, float)):
                        column_stats[col] = DatasetStats.compute_numeric_stats(list(values))
                    else:
                        column_stats[col] = DatasetStats.compute_categorical_stats(list(values))

            # Detect target column
            target_candidates = ["target", "label", "y", "class", "output"]
            target_col = next((c for c in columns if c.lower() in target_candidates), None)
            feature_cols = [c for c in columns if c != target_col] if target_col else columns

            return {
                "samples": n_samples,
                "num_features": len(feature_cols),
                "feature_columns": feature_cols,
                "label_column": target_col,
                "columns": columns,
                "column_stats": column_stats,
                "framework": "dict",
                "_auto_extracted": True,
            }
        except Exception as e:
            logger.debug(f"Could not extract dict stats: {e}")
            return {}

    @staticmethod
    def extract_from_tensorflow(dataset: Any) -> dict[str, Any]:
        """Extract statistics from a TensorFlow dataset."""
        try:
            result = {
                "framework": "tensorflow",
                "_auto_extracted": True,
            }

            # Get cardinality if available
            if hasattr(dataset, "cardinality"):
                card = dataset.cardinality()
                if hasattr(card, "numpy"):
                    card = card.numpy()
                result["cardinality"] = int(card) if card >= 0 else "unknown"
                result["samples"] = int(card) if card >= 0 else None

            # Get element spec if available
            if hasattr(dataset, "element_spec"):
                spec = dataset.element_spec

                def spec_to_dict(s: Any) -> dict | str:
                    if hasattr(s, "shape") and hasattr(s, "dtype"):
                        return {"shape": str(s.shape), "dtype": str(s.dtype)}
                    if isinstance(s, dict):
                        return {k: spec_to_dict(v) for k, v in s.items()}
                    if isinstance(s, (tuple, list)):
                        return [spec_to_dict(x) for x in s]
                    return str(s)

                result["element_spec"] = spec_to_dict(spec)

            return result
        except Exception as e:
            logger.debug(f"Could not extract tensorflow stats: {e}")
            return {"framework": "tensorflow", "_auto_extracted": True}

    @staticmethod
    def extract_stats(data: Any) -> dict[str, Any]:
        """Auto-detect data type and extract statistics."""
        data_type = DatasetStats.detect_data_type(data)

        if data_type == "pandas":
            return DatasetStats.extract_from_pandas(data)
        elif data_type == "numpy":
            return DatasetStats.extract_from_numpy(data)
        elif data_type == "dict":
            return DatasetStats.extract_from_dict(data)
        elif data_type == "tensorflow":
            return DatasetStats.extract_from_tensorflow(data)
        elif data_type == "list":
            # Try to convert list to dict format
            if data and isinstance(data[0], dict):
                # List of dicts -> convert to dict of lists
                keys = data[0].keys()
                dict_data = {k: [row.get(k) for row in data] for k in keys}
                return DatasetStats.extract_from_dict(dict_data)
            return {"samples": len(data), "framework": "list", "_auto_extracted": True}

        return {"_auto_extracted": False}


class Dataset(Asset):
    """Dataset asset with automatic schema detection and statistics extraction.

    The Dataset class automatically extracts statistics and metadata from various
    data formats, reducing boilerplate code and improving UX.

    Supported formats:
        - pandas DataFrame: Auto-extracts columns, dtypes, statistics
        - numpy array: Auto-extracts shape, dtype, statistics
        - dict: Auto-extracts features/target structure, column stats
        - TensorFlow Dataset: Auto-extracts element_spec, cardinality
        - List of dicts: Converts to dict format and extracts stats

    Example:
        >>> # Minimal usage - stats are extracted automatically!
        >>> import pandas as pd
        >>> df = pd.read_csv("data.csv")
        >>> dataset = Dataset.create(data=df, name="my_dataset")
        >>> print(dataset.num_samples)  # Auto-extracted
        >>> print(dataset.feature_columns)  # Auto-detected

        >>> # With dict format
        >>> data = {"features": {"x": [1, 2, 3], "y": [4, 5, 6]}, "target": [0, 1, 0]}
        >>> dataset = Dataset.create(data=data, name="my_dataset")
        >>> # All stats computed automatically!
    """

    def __init__(
        self,
        name: str,
        version: str | None = None,
        data: Any = None,
        schema: Any | None = None,
        location: str | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
        auto_extract_stats: bool = True,
    ):
        """Initialize Dataset with automatic statistics extraction.

        Args:
            name: Dataset name
            version: Version string
            data: The actual data (DataFrame, array, dict, etc.)
            schema: Optional schema definition
            location: Storage location/path
            parent: Parent asset for lineage
            tags: Metadata tags
            properties: Additional properties (merged with auto-extracted)
            auto_extract_stats: Whether to automatically extract statistics
        """
        # Initialize properties dict
        final_properties = properties.copy() if properties else {}

        # Auto-extract statistics if enabled and data is provided
        if auto_extract_stats and data is not None:
            extracted = DatasetStats.extract_stats(data)
            # Merge extracted stats with user-provided properties
            # User properties take precedence
            for key, value in extracted.items():
                if key not in final_properties:
                    final_properties[key] = value

        super().__init__(
            name=name,
            version=version,
            data=data,
            parent=parent,
            tags=tags,
            properties=final_properties,
        )

        self.schema = schema
        self.location = location

        # Add dataset-specific properties
        if schema:
            self.metadata.properties["schema"] = str(schema)
        if location:
            self.metadata.properties["location"] = location

    @classmethod
    def create(
        cls,
        data: Any,
        name: str,
        version: str | None = None,
        schema: Any | None = None,
        location: str | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
        auto_extract_stats: bool = True,
        **kwargs: Any,
    ) -> "Dataset":
        """Create a Dataset with automatic statistics extraction.

        This is the preferred way to create Dataset objects. Statistics are
        automatically extracted from the data, reducing boilerplate code.

        Args:
            data: The actual data (DataFrame, array, dict, etc.)
            name: Dataset name
            version: Version string (optional)
            schema: Optional schema definition
            location: Storage location/path
            parent: Parent asset for lineage
            tags: Metadata tags
            properties: Additional properties (merged with auto-extracted)
            auto_extract_stats: Whether to automatically extract statistics
            **kwargs: Additional properties to store

        Returns:
            Dataset instance with auto-extracted statistics

        Example:
            >>> df = pd.read_csv("data.csv")
            >>> dataset = Dataset.create(data=df, name="my_data", source="data.csv")
            >>> # Stats are automatically extracted!
        """
        # Merge kwargs into properties
        final_props = properties.copy() if properties else {}
        for key, value in kwargs.items():
            if key not in final_props:
                final_props[key] = value

        return cls(
            name=name,
            version=version,
            data=data,
            schema=schema,
            location=location,
            parent=parent,
            tags=tags,
            properties=final_props,
            auto_extract_stats=auto_extract_stats,
        )

    @classmethod
    def from_csv(
        cls,
        path: str,
        name: str | None = None,
        **kwargs: Any,
    ) -> "Dataset":
        """Load a Dataset from a CSV file with automatic statistics.

        Args:
            path: Path to CSV file
            name: Dataset name (defaults to filename)
            **kwargs: Additional properties

        Returns:
            Dataset with auto-extracted statistics
        """
        try:
            import pandas as pd

            df = pd.read_csv(path)
            dataset_name = name or path.split("/")[-1].replace(".csv", "")

            return cls.create(
                data=df,
                name=dataset_name,
                location=path,
                properties={"source": path, "format": "csv"},
                **kwargs,
            )
        except ImportError:
            raise ImportError("pandas is required for from_csv(). Install with: pip install pandas")

    @classmethod
    def from_parquet(
        cls,
        path: str,
        name: str | None = None,
        **kwargs: Any,
    ) -> "Dataset":
        """Load a Dataset from a Parquet file with automatic statistics.

        Args:
            path: Path to Parquet file
            name: Dataset name (defaults to filename)
            **kwargs: Additional properties

        Returns:
            Dataset with auto-extracted statistics
        """
        try:
            import pandas as pd

            df = pd.read_parquet(path)
            dataset_name = name or path.split("/")[-1].replace(".parquet", "")

            return cls.create(
                data=df,
                name=dataset_name,
                location=path,
                properties={"source": path, "format": "parquet"},
                **kwargs,
            )
        except ImportError:
            raise ImportError("pandas and pyarrow are required for from_parquet()")

    @property
    def size(self) -> int | None:
        """Get dataset size if available."""
        return self.metadata.properties.get("size")

    @property
    def num_samples(self) -> int | None:
        """Get number of samples (auto-extracted or user-provided)."""
        return (
            self.metadata.properties.get("samples")
            or self.metadata.properties.get("num_samples")
            or self.metadata.properties.get("cardinality")
        )

    @property
    def num_features(self) -> int | None:
        """Get number of features (auto-extracted or user-provided)."""
        return self.metadata.properties.get("num_features")

    @property
    def feature_columns(self) -> list[str] | None:
        """Get list of feature column names (auto-extracted or user-provided)."""
        return self.metadata.properties.get("feature_columns")

    @property
    def label_column(self) -> str | None:
        """Get the label/target column name (auto-detected or user-provided)."""
        return self.metadata.properties.get("label_column")

    @property
    def columns(self) -> list[str] | None:
        """Get all column names (auto-extracted or user-provided)."""
        return self.metadata.properties.get("columns")

    @property
    def column_stats(self) -> dict[str, dict] | None:
        """Get per-column statistics (auto-extracted)."""
        return self.metadata.properties.get("column_stats")

    @property
    def framework(self) -> str | None:
        """Get the data framework/format (auto-detected)."""
        return self.metadata.properties.get("framework")

    def get_column_stat(self, column: str, stat: str) -> Any:
        """Get a specific statistic for a column.

        Args:
            column: Column name
            stat: Statistic name (mean, std, min, max, median, count, unique)

        Returns:
            The statistic value or None
        """
        stats = self.column_stats
        if stats and column in stats:
            return stats[column].get(stat)
        return None

    def validate_schema(self) -> bool:
        """Validate data against schema (placeholder)."""
        if self.schema is None or self.data is None:
            return True
        # Schema validation would go here
        return True

    def split(
        self,
        train_ratio: float = 0.8,
        name_prefix: str | None = None,
        random_state: int | None = 42,
    ) -> tuple["Dataset", "Dataset"]:
        """Split dataset into train/test with auto-extracted statistics.

        Args:
            train_ratio: Ratio for training split
            name_prefix: Prefix for split dataset names
            random_state: Random seed for reproducibility

        Returns:
            Tuple of (train_dataset, test_dataset)
        """
        prefix = name_prefix or self.name

        # Try to split based on data type
        data_type = DatasetStats.detect_data_type(self.data)

        if data_type == "pandas":
            try:
                df = self.data.sample(frac=1, random_state=random_state).reset_index(drop=True)
                train_size = int(len(df) * train_ratio)
                train_data = df[:train_size]
                test_data = df[train_size:]
            except Exception:
                train_data = self.data
                test_data = self.data
        elif data_type == "dict" and "features" in self.data:
            # Split dict format
            features = self.data["features"]
            target = self.data.get("target", [])
            first_key = next(iter(features.keys()))
            n_samples = len(features[first_key])
            train_size = int(n_samples * train_ratio)

            train_features = {k: v[:train_size] for k, v in features.items()}
            test_features = {k: v[train_size:] for k, v in features.items()}

            train_data = {"features": train_features, "target": target[:train_size] if target else []}
            test_data = {"features": test_features, "target": target[train_size:] if target else []}
        else:
            # Fallback - no actual splitting
            train_data = self.data
            test_data = self.data

        train_dataset = Dataset(
            name=f"{prefix}_train",
            version=self.version,
            data=train_data,
            schema=self.schema,
            parent=self,
            tags={**self.metadata.tags, "split": "train"},
        )

        test_dataset = Dataset(
            name=f"{prefix}_test",
            version=self.version,
            data=test_data,
            schema=self.schema,
            parent=self,
            tags={**self.metadata.tags, "split": "test"},
        )

        return train_dataset, test_dataset

    def __repr__(self) -> str:
        """String representation with key stats."""
        parts = [f"Dataset(name='{self.name}'"]
        if self.num_samples:
            parts.append(f"samples={self.num_samples}")
        if self.num_features:
            parts.append(f"features={self.num_features}")
        if self.framework:
            parts.append(f"framework='{self.framework}'")
        return ", ".join(parts) + ")"

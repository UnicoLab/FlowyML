"""Pandas materializer for DataFrame serialization."""

import json
from pathlib import Path
from typing import Any

from uniflow.storage.materializers.base import BaseMaterializer, register_materializer

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


if PANDAS_AVAILABLE:

    class PandasMaterializer(BaseMaterializer):
        """Materializer for Pandas DataFrames and Series."""

        def save(self, obj: Any, path: Path) -> None:
            """Save Pandas object to path.

            Args:
                obj: Pandas DataFrame or Series
                path: Directory path where object should be saved
            """
            path.mkdir(parents=True, exist_ok=True)

            if isinstance(obj, pd.DataFrame):
                # Save DataFrame as parquet (efficient) or CSV (fallback)
                try:
                    data_path = path / "data.parquet"
                    obj.to_parquet(data_path, index=True)
                    format_used = "parquet"
                except Exception:
                    data_path = path / "data.csv"
                    obj.to_csv(data_path, index=True)
                    format_used = "csv"

                # Save metadata
                metadata = {
                    "type": "pandas_dataframe",
                    "format": format_used,
                    "shape": list(obj.shape),
                    "columns": obj.columns.tolist(),
                    "dtypes": {col: str(dtype) for col, dtype in obj.dtypes.items()},
                    "index_name": obj.index.name,
                }

                with open(path / "metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)

            elif isinstance(obj, pd.Series):
                # Save Series
                try:
                    data_path = path / "data.parquet"
                    obj.to_frame().to_parquet(data_path, index=True)
                    format_used = "parquet"
                except Exception:
                    data_path = path / "data.csv"
                    obj.to_csv(data_path, index=True, header=True)
                    format_used = "csv"

                metadata = {
                    "type": "pandas_series",
                    "format": format_used,
                    "shape": len(obj),
                    "name": obj.name,
                    "dtype": str(obj.dtype),
                    "index_name": obj.index.name,
                }

                with open(path / "metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)

        def load(self, path: Path) -> Any:
            """Load Pandas object from path.

            Args:
                path: Directory path from which to load object

            Returns:
                Loaded Pandas DataFrame or Series
            """
            # Load metadata
            metadata_path = path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            obj_type = metadata.get("type", "pandas_dataframe")
            format_used = metadata.get("format", "parquet")

            if obj_type == "pandas_dataframe":
                if format_used == "parquet":
                    data_path = path / "data.parquet"
                    return pd.read_parquet(data_path)
                else:
                    data_path = path / "data.csv"
                    return pd.read_csv(data_path, index_col=0)

            elif obj_type == "pandas_series":
                if format_used == "parquet":
                    data_path = path / "data.parquet"
                    df = pd.read_parquet(data_path)
                    return df.iloc[:, 0]
                else:
                    data_path = path / "data.csv"
                    series = pd.read_csv(data_path, index_col=0)
                    if isinstance(series, pd.DataFrame):
                        series = series.iloc[:, 0]
                    return series

            else:
                raise ValueError(f"Unknown Pandas object type: {obj_type}")

        @classmethod
        def supported_types(cls) -> list[type]:
            """Return Pandas types supported by this materializer."""
            return [pd.DataFrame, pd.Series]

    # Auto-register
    register_materializer(PandasMaterializer)

else:
    # Placeholder when Pandas not available
    class PandasMaterializer(BaseMaterializer):
        """Placeholder materializer when Pandas is not installed."""

        def save(self, obj: Any, path: Path) -> None:
            raise ImportError("Pandas is not installed. Install with: pip install pandas")

        def load(self, path: Path) -> Any:
            raise ImportError("Pandas is not installed. Install with: pip install pandas")

        @classmethod
        def supported_types(cls) -> list[type]:
            return []

"""FlowyML Evaluations — EvalDataset Asset.

First-class evaluation dataset asset with versioning, tagging, and lineage.
Supports both classical ML and GenAI data formats.
"""

from typing import Any
from flowyml.assets.base import Asset


class EvalDataset(Asset):
    """Versioned evaluation dataset asset.

    A first-class FlowyML asset for managing evaluation data. Extends Asset
    to inherit versioning, tagging, lineage tracking, and persistence.

    Supports two data formats:

    **Classical ML format** — predictions and targets:
        data = {
            "predictions": [0, 1, 1, 0, 1],
            "targets": [0, 1, 0, 0, 1],
        }
        or with features for analysis:
        data = {
            "predictions": [0, 1, 1, 0, 1],
            "targets": [0, 1, 0, 0, 1],
            "features": {"age": [25, 30], "income": [50000, 60000]},
        }

    **GenAI format** — list of dictionaries with inputs/outputs:
        data = [
            {"inputs": "What is ML?", "outputs": "ML is...", "expected": "...", "context": [...]},
            {"inputs": "Explain AI", "outputs": "AI is...", "expected": "..."},
        ]

    Attributes:
        name: Dataset name
        data: The evaluation data (dict for classical ML, list for GenAI)
        data_format: 'classical_ml' or 'genai' (auto-detected)
        num_examples: Number of examples in the dataset
        column_names: List of available fields/columns

    Example:
        >>> # Classical ML dataset
        >>> eval_ds = EvalDataset(
        ...     name="iris_test_v1",
        ...     data={"predictions": [0, 1, 2, 1], "targets": [0, 1, 1, 1]},
        ...     tags={"split": "test", "model": "random_forest"},
        ... )

        >>> # GenAI dataset
        >>> eval_ds = EvalDataset.create_genai(
        ...     name="rag_golden_set",
        ...     examples=[
        ...         {"inputs": "What is X?", "outputs": "X is Y", "context": ["X=Y"]},
        ...     ],
        ...     tags={"domain": "medical"},
        ... )
    """

    def __init__(
        self,
        name: str,
        data: dict[str, Any] | list[dict[str, Any]] | None = None,
        version: str | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            name=name,
            version=version,
            data=data,
            parent=parent,
            tags=tags,
            properties=properties,
        )

        # Auto-detect format
        self._data_format = self._detect_format()
        self.metadata.properties["data_format"] = self._data_format
        self.metadata.properties["num_examples"] = self.num_examples
        self.metadata.properties["asset_type"] = "EvalDataset"

    def _detect_format(self) -> str:
        """Auto-detect data format."""
        if isinstance(self.data, list):
            return "genai"
        elif isinstance(self.data, dict):
            if "predictions" in self.data or "targets" in self.data:
                return "classical_ml"
            return "dict"
        return "unknown"

    @property
    def data_format(self) -> str:
        """Get the data format ('classical_ml', 'genai', or 'dict')."""
        return self._data_format

    @property
    def num_examples(self) -> int:
        """Get the number of examples in the dataset."""
        if isinstance(self.data, list):
            return len(self.data)
        elif isinstance(self.data, dict):
            # Use the first array-like value to determine count
            for v in self.data.values():
                if isinstance(v, (list, tuple)):
                    return len(v)
                try:
                    return len(v)
                except TypeError:
                    continue
        return 0

    @property
    def column_names(self) -> list[str]:
        """Get the available field/column names."""
        if isinstance(self.data, list) and len(self.data) > 0:
            return list(self.data[0].keys())
        elif isinstance(self.data, dict):
            return list(self.data.keys())
        return []

    @property
    def predictions(self) -> Any:
        """Get predictions (classical ML format)."""
        if isinstance(self.data, dict):
            return self.data.get("predictions")
        return None

    @property
    def targets(self) -> Any:
        """Get targets/ground truth (classical ML format)."""
        if isinstance(self.data, dict):
            return self.data.get("targets")
        return None

    def to_scorer_args(self) -> list[dict[str, Any]]:
        """Convert dataset to scorer-compatible argument dicts.

        Returns a list of dicts, each suitable as kwargs to Scorer.score().

        For classical ML: returns [{"predictions": [...], "targets": [...]}]
        For GenAI: returns [{"inputs": ..., "outputs": ..., "context": ...}, ...]
        """
        if self._data_format == "classical_ml":
            # Classical ML: single call with full arrays
            return [{"predictions": self.predictions, "targets": self.targets}]
        elif self._data_format == "genai":
            # GenAI: one call per example
            return list(self.data) if isinstance(self.data, list) else []
        elif isinstance(self.data, list):
            return list(self.data)
        return []

    def split(self, ratio: float = 0.5, seed: int = 42) -> tuple["EvalDataset", "EvalDataset"]:
        """Split dataset into two parts.

        Args:
            ratio: Fraction of data in the first split
            seed: Random seed for reproducibility

        Returns:
            Tuple of two EvalDatasets
        """
        import random

        rng = random.Random(seed)

        if isinstance(self.data, list):
            data = list(self.data)
            rng.shuffle(data)
            n = int(len(data) * ratio)
            return (
                EvalDataset(name=f"{self.name}_split_a", data=data[:n], parent=self, tags=self.tags),
                EvalDataset(name=f"{self.name}_split_b", data=data[n:], parent=self, tags=self.tags),
            )
        elif isinstance(self.data, dict):
            # Get the length from the first list-like value
            length = self.num_examples
            indices = list(range(length))
            rng.shuffle(indices)
            n = int(length * ratio)
            idx_a, idx_b = set(indices[:n]), set(indices[n:])

            data_a, data_b = {}, {}
            for k, v in self.data.items():
                if isinstance(v, list):
                    data_a[k] = [v[i] for i in range(length) if i in idx_a]
                    data_b[k] = [v[i] for i in range(length) if i in idx_b]
                else:
                    data_a[k] = v
                    data_b[k] = v

            return (
                EvalDataset(name=f"{self.name}_split_a", data=data_a, parent=self, tags=self.tags),
                EvalDataset(name=f"{self.name}_split_b", data=data_b, parent=self, tags=self.tags),
            )
        raise ValueError("Cannot split dataset with unknown format")

    def sample(self, n: int, seed: int = 42) -> "EvalDataset":
        """Sample n examples from the dataset.

        Args:
            n: Number of examples to sample
            seed: Random seed

        Returns:
            New EvalDataset with sampled data
        """
        import random

        rng = random.Random(seed)

        if isinstance(self.data, list):
            sampled = rng.sample(self.data, min(n, len(self.data)))
            return EvalDataset(name=f"{self.name}_sample", data=sampled, parent=self, tags=self.tags)
        elif isinstance(self.data, dict):
            length = self.num_examples
            indices = rng.sample(range(length), min(n, length))
            idx_set = set(indices)
            sampled = {}
            for k, v in self.data.items():
                if isinstance(v, list):
                    sampled[k] = [v[i] for i in range(length) if i in idx_set]
                else:
                    sampled[k] = v
            return EvalDataset(name=f"{self.name}_sample", data=sampled, parent=self, tags=self.tags)
        raise ValueError("Cannot sample from dataset with unknown format")

    @classmethod
    def create_genai(
        cls,
        name: str,
        examples: list[dict[str, Any]],
        version: str | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> "EvalDataset":
        """Factory to create a GenAI evaluation dataset.

        Args:
            name: Dataset name
            examples: List of {inputs, outputs, expected, context} dicts
            version: Version string
            tags: Tags for categorization
            **kwargs: Additional keyword arguments passed to constructor

        Returns:
            EvalDataset configured for GenAI evaluation
        """
        return cls(name=name, data=examples, version=version, tags=tags, **kwargs)

    @classmethod
    def create_classical(
        cls,
        name: str,
        predictions: Any,
        targets: Any,
        features: dict[str, Any] | None = None,
        version: str | None = None,
        tags: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> "EvalDataset":
        """Factory to create a classical ML evaluation dataset.

        Args:
            name: Dataset name
            predictions: Model predictions
            targets: Ground truth labels
            features: Optional feature data for analysis
            version: Version string
            tags: Tags for categorization
            **kwargs: Additional keyword arguments passed to constructor

        Returns:
            EvalDataset configured for classical ML evaluation
        """
        data = {"predictions": list(predictions), "targets": list(targets)}
        if features:
            data["features"] = features
        return cls(name=name, data=data, version=version, tags=tags, **kwargs)

    @classmethod
    def from_csv(
        cls,
        path: str,
        name: str | None = None,
        prediction_col: str = "prediction",
        target_col: str = "target",
        **kwargs: Any,
    ) -> "EvalDataset":
        """Load evaluation dataset from CSV.

        Args:
            path: Path to CSV file
            name: Dataset name (defaults to filename)
            prediction_col: Column name for predictions
            target_col: Column name for targets
            **kwargs: Additional keyword arguments passed to constructor

        Returns:
            EvalDataset with data from CSV
        """
        import csv
        from pathlib import Path

        file_path = Path(path)
        ds_name = name or file_path.stem

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if prediction_col in rows[0] and target_col in rows[0]:
            # Classical ML format
            predictions = []
            targets = []
            for row in rows:
                try:
                    predictions.append(float(row[prediction_col]))
                    targets.append(float(row[target_col]))
                except (ValueError, KeyError):
                    predictions.append(row.get(prediction_col))
                    targets.append(row.get(target_col))
            return cls.create_classical(ds_name, predictions, targets, **kwargs)
        else:
            # GenAI format — treat each row as an example
            return cls.create_genai(ds_name, rows, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary including eval-specific metadata."""
        base = super().to_dict()
        base["eval_metadata"] = {
            "data_format": self._data_format,
            "num_examples": self.num_examples,
            "column_names": self.column_names,
        }
        return base

    def __repr__(self) -> str:
        return (
            f"EvalDataset(name='{self.name}', format='{self._data_format}', "
            f"n={self.num_examples}, version='{self.version}')"
        )

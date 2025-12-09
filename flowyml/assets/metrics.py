"""Metrics Asset - Represents experiment metrics and evaluation results."""

from typing import Any
from flowyml.assets.base import Asset


class Metrics(Asset):
    """Metrics asset for experiment tracking.

    Example:
        >>> metrics = Metrics(name="training_metrics", data={"accuracy": 0.95, "loss": 0.05, "f1_score": 0.93})
    """

    def __init__(
        self,
        name: str,
        version: str | None = None,
        data: dict[str, Any] | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
        **metrics,
    ):
        # Merge data and kwargs metrics
        all_metrics = data or {}
        all_metrics.update(metrics)

        super().__init__(
            name=name,
            version=version,
            data=all_metrics,
            parent=parent,
            tags=tags,
            properties=properties,
        )

        # Store metrics in properties for easy access
        self.metadata.properties.update(all_metrics)

    def get_metric(self, name: str, default: Any = None) -> Any:
        """Get a specific metric value."""
        if self.data and name in self.data:
            return self.data[name]
        return self.metadata.properties.get(name, default)

    def add_metric(self, name: str, value: Any) -> None:
        """Add a new metric."""
        if self.data is None:
            self.data = {}
        self.data[name] = value
        self.metadata.properties[name] = value

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics."""
        return self.data or {}

    def compare_with(self, other: "Metrics") -> dict[str, dict[str, Any]]:
        """Compare metrics with another Metrics asset.

        Returns:
            Dictionary with comparison results
        """
        self_metrics = self.get_all_metrics()
        other_metrics = other.get_all_metrics()

        comparison = {}
        all_keys = set(self_metrics.keys()) | set(other_metrics.keys())

        for key in all_keys:
            self_val = self_metrics.get(key)
            other_val = other_metrics.get(key)

            comparison[key] = {
                "self": self_val,
                "other": other_val,
                "diff": self_val - other_val
                if (
                    self_val is not None
                    and other_val is not None
                    and isinstance(self_val, (int, float))
                    and isinstance(other_val, (int, float))
                )
                else None,
            }

        return comparison

    @classmethod
    def create(
        cls,
        name: str | None = None,
        version: str | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        **kwargs,
    ) -> "Metrics":
        """Factory method to create metrics.

        Supports multiple ways to provide metrics:
        1. As keyword arguments: Metrics.create(accuracy=0.95, loss=0.05)
        2. As a dict: Metrics.create(metrics={"accuracy": 0.95, "loss": 0.05})
        3. Mixed: Metrics.create(metrics={"accuracy": 0.95}, loss=0.05)

        Args:
            name: Name of the metrics asset
            version: Version string
            parent: Parent asset for lineage
            tags: Tags dictionary (or use metadata for convenience)
            properties: Properties dictionary
            metadata: Metadata dictionary (merged into tags and properties)
            metrics: Metrics as a dictionary (alternative to **kwargs)
            **kwargs: Additional metrics as keyword arguments

        Example:
            >>> # Using keyword arguments
            >>> metrics = Metrics.create(accuracy=0.95, loss=0.05, training_time="2h 15m")

            >>> # Using metrics dict
            >>> metrics = Metrics.create(
            ...     name="example_metrics",
            ...     metrics={"test_accuracy": 0.93, "test_loss": 0.07},
            ...     metadata={"source": "example"},
            ... )
        """
        # Merge metrics dict with kwargs
        all_metrics = {}
        if metrics:
            all_metrics.update(metrics)
        all_metrics.update(kwargs)

        # Handle metadata - merge into tags and properties
        final_tags = tags or {}
        final_properties = properties or {}
        if metadata:
            # If metadata contains string values, treat as tags
            # Otherwise, merge into properties
            for key, value in metadata.items():
                if isinstance(value, str):
                    final_tags[key] = value
                else:
                    final_properties[key] = value

        return cls(
            name=name or "metrics",
            version=version,
            data=all_metrics if all_metrics else None,
            parent=parent,
            tags=final_tags,
            properties=final_properties,
        )

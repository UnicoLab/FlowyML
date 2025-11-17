"""
Metrics Asset - Represents experiment metrics and evaluation results.
"""

from typing import Any, Dict, Optional
from flowy.assets.base import Asset


class Metrics(Asset):
    """
    Metrics asset for experiment tracking.
    
    Example:
        >>> metrics = Metrics(
        ...     name="training_metrics",
        ...     data={
        ...         'accuracy': 0.95,
        ...         'loss': 0.05,
        ...         'f1_score': 0.93
        ...     }
        ... )
    """
    
    def __init__(
        self,
        name: str,
        version: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        parent: Optional[Asset] = None,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        **metrics
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
            properties=properties
        )
        
        # Store metrics in properties for easy access
        self.metadata.properties.update(all_metrics)
    
    def get_metric(self, name: str, default: Any = None) -> Any:
        """Get a specific metric value."""
        if self.data and name in self.data:
            return self.data[name]
        return self.metadata.properties.get(name, default)
    
    def add_metric(self, name: str, value: Any):
        """Add a new metric."""
        if self.data is None:
            self.data = {}
        self.data[name] = value
        self.metadata.properties[name] = value
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        return self.data or {}
    
    def compare_with(self, other: "Metrics") -> Dict[str, Dict[str, Any]]:
        """
        Compare metrics with another Metrics asset.
        
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
                'self': self_val,
                'other': other_val,
                'diff': self_val - other_val if (
                    self_val is not None and other_val is not None and
                    isinstance(self_val, (int, float)) and isinstance(other_val, (int, float))
                ) else None
            }
        
        return comparison
    
    @classmethod
    def create(
        cls,
        name: Optional[str] = None,
        parent: Optional[Asset] = None,
        **metrics
    ) -> "Metrics":
        """
        Factory method to create metrics.
        
        Example:
            >>> metrics = Metrics.create(
            ...     accuracy=0.95,
            ...     loss=0.05,
            ...     training_time="2h 15m"
            ... )
        """
        return cls(
            name=name or "metrics",
            data=metrics,
            parent=parent
        )

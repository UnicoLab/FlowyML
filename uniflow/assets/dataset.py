"""
Dataset Asset - Represents ML datasets with schema validation.
"""

from typing import Any, Dict, Optional
from uniflow.assets.base import Asset


class Dataset(Asset):
    """
    Dataset asset with schema and lineage tracking.
    
    Example:
        >>> raw_data = Dataset(
        ...     name="imagenet_train",
        ...     version="v2.0",
        ...     data=train_dataset,
        ...     properties={"size": "150GB", "samples": 1_281_167}
        ... )
    """
    
    def __init__(
        self,
        name: str,
        version: Optional[str] = None,
        data: Any = None,
        schema: Optional[Any] = None,
        location: Optional[str] = None,
        parent: Optional[Asset] = None,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            name=name,
            version=version,
            data=data,
            parent=parent,
            tags=tags,
            properties=properties
        )
        
        self.schema = schema
        self.location = location
        
        # Add dataset-specific properties
        if schema:
            self.metadata.properties['schema'] = str(schema)
        if location:
            self.metadata.properties['location'] = location
    
    @property
    def size(self) -> Optional[int]:
        """Get dataset size if available."""
        return self.metadata.properties.get('size')
    
    @property
    def num_samples(self) -> Optional[int]:
        """Get number of samples if available."""
        return self.metadata.properties.get('samples') or self.metadata.properties.get('num_samples')
    
    def validate_schema(self) -> bool:
        """Validate data against schema (placeholder)."""
        if self.schema is None or self.data is None:
            return True
        # Schema validation would go here
        return True
    
    def split(self, train_ratio: float = 0.8, name_prefix: Optional[str] = None):
        """
        Split dataset into train/test.
        
        Args:
            train_ratio: Ratio for training split
            name_prefix: Prefix for split dataset names
            
        Returns:
            Tuple of (train_dataset, test_dataset)
        """
        prefix = name_prefix or self.name
        
        # Placeholder - actual splitting logic would depend on data type
        train_data = self.data  # Would actually split the data
        test_data = self.data
        
        train_dataset = Dataset(
            name=f"{prefix}_train",
            version=self.version,
            data=train_data,
            schema=self.schema,
            parent=self,
            tags={**self.metadata.tags, 'split': 'train'}
        )
        
        test_dataset = Dataset(
            name=f"{prefix}_test",
            version=self.version,
            data=test_data,
            schema=self.schema,
            parent=self,
            tags={**self.metadata.tags, 'split': 'test'}
        )
        
        return train_dataset, test_dataset

"""
Base Asset - Foundation for all ML assets in UniFlow.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class AssetMetadata:
    """Metadata for an asset."""
    id: str
    name: str
    version: str
    asset_type: str
    created_at: datetime
    created_by: str
    parent_ids: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'asset_type': self.asset_type,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'parent_ids': self.parent_ids,
            'tags': self.tags,
            'properties': self.properties
        }


class Asset:
    """
    Base class for all ML assets (datasets, models, features, etc).
    
    Assets are first-class objects in UniFlow pipelines with full lineage tracking.
    """
    
    def __init__(
        self,
        name: str,
        version: Optional[str] = None,
        data: Any = None,
        parent: Optional["Asset"] = None,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.version = version or "v1.0.0"
        self.data = data
        self.id = str(uuid4())
        
        # Metadata
        self.metadata = AssetMetadata(
            id=self.id,
            name=name,
            version=self.version,
            asset_type=self.__class__.__name__,
            created_at=datetime.now(),
            created_by="uniflow",
            parent_ids=[parent.id] if parent else [],
            tags=tags or {},
            properties=properties or {}
        )
        
        # Lineage tracking
        self.parents: List[Asset] = [parent] if parent else []
        self.children: List[Asset] = []
        
        if parent:
            parent.children.append(self)
    
    @classmethod
    def create(
        cls,
        data: Any,
        name: Optional[str] = None,
        version: Optional[str] = None,
        parent: Optional["Asset"] = None,
        **kwargs
    ) -> "Asset":
        """
        Factory method to create an asset.
        
        Args:
            data: The actual data/object
            name: Asset name
            version: Asset version
            parent: Parent asset for lineage
            **kwargs: Additional metadata
            
        Returns:
            New asset instance
        """
        asset_name = name or f"{cls.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Extract properties if passed explicitly
        props = kwargs.pop('properties', {})
        # Merge with remaining kwargs
        props.update(kwargs)
        
        return cls(
            name=asset_name,
            version=version,
            data=data,
            parent=parent,
            properties=props
        )
    
    def get_hash(self) -> str:
        """Generate hash of asset for caching/versioning."""
        content = json.dumps({
            'name': self.name,
            'version': self.version,
            'type': self.metadata.asset_type,
            'created_at': self.metadata.created_at.isoformat()
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_lineage(self, depth: int = -1) -> Dict[str, Any]:
        """
        Get asset lineage.
        
        Args:
            depth: How many levels to traverse (-1 for all)
            
        Returns:
            Lineage tree as nested dict
        """
        lineage = {
            'asset': {
                'id': self.id,
                'name': self.name,
                'type': self.metadata.asset_type,
                'version': self.version
            },
            'parents': [],
            'children': []
        }
        
        if depth != 0:
            next_depth = depth - 1 if depth > 0 else -1
            lineage['parents'] = [p.get_lineage(next_depth) for p in self.parents]
            lineage['children'] = [c.get_lineage(next_depth) for c in self.children]
        
        return lineage
    
    def get_all_ancestors(self) -> Set["Asset"]:
        """Get all ancestor assets."""
        ancestors = set()
        
        def traverse(asset):
            for parent in asset.parents:
                if parent not in ancestors:
                    ancestors.add(parent)
                    traverse(parent)
        
        traverse(self)
        return ancestors
    
    def get_all_descendants(self) -> Set["Asset"]:
        """Get all descendant assets."""
        descendants = set()
        
        def traverse(asset):
            for child in asset.children:
                if child not in descendants:
                    descendants.add(child)
                    traverse(child)
        
        traverse(self)
        return descendants
    
    def add_tag(self, key: str, value: str):
        """Add a tag to the asset."""
        self.metadata.tags[key] = value
    
    def add_property(self, key: str, value: Any):
        """Add a property to the asset."""
        self.metadata.properties[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert asset to dictionary."""
        return {
            'metadata': self.metadata.to_dict(),
            'lineage': {
                'parents': [p.id for p in self.parents],
                'children': [c.id for c in self.children]
            }
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return isinstance(other, Asset) and self.id == other.id

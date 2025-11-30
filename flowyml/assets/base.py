"""Base Asset - Foundation for all ML assets in flowyml."""

import hashlib
import json
from typing import Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class AssetMetadata:
    """Metadata for an asset."""

    asset_id: str
    name: str
    version: str
    asset_type: str
    created_at: datetime
    created_by: str
    parent_ids: list[str] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "version": self.version,
            "asset_type": self.asset_type,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "parent_ids": self.parent_ids,
            "tags": self.tags,
            "properties": self.properties,
        }


class Asset:
    """Base class for all ML assets (datasets, models, features, etc).

    Assets are first-class objects in flowyml pipelines with full lineage tracking.
    """

    def __init__(
        self,
        name: str,
        version: str | None = None,
        data: Any = None,
        parent: Optional["Asset"] = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
    ):
        self.name = name
        self.version = version or "v1.0.0"
        self.data = data
        self.asset_id = str(uuid4())

        # Metadata
        self.metadata = AssetMetadata(
            asset_id=self.asset_id,
            name=name,
            version=self.version,
            asset_type=self.__class__.__name__,
            created_at=datetime.now(),
            created_by="flowyml",
            parent_ids=[parent.asset_id] if parent else [],
            tags=tags or {},
            properties=properties or {},
        )

        # Lineage tracking
        self.parents: list[Asset] = [parent] if parent else []
        self.children: list[Asset] = []

        if parent:
            parent.children.append(self)

    @property
    def properties(self) -> dict[str, Any]:
        """Expose mutable properties stored in metadata."""
        return self.metadata.properties

    @property
    def tags(self) -> dict[str, str]:
        """Expose mutable tags stored in metadata."""
        return self.metadata.tags

    @classmethod
    def create(
        cls,
        data: Any,
        name: str | None = None,
        version: str | None = None,
        parent: Optional["Asset"] = None,
        **kwargs: Any,
    ) -> "Asset":
        """Factory method to create an asset.

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

        # Extract tags and properties if passed explicitly
        tags = kwargs.pop("tags", {})
        props = kwargs.pop("properties", {})
        # Merge remaining kwargs into properties
        props.update(kwargs)

        return cls(
            name=asset_name,
            version=version,
            data=data,
            parent=parent,
            tags=tags,
            properties=props,
        )

    def get_hash(self) -> str:
        """Generate hash of asset for caching/versioning."""
        content = json.dumps(
            {
                "name": self.name,
                "version": self.version,
                "type": self.metadata.asset_type,
                "created_at": self.metadata.created_at.isoformat(),
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_lineage(self, depth: int = -1) -> dict[str, Any]:
        """Get asset lineage.

        Args:
            depth: How many levels to traverse (-1 for all)

        Returns:
            Lineage tree as nested dict
        """
        lineage = {
            "asset": {
                "asset_id": self.asset_id,
                "name": self.name,
                "type": self.metadata.asset_type,
                "version": self.version,
            },
            "parents": [],
            "children": [],
        }

        if depth != 0:
            next_depth = depth - 1 if depth > 0 else -1
            lineage["parents"] = [p.get_lineage(next_depth) for p in self.parents]
            lineage["children"] = [c.get_lineage(next_depth) for c in self.children]

        return lineage

    def get_all_ancestors(self) -> set["Asset"]:
        """Get all ancestor assets."""
        ancestors = set()

        def traverse(asset) -> None:
            for parent in asset.parents:
                if parent not in ancestors:
                    ancestors.add(parent)
                    traverse(parent)

        traverse(self)
        return ancestors

    def get_all_descendants(self) -> set["Asset"]:
        """Get all descendant assets."""
        descendants = set()

        def traverse(asset) -> None:
            for child in asset.children:
                if child not in descendants:
                    descendants.add(child)
                    traverse(child)

        traverse(self)
        return descendants

    def add_tag(self, key: str, value: str) -> None:
        """Add a tag to the asset."""
        self.metadata.tags[key] = value

    def add_property(self, key: str, value: Any) -> None:
        """Add a property to the asset."""
        self.metadata.properties[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert asset to dictionary."""
        return {
            "metadata": self.metadata.to_dict(),
            "lineage": {
                "parents": [p.asset_id for p in self.parents],
                "children": [c.asset_id for c in self.children],
            },
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"

    def __hash__(self):
        return hash(self.asset_id)

    def __eq__(self, other):
        return isinstance(other, Asset) and self.asset_id == other.asset_id

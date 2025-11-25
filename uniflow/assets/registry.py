"""
Asset Registry - Central registry for all pipeline assets.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Type
from datetime import datetime

from uniflow.assets.base import Asset


class AssetRegistry:
    """
    Central registry for managing and querying assets.
    """
    
    def __init__(self, registry_dir: str = ".uniflow/assets"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        self.assets: Dict[str, Asset] = {}  # id -> asset
        self.assets_by_name: Dict[str, List[Asset]] = {}  # name -> [assets]
        self.assets_by_type: Dict[str, Set[Asset]] = {}  # type -> {assets}
        
        self._load_registry()
    
    def register(self, asset: Asset):
        """Register an asset."""
        self.assets[asset.id] = asset
        
        # Index by name
        if asset.name not in self.assets_by_name:
            self.assets_by_name[asset.name] = []
        self.assets_by_name[asset.name].append(asset)
        
        # Index by type
        asset_type = asset.metadata.asset_type
        if asset_type not in self.assets_by_type:
            self.assets_by_type[asset_type] = set()
        self.assets_by_type[asset_type].add(asset)
        
        self._save_registry()
    
    def get(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID."""
        return self.assets.get(asset_id)
    
    def get_by_name(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[Asset]:
        """
        Get asset by name and optionally version.
        
        Returns the latest version if version not specified.
        """
        assets = self.assets_by_name.get(name, [])
        
        if not assets:
            return None
        
        if version:
            for asset in assets:
                if asset.version == version:
                    return asset
            return None
        
        # Return latest version
        return max(assets, key=lambda a: a.metadata.created_at)
    
    def list_by_type(self, asset_type: str) -> List[Asset]:
        """List all assets of a specific type."""
        return list(self.assets_by_type.get(asset_type, set()))
    
    def list_all(self) -> List[Asset]:
        """List all registered assets."""
        return list(self.assets.values())
    
    def search(
        self,
        name: Optional[str] = None,
        asset_type: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        created_after: Optional[datetime] = None
    ) -> List[Asset]:
        """
        Search for assets matching criteria.
        
        Args:
            name: Filter by name (substring match)
            asset_type: Filter by asset type
            tags: Filter by tags (must match all)
            created_after: Filter by creation date
            
        Returns:
            List of matching assets
        """
        results = list(self.assets.values())
        
        if name:
            results = [a for a in results if name.lower() in a.name.lower()]
        
        if asset_type:
            results = [a for a in results if a.metadata.asset_type == asset_type]
        
        if tags:
            results = [
                a for a in results
                if all(a.metadata.tags.get(k) == v for k, v in tags.items())
            ]
        
        if created_after:
            results = [
                a for a in results
                if a.metadata.created_at > created_after
            ]
        
        return results
    
    def get_lineage_graph(self, asset_id: str) -> Dict:
        """Get full lineage graph for an asset."""
        asset = self.get(asset_id)
        if not asset:
            return {}
        return asset.get_lineage()
    
    def _save_registry(self):
        """Save registry metadata to disk."""
        registry_file = self.registry_dir / "registry.json"
        
        data = {
            'assets': {
                asset_id: asset.to_dict()
                for asset_id, asset in self.assets.items()
            }
        }
        
        with open(registry_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_registry(self):
        """Load registry metadata from disk."""
        registry_file = self.registry_dir / "registry.json"
        
        if not registry_file.exists():
            return
        
        try:
            with open(registry_file, 'r') as f:
                data = json.load(f)
            
            # Note: This is simplified - in production, we'd need to
            # deserialize the actual asset objects with their data
            # For now, we just load the metadata
            
        except Exception as e:
            print(f"Warning: Failed to load registry: {e}")
    
    def clear(self):
        """Clear the registry."""
        self.assets.clear()
        self.assets_by_name.clear()
        self.assets_by_type.clear()
        self._save_registry()
    
    def stats(self) -> Dict[str, int]:
        """Get registry statistics."""
        return {
            'total_assets': len(self.assets),
            'by_type': {
                asset_type: len(assets)
                for asset_type, assets in self.assets_by_type.items()
            }
        }

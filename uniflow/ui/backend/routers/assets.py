from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from uniflow.storage.metadata import SQLiteMetadataStore
from uniflow.utils.config import get_config

router = APIRouter()

def get_store():
    return SQLiteMetadataStore()

@router.get("/")
async def list_assets(limit: int = 50, type: str = None, run_id: str = None):
    """List all assets."""
    try:
        store = get_store()
        
        # Build filters
        filters = {}
        if type:
            filters['type'] = type
        if run_id:
            filters['run_id'] = run_id
            
        assets = store.list_assets(limit=limit, **filters)
            
        return {"assets": assets}
    except Exception as e:
        return {"assets": [], "error": str(e)}

@router.get("/{artifact_id}")
async def get_asset(artifact_id: str):
    """Get details for a specific asset."""
    store = get_store()
    asset = store.load_artifact(artifact_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

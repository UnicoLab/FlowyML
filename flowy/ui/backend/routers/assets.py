from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from flowy.storage.metadata import SQLiteMetadataStore
from flowy.utils.config import get_config

router = APIRouter()

def get_store():
    return SQLiteMetadataStore()

@router.get("/")
async def list_assets(limit: int = 50, type: str = None, run_id: str = None):
    """List all assets."""
    try:
        store = get_store()
        import sqlite3
        import json
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if type:
            conditions.append("type = ?")
            params.append(type)
            
        if run_id:
            conditions.append("run_id = ?")
            params.append(run_id)
            
        if conditions:
            query = "SELECT artifact_id, metadata FROM artifacts WHERE " + " AND ".join(conditions)
        else:
            query = "SELECT artifact_id, metadata FROM artifacts"
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        assets = []
        for row in rows:
            asset = json.loads(row[1])
            asset['artifact_id'] = row[0]
            assets.append(asset)
            
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

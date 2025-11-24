from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from flowy.storage.metadata import SQLiteMetadataStore
from flowy.utils.config import get_config

router = APIRouter()

def get_store():
    return SQLiteMetadataStore()

@router.get("/")
async def list_assets(limit: int = 50, type: str = None):
    """List all assets."""
    try:
        store = get_store()
        import sqlite3
        import json
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()
        
        query = "SELECT metadata FROM artifacts"
        params = []
        if type:
            query += " WHERE type = ?"
            params.append(type)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        assets = [json.loads(row[0]) for row in rows]
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

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from flowy.storage.metadata import SQLiteMetadataStore
from flowy.utils.config import get_config

router = APIRouter()

def get_store():
    return SQLiteMetadataStore()

@router.get("/")
async def list_runs(limit: int = 20):
    """List all runs."""
    try:
        store = get_store()
        runs = store.list_runs(limit=limit)
        return {"runs": runs}
    except Exception as e:
        return {"runs": [], "error": str(e)}

@router.get("/{run_id}")
async def get_run(run_id: str):
    """Get details for a specific run."""
    store = get_store()
    run = store.load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.get("/{run_id}/metrics")
async def get_run_metrics(run_id: str):
    """Get metrics for a specific run."""
    store = get_store()
    metrics = store.get_metrics(run_id)
    return {"metrics": metrics}

@router.get("/{run_id}/artifacts")
async def get_run_artifacts(run_id: str):
    """Get artifacts for a specific run."""
    store = get_store()
    # We need to query artifacts by run_id
    # SQLiteMetadataStore doesn't have a direct method for this exposed nicely, 
    # but we can add one or use raw SQL.
    # Let's use raw SQL for now to be safe.
    import sqlite3
    import json
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT metadata FROM artifacts WHERE run_id = ?", (run_id,))
    rows = cursor.fetchall()
    conn.close()
    
    artifacts = [json.loads(row[0]) for row in rows]
    return {"artifacts": artifacts}

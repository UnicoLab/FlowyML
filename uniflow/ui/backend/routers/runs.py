from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from uniflow.storage.metadata import SQLiteMetadataStore
from uniflow.utils.config import get_config

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
    artifacts = store.list_assets(run_id=run_id)
    return {"artifacts": artifacts}

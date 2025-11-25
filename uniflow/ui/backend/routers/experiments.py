from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from uniflow.storage.metadata import SQLiteMetadataStore

router = APIRouter()

def get_store():
    return SQLiteMetadataStore()

@router.get("/")
async def list_experiments():
    """List all experiments."""
    try:
        store = get_store()
        experiments = store.list_experiments()
        return {"experiments": experiments}
    except Exception as e:
        return {"experiments": [], "error": str(e)}

@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get experiment details."""
    store = get_store()
    experiment = store.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment

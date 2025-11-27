from fastapi import APIRouter, HTTPException
from uniflow.storage.metadata import SQLiteMetadataStore

router = APIRouter()


def get_store():
    return SQLiteMetadataStore()


@router.get("/")
async def list_experiments(project: str = None):
    """List all experiments, optionally filtered by project."""
    try:
        store = get_store()
        experiments = store.list_experiments()

        # Filter by project if specified
        if project:
            experiments = [e for e in experiments if e.get("project") == project]

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

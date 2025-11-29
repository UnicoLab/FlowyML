from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from flowyml.storage.metadata import SQLiteMetadataStore

router = APIRouter()


def get_store():
    return SQLiteMetadataStore()


@router.get("/")
async def list_runs(limit: int = 20, project: str = None):
    """List all runs, optionally filtered by project."""
    try:
        store = get_store()
        runs = store.list_runs(limit=limit)

        # Filter by project if specified
        if project:
            runs = [r for r in runs if r.get("project") == project]

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


class ProjectUpdate(BaseModel):
    project_name: str


@router.put("/{run_id}/project")
async def update_run_project(run_id: str, update: ProjectUpdate):
    """Update the project for a run."""
    store = get_store()
    try:
        store.update_run_project(run_id, update.project_name)
        return {"status": "success", "project": update.project_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

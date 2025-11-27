from fastapi import APIRouter, HTTPException
from uniflow.storage.metadata import SQLiteMetadataStore

router = APIRouter()


def get_store():
    return SQLiteMetadataStore()


@router.get("/")
async def list_assets(limit: int = 50, asset_type: str = None, run_id: str = None, project: str = None):
    """List all assets, optionally filtered by project."""
    try:
        store = get_store()

        # Build filters
        filters = {}
        if asset_type:
            filters["type"] = asset_type
        if run_id:
            filters["run_id"] = run_id

        assets = store.list_assets(limit=limit, **filters)

        # Filter by project if specified
        if project:
            # Get all runs for this project
            all_runs = store.list_runs(limit=1000)
            project_run_ids = {r.get("run_id") for r in all_runs if r.get("project") == project}
            assets = [a for a in assets if a.get("run_id") in project_run_ids]

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

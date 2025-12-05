from fastapi import APIRouter, HTTPException
from flowyml.ui.backend.dependencies import get_store

router = APIRouter()


@router.get("/")
async def get_global_stats(project: str | None = None):
    """Get global statistics."""
    try:
        store = get_store()
        return store.get_statistics(project=project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.utils.config import get_config

router = APIRouter()


def get_store():
    get_config()
    # Assuming default path or from config
    # The SQLiteMetadataStore defaults to .flowyml/metadata.db which is what we want for now
    return SQLiteMetadataStore()


@router.get("/")
async def list_pipelines(project: str = None):
    """List all unique pipelines, optionally filtered by project."""
    try:
        store = get_store()
        pipelines = store.list_pipelines(project=project)
        return {"pipelines": pipelines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pipeline_name}/runs")
async def list_pipeline_runs(pipeline_name: str, limit: int = 10):
    """List runs for a specific pipeline."""
    store = get_store()
    runs = store.query(pipeline_name=pipeline_name)
    return {"runs": runs[:limit]}


@router.get("/stats")
async def get_all_pipelines_stats():
    """Get statistics for all pipelines."""
    try:
        store = get_store()
        pipelines = store.list_pipelines()

        if not pipelines:
            return {"total_pipelines": 0, "total_runs": 0, "pipelines": []}

        stats = []
        for pipeline_name in pipelines:
            runs = store.query(pipeline_name=pipeline_name)
            total = len(runs)
            successful = len([r for r in runs if r.get("status") == "completed"])
            stats.append(
                {
                    "name": pipeline_name,
                    "total_runs": total,
                    "success_rate": successful / total if total > 0 else 0,
                },
            )

        return {
            "total_pipelines": len(pipelines),
            "total_runs": sum(s["total_runs"] for s in stats),
            "pipelines": stats,
        }
    except Exception as e:
        # Database might not exist yet
        return {"total_pipelines": 0, "total_runs": 0, "pipelines": [], "error": str(e)}


@router.get("/{pipeline_name}/stats")
async def get_pipeline_stats(pipeline_name: str):
    """Get statistics for a specific pipeline."""
    try:
        store = get_store()
        runs = store.query(pipeline_name=pipeline_name)

        total_runs = len(runs)
        if total_runs == 0:
            return {"total_runs": 0, "success_rate": 0, "avg_duration": 0}

        successful_runs = [r for r in runs if r.get("status") == "completed"]
        success_rate = len(successful_runs) / total_runs if total_runs > 0 else 0

        durations = [r.get("duration", 0) for r in runs if r.get("duration") is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_runs": total_runs,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "last_run": runs[0] if runs else None,
        }
    except Exception as e:
        return {"total_runs": 0, "success_rate": 0, "avg_duration": 0, "error": str(e)}


class ProjectUpdate(BaseModel):
    project_name: str


@router.put("/{pipeline_name}/project")
async def update_pipeline_project(pipeline_name: str, update: ProjectUpdate):
    """Update the project for a pipeline."""
    try:
        store = get_store()
        # This updates all runs for this pipeline to the new project
        # In a real system, we might want to just tag the pipeline definition
        # But since our "pipeline" concept is derived from runs, we update runs
        store.update_pipeline_project(pipeline_name, update.project_name)
        return {"status": "success", "project": update.project_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

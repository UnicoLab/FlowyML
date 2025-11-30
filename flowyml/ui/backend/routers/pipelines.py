from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.project import ProjectManager
from flowyml.utils.config import get_config
from typing import Optional

router = APIRouter()


def get_store():
    get_config()
    return SQLiteMetadataStore()


def _iter_metadata_stores():
    """Yield tuples of (project_name, store) including global and project stores."""
    stores = [(None, SQLiteMetadataStore())]
    try:
        manager = ProjectManager()
        for project_meta in manager.list_projects():
            name = project_meta.get("name")
            if not name:
                continue
            project = manager.get_project(name)
            if project:
                stores.append((name, project.metadata_store))
    except Exception:
        pass
    return stores


@router.get("/")
async def list_pipelines(project: Optional[str] = None, limit: int = 100):
    """List all unique pipelines with details, optionally filtered by project."""
    try:
        pipeline_map = {}  # pipeline_name -> data

        for project_name, store in _iter_metadata_stores():
            # Skip other projects if filtering
            if project and project_name and project != project_name:
                continue

            # Get pipeline names from this store
            store_pipeline_names = store.list_pipelines()

            for name in store_pipeline_names:
                # Get runs for this pipeline
                filters = {"pipeline_name": name}
                runs = store.query(**filters)

                if not runs:
                    continue

                last_run = runs[0]
                run_project = last_run.get("project") or project_name

                # Skip if filtering by project and doesn't match
                if project and run_project != project:
                    continue

                # Use composite key if we already have this pipeline from another project
                key = f"{name}:{run_project}" if run_project else name

                if key not in pipeline_map:
                    pipeline_map[key] = {
                        "name": name,
                        "created": last_run.get("start_time"),
                        "version": last_run.get("git_sha", "latest")[:7] if last_run.get("git_sha") else "1.0",
                        "status": last_run.get("status", "unknown"),
                        "run_count": len(runs),
                        "last_run_id": last_run.get("run_id"),
                        "project": run_project,
                    }

        # Return list of pipelines
        enriched_pipelines = list(pipeline_map.values())[:limit]
        return {"pipelines": enriched_pipelines}
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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.project import ProjectManager
from typing import Optional

router = APIRouter()


def get_store():
    return SQLiteMetadataStore()


def _iter_metadata_stores():
    """Yield tuples of (project_name, store) including global and project stores."""
    stores: list[tuple[Optional[str], SQLiteMetadataStore]] = [(None, SQLiteMetadataStore())]
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


def _deduplicate_runs(runs):
    seen = {}
    for run, project_name in runs:
        run_id = run.get("run_id") or f"{project_name}:{len(seen)}"
        if run_id in seen:
            continue
        entry = dict(run)
        if project_name and not entry.get("project"):
            entry["project"] = project_name
        seen[run_id] = entry
    return list(seen.values())


def _sort_runs(runs):
    def sort_key(run):
        return run.get("start_time") or run.get("created_at") or ""

    return sorted(runs, key=sort_key, reverse=True)


@router.get("/")
async def list_runs(limit: int = 20, project: str = None):
    """List all runs, optionally filtered by project."""
    try:
        combined = []
        for project_name, store in _iter_metadata_stores():
            # Skip other projects if filtering by project name
            if project and project_name and project != project_name:
                continue
            store_runs = store.list_runs(limit=limit)
            for run in store_runs:
                combined.append((run, project_name))

        runs = _deduplicate_runs(combined)

        if project:
            runs = [r for r in runs if r.get("project") == project]

        runs = _sort_runs(runs)[:limit]
        return {"runs": runs}
    except Exception as e:
        return {"runs": [], "error": str(e)}


@router.get("/{run_id}")
async def get_run(run_id: str):
    """Get details for a specific run."""
    run, _ = _find_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/metrics")
async def get_run_metrics(run_id: str):
    """Get metrics for a specific run."""
    store = _find_store_for_run(run_id)
    metrics = store.get_metrics(run_id)
    return {"metrics": metrics}


@router.get("/{run_id}/artifacts")
async def get_run_artifacts(run_id: str):
    """Get artifacts for a specific run."""
    store = _find_store_for_run(run_id)
    artifacts = store.list_assets(run_id=run_id)
    return {"artifacts": artifacts}


class ProjectUpdate(BaseModel):
    project_name: str


@router.put("/{run_id}/project")
async def update_run_project(run_id: str, update: ProjectUpdate):
    """Update the project for a run."""
    store = _find_store_for_run(run_id)
    try:
        store.update_run_project(run_id, update.project_name)
        return {"status": "success", "project": update.project_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _find_run(run_id: str):
    for project_name, store in _iter_metadata_stores():
        run = store.load_run(run_id)
        if run:
            if project_name and not run.get("project"):
                run["project"] = project_name
            return run, store
    return None, None


def _find_store_for_run(run_id: str) -> SQLiteMetadataStore:
    _, store = _find_run(run_id)
    if store:
        return store
    raise HTTPException(status_code=404, detail="Run not found")

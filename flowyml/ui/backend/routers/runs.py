from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.project import ProjectManager
import json
from flowyml.ui.backend.dependencies import get_store

router = APIRouter()


def _iter_metadata_stores():
    """Yield tuples of (project_name, store) including global and project stores."""
    stores: list[tuple[str | None, SQLiteMetadataStore]] = [(None, get_store())]
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
async def list_runs(
    limit: int = 20,
    project: str = None,
    pipeline_name: str = None,
    status: str = None,
):
    """List all runs, optionally filtered by project, pipeline_name, and status."""
    try:
        combined = []
        for project_name, store in _iter_metadata_stores():
            # Skip other projects if filtering by project name
            if project and project_name and project != project_name:
                continue

            # Use store's query method if available for better performance, or list_runs
            # SQLMetadataStore has query method.
            if hasattr(store, "query"):
                filters = {}
                if pipeline_name:
                    filters["pipeline_name"] = pipeline_name
                if status:
                    filters["status"] = status

                # We can't pass limit to query easily if it doesn't support it,
                # but SQLMetadataStore.query usually returns all matching.
                # We'll slice later.
                store_runs = store.query(**filters)
            else:
                store_runs = store.list_runs(limit=limit)

            for run in store_runs:
                # Apply filters if store didn't (e.g. if we used list_runs or store doesn't support query)
                if pipeline_name and run.get("pipeline_name") != pipeline_name:
                    continue
                if status and run.get("status") != status:
                    continue

                combined.append((run, project_name))

        runs = _deduplicate_runs(combined)

        if project:
            runs = [r for r in runs if r.get("project") == project]

        runs = _sort_runs(runs)[:limit]
        return {"runs": runs}
    except Exception as e:
        return {"runs": [], "error": str(e)}


class RunCreate(BaseModel):
    run_id: str
    pipeline_name: str
    status: str = "pending"
    start_time: str
    end_time: str | None = None
    duration: float | None = None
    metadata: dict = {}
    project: str | None = None
    metrics: dict | None = None
    parameters: dict | None = None


@router.post("/")
async def create_run(run: RunCreate):
    """Create or update a run."""
    try:
        store = get_store()

        # Prepare metadata dict
        metadata = run.metadata.copy()
        metadata.update(
            {
                "pipeline_name": run.pipeline_name,
                "status": run.status,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "duration": run.duration,
                "project": run.project,
            },
        )

        if run.metrics:
            metadata["metrics"] = run.metrics

        if run.parameters:
            metadata["parameters"] = run.parameters

        store.save_run(run.run_id, metadata)
        return {"status": "success", "run_id": run.run_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/{run_id}/cloud-status")
async def get_cloud_status(run_id: str):
    """Get real-time status from cloud orchestrator for remote runs.

    Returns cloud provider status if the run is remote, otherwise returns
    status from metadata store.
    """
    run, store = _find_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get orchestrator info from run metadata
    metadata = run.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}

    orchestrator_type = metadata.get("orchestrator_type", "local")

    # If local run, just return metadata store status
    if orchestrator_type == "local":
        return {
            "run_id": run_id,
            "status": run.get("status", "unknown"),
            "orchestrator_type": "local",
            "is_remote": False,
            "cloud_status": None,
        }

    # For remote runs, try to query cloud orchestrator
    cloud_status = None
    cloud_error = None

    try:
        # Import orchestrators dynamically to avoid errors if cloud SDKs aren't installed
        from flowyml.utils.stack_config import load_active_stack

        stack = load_active_stack()
        if not stack or not stack.orchestrator:
            cloud_error = "No active stack or orchestrator configured"
        else:
            orchestrator = stack.orchestrator

            # Check if orchestrator has get_run_status method
            if hasattr(orchestrator, "get_run_status"):
                from flowyml.core.execution_status import ExecutionStatus

                status = orchestrator.get_run_status(run_id)

                # Convert ExecutionStatus to dict
                if isinstance(status, ExecutionStatus):
                    cloud_status = {
                        "status": status.value,
                        "is_finished": status.is_finished,
                        "is_successful": status.is_successful,
                    }
                else:
                    cloud_status = {"status": str(status)}
            else:
                cloud_error = f"Orchestrator {orchestrator_type} does not support status queries"

    except ImportError as e:
        cloud_error = f"Cloud SDK not available: {str(e)}"
    except Exception as e:
        cloud_error = f"Error querying cloud status: {str(e)}"

    return {
        "run_id": run_id,
        "status": run.get("status", "unknown"),
        "orchestrator_type": orchestrator_type,
        "is_remote": True,
        "cloud_status": cloud_status,
        "cloud_error": cloud_error,
    }

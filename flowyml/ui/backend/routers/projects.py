from fastapi import APIRouter, HTTPException, Depends, Query
from flowyml.core.project import ProjectManager
from flowyml.utils.config import get_config
from pydantic import BaseModel

router = APIRouter()

#: Upper bound on any client-supplied page size. Without it a request such as
#: `?limit=100000000` makes the server materialise an unbounded result set.
MAX_PAGE_SIZE = 1000


def get_projects_manager() -> ProjectManager:
    """Instantiate a ProjectManager bound to the current config."""
    config = get_config()
    return ProjectManager(str(config.projects_dir))


@router.get("/")
async def list_projects(manager: ProjectManager = Depends(get_projects_manager)):
    """List all projects, including those discovered from run metadata."""
    try:
        # Get explicitly created projects
        explicit_projects = manager.list_projects()
        project_names = {p.get("name") for p in explicit_projects if p.get("name")}

        # Also discover projects from run metadata in global store
        from flowyml.ui.backend.dependencies import get_store

        store = get_store()

        discovered_projects = []
        try:
            # Get all runs and extract unique project names
            runs = store.list_runs(limit=1000)
            for run in runs:
                project_name = run.get("project")
                if project_name and project_name not in project_names:
                    project_names.add(project_name)
                    # Create a synthetic project entry for discovered projects
                    discovered_projects.append(
                        {
                            "name": project_name,
                            "description": "Auto-discovered from pipeline runs",
                            "created_at": run.get("start_time"),
                            "pipelines": [],
                            "tags": {},
                            "discovered": True,  # Flag to indicate this wasn't explicitly created
                        },
                    )
        except Exception:
            pass  # Store might not be initialized

        # Combine explicit and discovered projects
        all_projects = explicit_projects + discovered_projects
        return {"projects": all_projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


@router.post("/")
async def create_project(
    project: ProjectCreate,
    manager: ProjectManager = Depends(get_projects_manager),
):
    """Create a new project."""
    created_project = manager.create_project(project.name, project.description)
    return {
        "name": created_project.name,
        "description": created_project.description,
        "created": True,
    }


@router.get("/{project_name}")
async def get_project(project_name: str, manager: ProjectManager = Depends(get_projects_manager)):
    """Get project details."""
    project = manager.get_project(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "name": project.name,
        "description": project.description,
        "metadata": project.metadata,
        "stats": project.get_stats(),
        "pipelines": project.get_pipelines(),
    }


@router.get("/{project_name}/runs")
async def get_project_runs(
    project_name: str,
    pipeline_name: str | None = None,
    limit: int = Query(100, ge=1, le=MAX_PAGE_SIZE),
    manager: ProjectManager = Depends(get_projects_manager),
):
    """Get runs for a project."""
    project = manager.get_project(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    runs = project.list_runs(pipeline_name=pipeline_name, limit=limit)
    return runs


@router.get("/{project_name}/artifacts")
async def get_project_artifacts(
    project_name: str,
    artifact_type: str | None = None,
    limit: int = Query(100, ge=1, le=MAX_PAGE_SIZE),
    manager: ProjectManager = Depends(get_projects_manager),
):
    """Get artifacts for a project."""
    project = manager.get_project(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    artifacts = project.get_artifacts(artifact_type=artifact_type, limit=limit)
    return artifacts


@router.get("/{project_name}/metrics")
async def get_project_metrics(
    project_name: str,
    model_name: str | None = None,
    limit: int = Query(100, ge=1, le=MAX_PAGE_SIZE),
    manager: ProjectManager = Depends(get_projects_manager),
):
    """Get logged metrics for a project (from model_metrics table and Metrics artifacts)."""
    metrics = []

    from flowyml.ui.backend.dependencies import get_store

    store = get_store()

    try:
        # Get all runs for this project
        all_runs = store.list_runs(limit=1000)
        project_run_ids = {r.get("run_id") for r in all_runs if r.get("project") == project_name}

        # 1. Try to get metrics from model_metrics table
        all_model_metrics = store.list_model_metrics(limit=limit * 2)
        for m in all_model_metrics:
            if m.get("run_id") in project_run_ids or m.get("project") == project_name:
                metrics.append(m)

        # 2. Also extract metrics from Metrics artifacts
        all_assets = store.list_assets(limit=500)
        for asset in all_assets:
            # Check if it's a metrics artifact for this project (case-insensitive type check)
            asset_type = str(asset.get("type", "")).lower()
            if asset_type == "metrics" and asset.get("run_id") in project_run_ids:
                # Get properties which contain the metric values
                props = asset.get("properties", {})
                created_at = asset.get("created_at", "")
                run_id = asset.get("run_id", "")
                asset_name = asset.get("name", "evaluation")

                # Convert artifact properties to metric entries
                for key, value in props.items():
                    if isinstance(value, (int, float)) and key not in ["samples"]:
                        metrics.append(
                            {
                                "project": project_name,
                                "model_name": asset_name,
                                "run_id": run_id,
                                "metric_name": key,
                                "metric_value": value,
                                "environment": "evaluation",
                                "tags": {"source": "artifact"},
                                "created_at": created_at,
                            },
                        )
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Error fetching metrics: {e}")

    # Try explicit project as fallback
    if not metrics:
        project = manager.get_project(project_name)
        if project:
            metrics = project.list_model_metrics(model_name=model_name, limit=limit)

    return {
        "project": project_name,
        "metrics": metrics[:limit],
    }


@router.delete("/{project_name}")
async def delete_project(
    project_name: str,
    manager: ProjectManager = Depends(get_projects_manager),
):
    """Delete a project."""
    manager.delete_project(project_name, confirm=True)
    return {"deleted": True}

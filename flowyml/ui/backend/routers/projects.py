from fastapi import APIRouter, HTTPException, Depends
from flowyml.core.project import ProjectManager
from flowyml.utils.config import get_config
from pydantic import BaseModel

router = APIRouter()


def get_projects_manager() -> ProjectManager:
    """Instantiate a ProjectManager bound to the current config."""
    config = get_config()
    return ProjectManager(str(config.projects_dir))


@router.get("/")
async def list_projects(manager: ProjectManager = Depends(get_projects_manager)):
    """List all projects."""
    try:
        projects = manager.list_projects()
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


@router.post("/")
async def create_project(project: ProjectCreate, manager: ProjectManager = Depends(get_projects_manager)):
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
    limit: int = 100,
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
    limit: int = 100,
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
    limit: int = 100,
    manager: ProjectManager = Depends(get_projects_manager),
):
    """Get logged production metrics for a project."""
    project = manager.get_project(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "project": project_name,
        "metrics": project.list_model_metrics(model_name=model_name, limit=limit),
    }


@router.delete("/{project_name}")
async def delete_project(project_name: str, manager: ProjectManager = Depends(get_projects_manager)):
    """Delete a project."""
    manager.delete_project(project_name, confirm=True)
    return {"deleted": True}

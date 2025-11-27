from fastapi import APIRouter, HTTPException
from typing import List, Optional
from uniflow.core.project import Project, ProjectManager

router = APIRouter()
manager = ProjectManager()

@router.get("/")
async def list_projects():
    """List all projects."""
    try:
        projects = manager.list_projects()
        return projects
    except Exception as e:
        print(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

@router.post("/")
async def create_project(project: ProjectCreate):
    """Create a new project."""
    created_project = manager.create_project(project.name, project.description)
    return {
        "name": created_project.name,
        "description": created_project.description,
        "created": True
    }

@router.get("/{project_name}")
async def get_project(project_name: str):
    """Get project details."""
    project = manager.get_project(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "name": project.name,
        "description": project.description,
        "metadata": project.metadata,
        "stats": project.get_stats(),
        "pipelines": project.get_pipelines()
    }

@router.get("/{project_name}/runs")
async def get_project_runs(
    project_name: str,
    pipeline_name: Optional[str] = None,
    limit: int = 100
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
    artifact_type: Optional[str] = None,
    limit: int = 100
):
    """Get artifacts for a project."""
    project = manager.get_project(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    artifacts = project.get_artifacts(artifact_type=artifact_type, limit=limit)
    return artifacts

@router.delete("/{project_name}")
async def delete_project(project_name: str):
    """Delete a project."""
    manager.delete_project(project_name, confirm=True)
    return {"deleted": True}

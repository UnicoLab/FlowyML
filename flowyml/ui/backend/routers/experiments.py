from fastapi import APIRouter, HTTPException
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.project import ProjectManager
from flowyml.ui.backend.dependencies import get_store
from pydantic import BaseModel

router = APIRouter()


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
async def list_experiments(project: str | None = None):
    """List all experiments, optionally filtered by project."""
    try:
        combined_experiments = []

        for project_name, store in _iter_metadata_stores():
            # Skip other projects if filtering
            if project and project_name and project != project_name:
                continue

            store_experiments = store.list_experiments()

            for exp in store_experiments:
                # Add project info if not already present
                if project_name and not exp.get("project"):
                    exp["project"] = project_name

                # Skip if filtering by project and doesn't match
                if project and exp.get("project") != project:
                    continue

                combined_experiments.append(exp)

        return {"experiments": combined_experiments}
    except Exception as e:
        return {"experiments": [], "error": str(e)}


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get experiment details."""
    # Try to find experiment in any store
    for project_name, store in _iter_metadata_stores():
        experiment = store.get_experiment(experiment_id)
        if experiment:
            if project_name and not experiment.get("project"):
                experiment["project"] = project_name
            return experiment

    raise HTTPException(status_code=404, detail="Experiment not found")


@router.put("/{experiment_name}/project")
async def update_experiment_project(experiment_name: str, project_update: dict):
    """Update the project for an experiment."""
    try:
        store = get_store()
        project_name = project_update.get("project_name")

        # Update experiment project
        store.update_experiment_project(experiment_name, project_name)

        return {"message": f"Updated experiment {experiment_name} to project {project_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ExperimentCreate(BaseModel):
    experiment_id: str
    name: str
    description: str = ""
    tags: dict = {}
    project: str | None = None


@router.post("/")
async def create_experiment(experiment: ExperimentCreate):
    """Create or update an experiment."""
    try:
        store = get_store()
        store.save_experiment(
            experiment_id=experiment.experiment_id,
            name=experiment.name,
            description=experiment.description,
            tags=experiment.tags,
        )

        if experiment.project:
            store.update_experiment_project(experiment.name, experiment.project)

        return {"status": "success", "experiment_id": experiment.experiment_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ExperimentRunLog(BaseModel):
    run_id: str
    metrics: dict | None = None
    parameters: dict | None = None


@router.post("/{experiment_id}/runs")
async def log_experiment_run(experiment_id: str, log: ExperimentRunLog):
    """Log a run to an experiment."""
    try:
        store = get_store()
        store.log_experiment_run(
            experiment_id=experiment_id,
            run_id=log.run_id,
            metrics=log.metrics,
            parameters=log.parameters,
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

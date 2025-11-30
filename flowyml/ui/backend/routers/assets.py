from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.project import ProjectManager
from typing import Optional
from pathlib import Path

router = APIRouter()


def get_store():
    return SQLiteMetadataStore()


def _iter_metadata_stores():
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


def _dedupe_assets(assets):
    dedup = {}
    for asset, project_name in assets:
        artifact_id = asset.get("artifact_id") or f"{project_name}:{len(dedup)}"
        if artifact_id in dedup:
            continue
        entry = dict(asset)
        if project_name and not entry.get("project"):
            entry["project"] = project_name
        dedup[artifact_id] = entry
    return list(dedup.values())


@router.get("/")
async def list_assets(limit: int = 50, asset_type: str = None, run_id: str = None, project: str = None):
    """List all assets, optionally filtered by project."""
    try:
        combined = []
        for project_name, store in _iter_metadata_stores():
            if project and project_name and project != project_name:
                continue

            filters = {}
            if asset_type:
                filters["type"] = asset_type
            if run_id:
                filters["run_id"] = run_id

            assets = store.list_assets(limit=limit, **filters)
            for asset in assets:
                combined.append((asset, project_name))

        assets = _dedupe_assets(combined)

        if project:
            assets = [a for a in assets if a.get("project") == project]

        assets = assets[:limit]

        return {"assets": assets}
    except Exception as e:
        return {"assets": [], "error": str(e)}


@router.get("/lineage")
async def get_asset_lineage(
    asset_id: Optional[str] = None,
    project: Optional[str] = None,
    depth: int = 3,
):
    """
    Get lineage graph for artifacts.

    Returns nodes (artifacts, runs, pipelines) and edges (relationships).
    Can be scoped to a specific asset or all assets in a project.
    """
    try:
        store = get_store()
        nodes = []
        edges = []
        visited_artifacts = set()
        visited_runs = set()

        # Get starting artifacts
        if asset_id:
            artifact = store.load_artifact(asset_id)
            if not artifact:
                raise HTTPException(status_code=404, detail="Asset not found")
            starting_artifacts = [artifact]
        elif project:
            # Get all artifacts for project
            all_runs = store.list_runs(limit=1000)
            project_run_ids = {r.get("run_id") for r in all_runs if r.get("project") == project}
            all_artifacts = store.list_assets(limit=1000)
            starting_artifacts = [a for a in all_artifacts if a.get("run_id") in project_run_ids]
        else:
            # Get recent artifacts
            starting_artifacts = store.list_assets(limit=50)

        # Build graph
        for artifact in starting_artifacts:
            artifact_id = artifact.get("artifact_id")
            if not artifact_id or artifact_id in visited_artifacts:
                continue

            visited_artifacts.add(artifact_id)

            # Add artifact node
            nodes.append(
                {
                    "id": artifact_id,
                    "type": "artifact",
                    "label": artifact.get("name", artifact_id),
                    "artifact_type": artifact.get("type", "unknown"),
                    "metadata": {
                        "created_at": artifact.get("created_at"),
                        "properties": artifact.get("properties", {}),
                        "size": artifact.get("size"),
                        "run_id": artifact.get("run_id"),
                    },
                },
            )

            # Add relationship to run
            run_id = artifact.get("run_id")
            if run_id and run_id not in visited_runs:
                visited_runs.add(run_id)
                run = store.load_run(run_id)

                if run:
                    # Add run node
                    nodes.append(
                        {
                            "id": run_id,
                            "type": "run",
                            "label": run.get("run_name", run_id[:8]),
                            "metadata": {
                                "pipeline_name": run.get("pipeline_name"),
                                "status": run.get("status"),
                                "project": run.get("project"),
                            },
                        },
                    )

                    # Add edge: run produces artifact
                    edges.append(
                        {
                            "id": f"{run_id}->{artifact_id}",
                            "source": run_id,
                            "target": artifact_id,
                            "type": "produces",
                            "label": artifact.get("step", ""),
                        },
                    )

                    # Find input artifacts (from DAG/steps metadata)
                    metadata = run.get("metadata", {})
                    # dag = metadata.get("dag", {})
                    steps = metadata.get("steps", {})

                    # Get step that produced this artifact
                    artifact_step = artifact.get("step")
                    if artifact_step and artifact_step in steps:
                        step_info = steps.get(artifact_step, {})
                        inputs = step_info.get("inputs", [])

                        # Find artifacts that were inputs to this step
                        for input_name in inputs:
                            # Search for artifact with this name from the same run
                            input_artifacts = [
                                a for a in all_artifacts if a.get("name") == input_name and a.get("run_id") == run_id
                            ]
                            for input_artifact in input_artifacts:
                                input_id = input_artifact.get("artifact_id")
                                if input_id and input_id not in visited_artifacts:
                                    visited_artifacts.add(input_id)
                                    nodes.append(
                                        {
                                            "id": input_id,
                                            "type": "artifact",
                                            "label": input_artifact.get("name", input_id),
                                            "artifact_type": input_artifact.get("type", "unknown"),
                                            "metadata": {
                                                "created_at": input_artifact.get("created_at"),
                                                "properties": input_artifact.get("properties", {}),
                                            },
                                        },
                                    )

                                # Add edge: input artifact consumed by run
                                edges.append(
                                    {
                                        "id": f"{input_id}->{run_id}",
                                        "source": input_id,
                                        "target": run_id,
                                        "type": "consumes",
                                        "label": artifact_step,
                                    },
                                )

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_artifacts": len([n for n in nodes if n["type"] == "artifact"]),
                "total_runs": len([n for n in nodes if n["type"] == "run"]),
                "depth_used": depth,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build lineage: {str(e)}")


@router.get("/{artifact_id}")
async def get_asset(artifact_id: str):
    """Get details for a specific asset."""
    asset = _find_asset(artifact_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/{artifact_id}/download")
async def download_asset(artifact_id: str):
    """Download the artifact file referenced by metadata."""
    asset, _ = _find_asset_with_store(artifact_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    artifact_path = asset.get("path")
    if not artifact_path:
        raise HTTPException(status_code=404, detail="Artifact path not available")

    file_path = Path(artifact_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


def _find_asset(artifact_id: str):
    asset, _ = _find_asset_with_store(artifact_id)
    return asset


def _find_asset_with_store(artifact_id: str):
    for project_name, store in _iter_metadata_stores():
        asset = store.load_artifact(artifact_id)
        if asset:
            if project_name and not asset.get("project"):
                asset["project"] = project_name
            return asset, store
    return None, None

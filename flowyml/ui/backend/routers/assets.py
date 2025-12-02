from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.project import ProjectManager
from pathlib import Path
from flowyml.ui.backend.dependencies import get_store
import shutil
import asyncio
import contextlib

router = APIRouter()


def _save_file_sync(src, dst):
    with open(dst, "wb") as buffer:
        shutil.copyfileobj(src, buffer)


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


class AssetCreate(BaseModel):
    artifact_id: str
    name: str
    asset_type: str = Field(..., alias="type")
    run_id: str
    step: str
    project: str | None = None
    metadata: dict = {}
    value: str | None = None


@router.post("/")
async def create_asset(asset: AssetCreate):
    """Create or update an asset metadata."""
    try:
        store = get_store()

        # Prepare metadata
        metadata = asset.metadata.copy()
        metadata.update(
            {
                "name": asset.name,
                "type": asset.asset_type,
                "run_id": asset.run_id,
                "step": asset.step,
                "project": asset.project,
                "value": asset.value,
            },
        )

        store.save_artifact(asset.artifact_id, metadata)
        return {"status": "success", "artifact_id": asset.artifact_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{artifact_id}/upload")
async def upload_asset_content(artifact_id: str, file: UploadFile = File(...)):
    """Upload content for an artifact."""
    try:
        store = get_store()

        # Get existing metadata to find path or create a new one
        existing = store.load_artifact(artifact_id)

        if not existing:
            raise HTTPException(status_code=404, detail="Artifact metadata not found. Create metadata first.")

        # Determine storage path
        # We use the LocalArtifactStore logic here since the backend is running locally relative to itself
        from flowyml.storage.artifacts import LocalArtifactStore
        from flowyml.utils.config import get_config

        config = get_config()
        artifact_store = LocalArtifactStore(base_path=config.artifacts_dir)

        # Construct a path if not present
        if not existing.get("path"):
            # Create a path structure: project/run_id/artifact_id/filename
            project = existing.get("project", "default")
            run_id = existing.get("run_id", "unknown")
            filename = file.filename or "content"
            rel_path = f"{project}/{run_id}/{artifact_id}/{filename}"
        else:
            rel_path = existing.get("path")
            # If path is absolute, make it relative to artifacts dir if possible, or just use it
            # But LocalArtifactStore expects relative paths usually, or handles absolute ones

        # Save the file
        full_path = artifact_store.base_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _save_file_sync, file.file, full_path)

        # Update metadata with path
        existing["path"] = str(rel_path)
        store.save_artifact(artifact_id, existing)

        return {"status": "success", "path": str(rel_path)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{artifact_id}")
async def delete_asset(artifact_id: str):
    """Delete an asset and its file."""
    try:
        store = get_store()

        # Get metadata to find path
        asset = store.load_artifact(artifact_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Delete file if it exists locally (since backend is local to itself)
        path = asset.get("path")
        if path:
            from flowyml.storage.artifacts import LocalArtifactStore
            from flowyml.utils.config import get_config

            config = get_config()
            artifact_store = LocalArtifactStore(base_path=config.artifacts_dir)

            with contextlib.suppress(Exception):
                artifact_store.delete(path)

        # Delete metadata
        store.delete_artifact(artifact_id)

        return {"status": "success", "artifact_id": artifact_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_asset_stats(project: str | None = None):
    """Get statistics about assets for the dashboard."""
    try:
        combined_assets = []
        for project_name, store in _iter_metadata_stores():
            if project and project_name and project != project_name:
                continue

            assets = store.list_assets(limit=1000)
            for asset in assets:
                combined_assets.append((asset, project_name))

        assets = _dedupe_assets(combined_assets)

        if project:
            assets = [a for a in assets if a.get("project") == project]

        # Calculate statistics
        total_assets = len(assets)

        # Count by type
        type_counts = {}
        for asset in assets:
            asset_type = asset.get("type", "unknown")
            type_counts[asset_type] = type_counts.get(asset_type, 0) + 1

        # Calculate total storage (if size info available)
        total_storage = sum(asset.get("size_bytes", 0) for asset in assets)

        # Get recent assets (last 10)
        sorted_assets = sorted(
            assets,
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )
        recent_assets = sorted_assets[:10]

        # Count by project
        project_counts = {}
        for asset in assets:
            proj = asset.get("project", "default")
            project_counts[proj] = project_counts.get(proj, 0) + 1

        return {
            "total_assets": total_assets,
            "by_type": type_counts,
            "total_storage_bytes": total_storage,
            "recent_assets": recent_assets,
            "by_project": project_counts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/search")
async def search_assets(q: str, limit: int = 50, project: str | None = None):
    """Search assets by name or properties."""
    try:
        combined_assets = []
        for project_name, store in _iter_metadata_stores():
            if project and project_name and project != project_name:
                continue

            assets = store.list_assets(limit=1000)
            for asset in assets:
                combined_assets.append((asset, project_name))

        assets = _dedupe_assets(combined_assets)

        if project:
            assets = [a for a in assets if a.get("project") == project]

        # Simple fuzzy search in name, type, and step
        query_lower = q.lower()
        matching_assets = []

        for asset in assets:
            name = asset.get("name", "").lower()
            asset_type = asset.get("type", "").lower()
            step = asset.get("step", "").lower()

            # Check if query matches any field
            if query_lower in name or query_lower in asset_type or query_lower in step:
                matching_assets.append(asset)

        return {
            "assets": matching_assets[:limit],
            "total": len(matching_assets),
            "query": q,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")


@router.get("/lineage")
async def get_asset_lineage(
    asset_id: str | None = None,
    project: str | None = None,
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


class ProjectUpdate(BaseModel):
    project_name: str


@router.put("/{artifact_id}/project")
async def update_asset_project(artifact_id: str, update: ProjectUpdate):
    """Update the project for an asset."""
    try:
        _, store = _find_asset_with_store(artifact_id)
        if not store:
            raise HTTPException(status_code=404, detail="Asset not found")

        store.update_artifact_project(artifact_id, update.project_name)
        return {"status": "success", "project": update.project_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

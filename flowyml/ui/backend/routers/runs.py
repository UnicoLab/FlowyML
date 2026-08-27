from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.project import ProjectManager
import json
from flowyml.ui.backend.dependencies import get_store

from loguru import logger

router = APIRouter()

#: Upper bound on any client-supplied page size. Without it a request such as
#: `?limit=100000000` makes the server materialise an unbounded result set.
MAX_PAGE_SIZE = 1000



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
    limit: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    project: str | None = None,
    pipeline_name: str | None = None,
    status: str | None = None,
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

        # Auto-sync cloud status for remote runs still in submitted/running
        synced_runs = []
        for run in runs:
            if run.get("status") in ("submitted", "running"):
                metadata = run.get("metadata", {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except Exception:
                        metadata = {}
                if metadata.get("remote_job_id"):
                    try:
                        store = get_store()
                        run = _sync_cloud_status(run, store)
                    except Exception:
                        pass
            synced_runs.append(run)

        return {"runs": synced_runs}
    except Exception as e:
        # See assets.list_assets: a 200 with an empty list hides an outage.
        logger.exception("Failed to list runs")
        raise HTTPException(status_code=500, detail=f"Failed to list runs: {e}") from e


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
    """Get details for a specific run.

    For remote (cloud) runs that are still 'submitted', automatically
    syncs the latest status from the cloud orchestrator.
    """
    run, store = _find_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # ── Auto-sync cloud status for remote runs ──────────────────────────
    if run.get("status") in ("submitted", "running"):
        run = _sync_cloud_status(run, store)

    # Mark dead steps
    dead_steps = _get_dead_steps(run_id)
    if dead_steps and "steps" in run:
        for step_name in dead_steps:
            if step_name in run["steps"]:
                # Only mark as dead if it was running
                if run["steps"][step_name].get("status") == "running":
                    run["steps"][step_name]["status"] = "dead"
                    run["steps"][step_name]["success"] = False

    # Inject heartbeat timestamps
    with _heartbeat_lock:
        if run_id in _heartbeat_timestamps:
            for step_name, ts in _heartbeat_timestamps[run_id].items():
                if step_name in run.get("steps", {}):
                    run["steps"][step_name]["last_heartbeat"] = ts
            for step_name, metrics in _step_metrics.get(run_id, {}).items():
                if step_name in run.get("steps", {}):
                    run["steps"][step_name]["metrics"] = metrics

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


def _sync_cloud_status(run: dict, store: SQLiteMetadataStore) -> dict:
    """Sync run status from cloud orchestrator (Vertex AI, etc.).

    Called when a run has status 'submitted' or 'running' to pull the
    latest execution state from the cloud provider and update the
    local metadata DB.

    Args:
        run: The run dict from the metadata store.
        store: The metadata store to update.

    Returns:
        Updated run dict.
    """
    import logging

    logger = logging.getLogger("flowyml.ui.cloud_sync")

    # Get remote job ID — may be at top level or in metadata
    metadata = run.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}

    remote_job_id = run.get("remote_job_id") or metadata.get("remote_job_id")
    platform = run.get("platform") or metadata.get("platform") or metadata.get("orchestrator_type")

    # Infer platform from remote_job_id format if not explicitly set
    if not platform and remote_job_id:
        if "pipelineJobs" in remote_job_id or "customJobs" in remote_job_id:
            platform = "vertex_ai"
        elif remote_job_id.startswith("arn:aws:"):
            platform = "sagemaker"
        elif "microsoft" in remote_job_id.lower() or "azure" in remote_job_id.lower():
            platform = "azure_ml"

    supported_platforms = ("vertex_ai", "gcp", "sagemaker", "aws", "azure_ml", "azure")
    if not remote_job_id or platform not in supported_platforms:
        return run

    try:
        from google.cloud import aiplatform

        # Extract project and location from the job resource name
        # Format: projects/{id}/locations/{loc}/pipelineJobs/{name}
        parts = remote_job_id.split("/")
        if len(parts) >= 6:
            project = parts[1]
            location = parts[3]
        else:
            return run

        aiplatform.init(project=project, location=location)
        job = aiplatform.PipelineJob.get(remote_job_id)

        # Map GCP state to FlowyML status
        state_map = {
            "PIPELINE_STATE_QUEUED": "submitted",
            "PIPELINE_STATE_PENDING": "submitted",
            "PIPELINE_STATE_RUNNING": "running",
            "PIPELINE_STATE_SUCCEEDED": "completed",
            "PIPELINE_STATE_FAILED": "failed",
            "PIPELINE_STATE_CANCELLING": "stopping",
            "PIPELINE_STATE_CANCELLED": "cancelled",
            "PIPELINE_STATE_PAUSED": "paused",
        }
        gcp_state = job.state.name if job.state else "UNKNOWN"
        new_status = state_map.get(gcp_state, run.get("status", "unknown"))

        # Extract task details (GCP groups)
        # Task states use different enum names than pipeline states
        task_state_map = {
            "QUEUED": "submitted",
            "PENDING": "submitted",
            "RUNNING": "running",
            "SUCCEEDED": "completed",
            "FAILED": "failed",
            "CANCELLING": "stopping",
            "CANCELLED": "cancelled",
            "SKIPPED": "skipped",
            "NOT_TRIGGERED": "skipped",
        }
        cloud_groups = {}
        task_details = job.task_details or []
        for task in task_details:
            task_state = task.state.name if task.state else "UNKNOWN"
            task_status = task_state_map.get(task_state, state_map.get(task_state, "unknown"))
            error_msg = task.error.message if task.error and task.error.message else None
            # Extract per-task timing
            task_duration = None
            task_start = None
            task_end = None
            try:
                if task.start_time and task.end_time:
                    task_duration = (task.end_time - task.start_time).total_seconds()
                    task_start = task.start_time.isoformat()
                    task_end = task.end_time.isoformat()
            except Exception:
                pass
            cloud_groups[task.task_name] = {
                "status": task_status,
                "success": task_status == "completed",
                "error": error_msg,
                "duration": task_duration,
                "start_time": task_start,
                "end_time": task_end,
            }

        # Build dashboard URL
        # remote_job_id format: projects/{project_num}/locations/{loc}/pipelineJobs/{job_id}
        job_short = remote_job_id.split("/")[-1]
        # Resolve project ID — GCP console needs project ID, not number
        project_id = project  # default from remote_job_id (may be a number)
        try:
            # If it looks like a number, try to resolve to project ID
            if project.isdigit():
                # Try gcloud default project first
                import subprocess

                result = subprocess.run(
                    ["gcloud", "config", "get-value", "project"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                gcloud_project = result.stdout.strip()
                if gcloud_project and not gcloud_project.isdigit():
                    project_id = gcloud_project
        except Exception:
            pass
        # The console URL format for Vertex AI Pipelines:
        dashboard_url = f"https://console.cloud.google.com/vertex-ai/pipelines/runs/{job_short}?project={project_id}"

        # Update the run dict
        run["status"] = new_status
        run["is_remote"] = True
        run["remote_platform"] = "vertex_ai"
        run["dashboard_url"] = dashboard_url
        run["remote_job_id"] = remote_job_id
        run["cloud_state"] = gcp_state
        run["cloud_groups"] = cloud_groups

        # ── Merge cloud status into existing steps ──────────────────────
        # Build a mapping: execution_group → cloud group name
        # GCP names groups as "flowyml-step-group", "flowyml-step-group-2", etc.
        # The original steps have execution_group metadata.
        existing_steps = run.get("steps", {})
        if existing_steps and cloud_groups:
            # Build group name → status lookup from cloud_groups
            # Also build execution_group → cloud_group_name mapping
            # by matching the group index to the DAG execution order
            dag = run.get("dag", {})
            dag_nodes = dag.get("nodes", []) if dag else []

            # Collect all unique execution groups in order
            seen_groups = []
            for node in dag_nodes:
                # Find the step's execution_group
                step_data = existing_steps.get(node.get("id", ""), {})
                eg = step_data.get("execution_group", "")
                if eg and eg not in seen_groups:
                    seen_groups.append(eg)

            # Map ordered execution groups to GCP group names
            # GCP uses: flowyml-step-group, flowyml-step-group-2, flowyml-step-group-3, ...
            group_name_map = {}
            sorted_cloud_names = sorted(
                [n for n in cloud_groups if n.startswith("flowyml-step-group")],
                key=lambda x: int(x.split("-")[-1]) if x.split("-")[-1].isdigit() else 0,
            )
            for idx, eg in enumerate(seen_groups):
                if idx < len(sorted_cloud_names):
                    group_name_map[eg] = sorted_cloud_names[idx]

            # Now update each step's status and timing from its cloud group
            for _step_name, step_data in existing_steps.items():
                if not isinstance(step_data, dict):
                    continue
                eg = step_data.get("execution_group", "")
                cloud_group_name = group_name_map.get(eg)
                if cloud_group_name and cloud_group_name in cloud_groups:
                    cg = cloud_groups[cloud_group_name]
                    step_data["status"] = cg["status"]
                    step_data["success"] = cg["success"]
                    step_data["cloud_group"] = cloud_group_name
                    # Propagate group timing to steps
                    if cg.get("duration") and not step_data.get("duration"):
                        step_data["duration"] = cg["duration"]
                    if cg.get("start_time"):
                        step_data["start_time"] = cg["start_time"]
                    if cg.get("end_time"):
                        step_data["end_time"] = cg["end_time"]
                    if cg.get("error"):
                        step_data["error"] = cg["error"]

        # Calculate duration if completed
        if new_status in ("completed", "failed", "cancelled"):
            try:
                create_time = job.create_time
                update_time = job.update_time
                if create_time and update_time:
                    duration = (update_time - create_time).total_seconds()
                    run["duration"] = duration
                    run["end_time"] = update_time.isoformat()
            except Exception:
                pass

        # Persist updated status to local DB
        try:
            run_id = run.get("run_id")
            if run_id and store:
                store.update_run_status(run_id, new_status)
                # Also update metadata with cloud info
                updated_meta = metadata.copy()
                updated_meta["cloud_state"] = gcp_state
                updated_meta["dashboard_url"] = dashboard_url
                updated_meta["is_remote"] = True
                if cloud_groups:
                    updated_meta["cloud_steps"] = cloud_groups
                store.save_run(run_id, {**run, "metadata": updated_meta})

                # Auto-discover cloud artifacts for completed runs
                if new_status in ("completed", "failed"):
                    try:
                        _discover_cloud_artifacts_for_run(run, store, logger, platform)
                    except Exception as e:
                        logger.warning("Artifact discovery failed: %s", e)
        except Exception as e:
            logger.warning("Failed to persist cloud status: %s", e)

        logger.info(
            "Cloud sync for %s: %s → %s (%d tasks)",
            run.get("run_id", "?"),
            gcp_state,
            new_status,
            len(cloud_groups),
        )

    except ImportError:
        pass  # google-cloud-aiplatform not installed
    except Exception as e:
        logger.warning("Cloud sync failed for %s: %s", run.get("run_id"), e)

    return run


def _discover_cloud_artifacts_for_run(run: dict, store, logger, platform: str = "vertex_ai"):
    """Discover and register cloud artifacts using the appropriate provider.

    Dispatches to GCP/AWS/Azure provider based on platform, then registers
    discovered artifacts into the local metadata store.
    """
    from flowyml.ui.backend.cloud_providers import get_provider

    provider = get_provider(platform)
    if not provider:
        logger.info("No cloud provider for platform: %s", platform)
        return

    run_id = run.get("run_id")
    if not run_id:
        return

    artifacts = provider.discover_artifacts(run, run_id)
    if not artifacts:
        logger.info("No cloud artifacts found for run %s", run_id)
        return

    for art in artifacts:
        store.save_asset(
            run_id=run_id,
            artifact_id=art.artifact_id,
            name=art.name,
            asset_type=art.artifact_type,
            step=art.step,
            path=art.path,
            size_bytes=art.size_bytes,
            materializer=art.materializer,
            storage=art.storage,
            created_at=art.created_at,
            properties=art.properties,
        )

    logger.info("Discovered %d cloud artifacts for run %s", len(artifacts), run_id)


def _discover_gcs_artifacts_for_run(run: dict, store, logger):
    """Discover and register GCS artifacts for a completed remote run (legacy fallback)."""
    import json as json_mod

    try:
        from google.cloud import storage as gcs_storage
    except ImportError:
        return

    run_id = run.get("run_id")
    if not run_id:
        return

    # Determine bucket name
    bucket_name = None
    try:
        from flowyml.core.stack import get_active_stack

        stack = get_active_stack()
        bucket_name = getattr(stack.artifact_store, "bucket_name", None)
    except Exception:
        pass

    if not bucket_name:
        bucket_name = "flowyml-test-artifacts"

    prefix = f"staging/runs/{run_id}/artifacts/"

    try:
        client = gcs_storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))
    except Exception as e:
        logger.warning("GCS artifact scan failed: %s", e)
        return

    if not blobs:
        return

    # Read meta.json sidecars
    meta_files = {}
    for blob in blobs:
        if blob.name.endswith(".meta.json"):
            try:
                content = blob.download_as_text()
                meta = json_mod.loads(content)
                base = blob.name.rsplit(".meta.json", 1)[0].split("/")[-1]
                meta_files[base] = meta
            except Exception:
                pass

    # Register artifacts
    count = 0
    steps = run.get("steps", {})
    for blob in blobs:
        if blob.name.endswith(".meta.json"):
            continue

        file_name = blob.name.split("/")[-1]
        base_name = file_name.rsplit(".", 1)[0]

        artifact_id = f"{run_id}:{base_name}"
        existing = store.load_artifact(artifact_id)
        if existing:
            continue

        meta = meta_files.get(base_name, {})
        artifact_type = meta.get("artifact_type", meta.get("type", "Unknown"))

        # Find which step produced this artifact
        step = "unknown"
        if isinstance(steps, dict):
            for step_name, step_data in steps.items():
                if isinstance(step_data, dict):
                    if base_name in step_data.get("outputs", []):
                        step = step_name
                        break

        gcs_uri = f"gs://{bucket_name}/{blob.name}"

        artifact_data = {
            "artifact_id": artifact_id,
            "name": base_name,
            "type": artifact_type,
            "run_id": run_id,
            "step": step,
            "path": gcs_uri,
            "size_bytes": blob.size,
            "materializer": meta.get("materializer", "unknown"),
            "storage": "gcs",
            "bucket": bucket_name,
            "created_at": blob.time_created.isoformat() if blob.time_created else None,
            "properties": meta.get("properties", {}),
        }

        store.save_artifact(artifact_id, artifact_data)
        count += 1

    if count > 0:
        logger.info("Discovered %d GCS artifacts for run %s", count, run_id)


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


class HeartbeatRequest(BaseModel):
    step_name: str
    status: str = "running"
    metrics: dict | None = None


# In-memory storage for heartbeat timestamps and metrics
# Format: {run_id: {step_name: last_heartbeat_timestamp}}
_heartbeat_timestamps: dict[str, dict[str, float]] = {}
# Format: {run_id: {step_name: metrics_dict}}
_step_metrics: dict[str, dict[str, dict]] = {}
_heartbeat_lock = __import__("threading").Lock()

# Heartbeat interval in seconds (should match executor's interval)
HEARTBEAT_INTERVAL = 5
# Number of missed heartbeats before marking step as dead
DEAD_THRESHOLD = 3


def _record_heartbeat(run_id: str, step_name: str) -> None:
    """Record heartbeat timestamp for a step."""
    import time

    with _heartbeat_lock:
        if run_id not in _heartbeat_timestamps:
            _heartbeat_timestamps[run_id] = {}
        _heartbeat_timestamps[run_id][step_name] = time.time()


def _record_step_metrics(run_id: str, step_name: str, metrics: dict) -> None:
    """Record metrics for a step."""
    with _heartbeat_lock:
        if run_id not in _step_metrics:
            _step_metrics[run_id] = {}
        _step_metrics[run_id][step_name] = metrics


def _get_dead_steps(run_id: str) -> list[str]:
    """Get list of steps that have missed too many heartbeats."""
    import time

    dead_steps = []
    timeout = HEARTBEAT_INTERVAL * DEAD_THRESHOLD

    with _heartbeat_lock:
        if run_id not in _heartbeat_timestamps:
            return []

        current_time = time.time()
        for step_name, last_heartbeat in _heartbeat_timestamps[run_id].items():
            if current_time - last_heartbeat > timeout:
                dead_steps.append(step_name)

    return dead_steps


def _cleanup_heartbeats(run_id: str) -> None:
    """Remove heartbeat tracking for a completed run."""
    with _heartbeat_lock:
        _heartbeat_timestamps.pop(run_id, None)
        _step_metrics.pop(run_id, None)


@router.post("/{run_id}/steps/{step_name}/heartbeat")
async def step_heartbeat(run_id: str, step_name: str, heartbeat: HeartbeatRequest):
    """Receive heartbeat from a running step.

    Returns:
        dict: Instructions for the step (e.g., {"action": "continue"} or {"action": "stop"})
    """
    store = _find_store_for_run(run_id)

    # Record heartbeat timestamp
    _record_heartbeat(run_id, step_name)

    # Record metrics if present
    if heartbeat.metrics:
        _record_step_metrics(run_id, step_name, heartbeat.metrics)

    # Check if run is marked for stopping
    run = store.load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run_status = run.get("status")
    if run_status in ["stopping", "stopped", "cancelled", "cancelling"]:
        return {"action": "stop"}

    return {"action": "continue"}


@router.get("/{run_id}/dead-steps")
async def get_dead_steps(run_id: str):
    """Get list of steps that appear to be dead (missed heartbeats)."""
    dead_steps = _get_dead_steps(run_id)
    return {"dead_steps": dead_steps}


@router.post("/{run_id}/stop")
async def stop_run(run_id: str):
    """Signal a run to stop."""
    store = _find_store_for_run(run_id)

    try:
        # Update run status to STOPPING
        # This will be picked up by the next heartbeat
        store.update_run_status(run_id, "stopping")
        return {"status": "success", "message": "Stop signal sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class LogChunk(BaseModel):
    content: str
    level: str = "INFO"
    timestamp: str | None = None


@router.post("/{run_id}/steps/{step_name}/logs")
async def post_step_logs(run_id: str, step_name: str, log_chunk: LogChunk):
    """Receive log chunk from a running step."""
    import anyio

    from flowyml.utils.config import get_config

    # Store logs in the runs directory
    runs_dir = get_config().runs_dir
    log_dir = runs_dir / run_id / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{step_name}.log"

    # Append log content
    timestamp = log_chunk.timestamp or ""
    line = f"[{timestamp}] [{log_chunk.level}] {log_chunk.content}\n"

    def write_log():
        with open(log_file, "a") as f:
            f.write(line)

    await anyio.to_thread.run_sync(write_log)

    # Broadcast to WebSocket clients
    try:
        from flowyml.ui.backend.routers.websocket import manager

        await manager.broadcast_log(run_id, step_name, log_chunk.content)
    except Exception:
        pass  # Ignore WebSocket broadcast failures

    return {"status": "success"}


@router.get("/{run_id}/steps/{step_name}/logs")
async def get_step_logs(run_id: str, step_name: str, offset: int = Query(0, ge=0)):
    """Get logs for a specific step.

    For local runs, reads from the local log file.
    For remote runs (Vertex AI), fetches from GCP Cloud Logging.
    """
    import anyio

    from flowyml.utils.config import get_config

    runs_dir = get_config().runs_dir
    log_file = runs_dir / run_id / "logs" / f"{step_name}.log"

    # Try local log file first
    if log_file.exists():

        def read_log():
            with open(log_file) as f:
                return f.read()

        content = await anyio.to_thread.run_sync(read_log)

        # Return content from offset
        if offset > 0 and offset < len(content):
            content = content[offset:]

        return {
            "logs": content,
            "offset": offset + len(content),
            "has_more": False,
        }

    # No local log file — check if this is a remote run and fetch from cloud provider
    store = get_store()
    run = store.load_run(run_id)
    if not run:
        return {"logs": "", "offset": 0, "has_more": False}

    remote_job_id = run.get("remote_job_id") or run.get("metadata", {}).get("remote_job_id")
    if not remote_job_id:
        return {"logs": "", "offset": 0, "has_more": False}

    # Use multi-cloud provider abstraction
    from flowyml.ui.backend.cloud_providers import detect_provider

    provider = detect_provider(run)
    if provider:
        cloud_logs = await anyio.to_thread.run_sync(
            lambda: provider.get_step_logs(run, step_name, remote_job_id),
        )
    else:
        cloud_logs = "[Unsupported cloud platform — no log provider available]"

    return {
        "logs": cloud_logs,
        "offset": len(cloud_logs),
        "has_more": False,
        "source": "cloud_logging",
    }


def _fetch_cloud_logs(run: dict, step_name: str, remote_job_id: str) -> str:
    """Fetch logs from GCP Cloud Logging for a remote pipeline step.

    Maps step_name → execution_group to filter task-level logs from Cloud Logging.
    The logs use execution_group names (e.g. 'data_group'), not flowyml-step-group names.
    """
    import logging

    logger = logging.getLogger("flowyml.ui.cloud_logs")

    try:
        from google.cloud import logging as gcp_logging
    except ImportError:
        return "[Cloud Logging SDK not installed. Run: pip install google-cloud-logging]"

    # Get step's execution group — Cloud Logging uses these as task names
    steps = run.get("steps", {})
    step_data = steps.get(step_name, {})
    execution_group = step_data.get("execution_group", "")

    # Extract job_short from remote_job_id
    # Format: projects/{project}/locations/{loc}/pipelineJobs/{job_id}
    parts = remote_job_id.split("/")
    project_number = parts[1] if len(parts) > 1 else ""
    job_short = parts[-1] if parts else ""

    # Resolve project ID
    project_id = project_number
    try:
        if project_number.isdigit():
            import subprocess

            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            gcloud_project = result.stdout.strip()
            if gcloud_project and not gcloud_project.isdigit():
                project_id = gcloud_project
    except Exception:
        pass

    try:
        client = gcp_logging.Client(project=project_id)

        # Cloud Logging filter — uses resource.labels.pipeline_job_id (not labels.)
        filter_str = f'resource.labels.pipeline_job_id="{job_short}"'
        logger.info("Cloud Logging filter: %s (execution_group=%s)", filter_str, execution_group)

        entries = list(
            client.list_entries(
                filter_=filter_str,
                order_by="timestamp asc",
                max_results=500,
            ),
        )

        if not entries:
            return f"[No Cloud Logging entries found for pipeline: {job_short}]"

        # Format entries, filtering by execution_group if available
        lines = []
        for entry in entries:
            ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
            payload = entry.payload

            if not isinstance(payload, dict):
                if payload:
                    lines.append(f"[{ts}] {payload}")
                continue

            task_name = payload.get("taskName", "")
            inner_payload = payload.get("payload", {})
            inner_task = inner_payload.get("taskName", "") if isinstance(inner_payload, dict) else ""
            effective_task = task_name or inner_task

            # If we have an execution_group filter, skip entries from other groups
            if execution_group and effective_task and effective_task != execution_group:
                # Allow pipeline-level entries (no task name) to pass through
                if effective_task and effective_task != job_short:
                    continue

            # Build human-readable log line
            state = ""
            if isinstance(inner_payload, dict):
                state = inner_payload.get("state", "")
            if not state:
                state = payload.get("state", "")

            message = payload.get("message", "")

            # Extract machine type from cache key metadata
            container_info = ""
            if isinstance(inner_payload, dict):
                container = inner_payload.get("container", {})
                if isinstance(container, dict):
                    resources = container.get("resources", {})
                    machine = resources.get("resolvedMachineType", "")
                    if machine:
                        container_info = f" [machine: {machine}]"

            # Format the line
            if message and state:
                lines.append(f"[{ts}] [{effective_task}] {state} — {message}{container_info}")
            elif state:
                lines.append(f"[{ts}] [{effective_task}] {state}{container_info}")
            elif message:
                lines.append(f"[{ts}] [{effective_task}] {message}{container_info}")

        if not lines:
            if execution_group:
                return f"[No log entries for execution group: {execution_group}]"
            return f"[No parseable log entries for pipeline: {job_short}]"

        header = f"☁️ Cloud Logging — {execution_group or 'all groups'} ({len(lines)} entries)\n{'─' * 60}\n"
        return header + "\n".join(lines)

    except Exception as e:
        logger.warning("Cloud Logging query failed: %s", e)
        return f"[Cloud Logging error: {e}]"


@router.get("/{run_id}/logs")
async def get_run_logs(run_id: str):
    """Get all logs for a run."""
    import anyio

    from flowyml.utils.config import get_config

    runs_dir = get_config().runs_dir
    log_dir = runs_dir / run_id / "logs"

    if not log_dir.exists():
        return {"logs": {}}

    def read_all_logs():
        logs = {}
        for log_file in log_dir.glob("*.log"):
            step_name = log_file.stem
            with open(log_file) as f:
                logs[step_name] = f.read()
        return logs

    logs = await anyio.to_thread.run_sync(read_all_logs)

    return {"logs": logs}


@router.get("/{run_id}/training-history")
async def get_training_history(run_id: str):
    """Get training history (per-epoch metrics) for a run.

    This combines:
    1. Training history from model artifacts (saved by FlowymlKerasCallback)
    2. Per-epoch metrics saved in the metrics table

    Returns a consolidated training history suitable for visualization.
    """
    store = _find_store_for_run(run_id)

    # Get per-epoch metrics from the metrics table
    metrics = store.get_metrics(run_id)

    # Build training history from metrics table
    # Group metrics by step (epoch) and name
    epoch_metrics = {}
    for m in metrics:
        step = m.get("step", 0)
        name = m.get("name", "unknown")
        value = m.get("value", 0)

        if step not in epoch_metrics:
            epoch_metrics[step] = {}
        epoch_metrics[step][name] = value

    # Convert to chart-friendly format
    training_history_from_metrics = {
        "epochs": [],
        "train_loss": [],
        "val_loss": [],
        "train_accuracy": [],
        "val_accuracy": [],
        "mae": [],
        "val_mae": [],
    }

    # Standard metric name mappings
    metric_mappings = {
        "loss": "train_loss",
        "val_loss": "val_loss",
        "accuracy": "train_accuracy",
        "acc": "train_accuracy",
        "val_accuracy": "val_accuracy",
        "val_acc": "val_accuracy",
        "mae": "mae",
        "val_mae": "val_mae",
    }

    # Track custom metrics
    custom_metrics = set()

    if epoch_metrics:
        sorted_epochs = sorted(epoch_metrics.keys())
        for epoch in sorted_epochs:
            training_history_from_metrics["epochs"].append(epoch + 1)  # 1-indexed for display

            epoch_data = epoch_metrics[epoch]
            for metric_name, value in epoch_data.items():
                # Map to standard name or track as custom
                standard_name = metric_mappings.get(metric_name)
                if standard_name:
                    training_history_from_metrics[standard_name].append(value)
                else:
                    # Custom metric
                    if metric_name not in custom_metrics:
                        custom_metrics.add(metric_name)
                        training_history_from_metrics[metric_name] = []
                    training_history_from_metrics[metric_name].append(value)

    # Also try to get training history from model artifacts
    artifacts = store.list_assets(run_id=run_id)
    artifact_history = None

    for artifact in artifacts:
        # Check if artifact has training_history
        if artifact.get("training_history"):
            artifact_history = artifact.get("training_history")
            break
        # Also check in metadata/properties
        metadata = artifact.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        if metadata.get("training_history"):
            artifact_history = metadata.get("training_history")
            break

    # Prefer artifact history if it has more data, otherwise use metrics
    if artifact_history and len(artifact_history.get("epochs", [])) > len(
        training_history_from_metrics.get("epochs", []),
    ):
        final_history = artifact_history
    elif training_history_from_metrics.get("epochs"):
        final_history = training_history_from_metrics
    else:
        final_history = artifact_history or {}

    # Clean up empty arrays
    cleaned_history = {k: v for k, v in final_history.items() if v and (not isinstance(v, list) or len(v) > 0)}

    return {
        "training_history": cleaned_history,
        "has_history": len(cleaned_history.get("epochs", [])) > 0,
        "total_epochs": len(cleaned_history.get("epochs", [])),
        "source": "artifact" if artifact_history else "metrics",
    }

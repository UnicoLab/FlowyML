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


class HeartbeatRequest(BaseModel):
    step_name: str
    status: str = "running"


# In-memory storage for heartbeat timestamps
# Format: {run_id: {step_name: last_heartbeat_timestamp}}
_heartbeat_timestamps: dict[str, dict[str, float]] = {}
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


@router.post("/{run_id}/steps/{step_name}/heartbeat")
async def step_heartbeat(run_id: str, step_name: str, heartbeat: HeartbeatRequest):
    """Receive heartbeat from a running step.

    Returns:
        dict: Instructions for the step (e.g., {"action": "continue"} or {"action": "stop"})
    """
    store = _find_store_for_run(run_id)

    # Record heartbeat timestamp
    _record_heartbeat(run_id, step_name)

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
async def get_step_logs(run_id: str, step_name: str, offset: int = 0):
    """Get logs for a specific step."""
    import anyio

    from flowyml.utils.config import get_config

    runs_dir = get_config().runs_dir
    log_file = runs_dir / run_id / "logs" / f"{step_name}.log"

    if not log_file.exists():
        return {"logs": "", "offset": 0, "has_more": False}

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
        "has_more": False,  # For now, always return all available
    }


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

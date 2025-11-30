"""Model metrics logging API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Security, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Any

from flowyml.ui.backend.auth import verify_api_token, security
from flowyml.storage.metadata import SQLiteMetadataStore
from flowyml.core.project import ProjectManager
from flowyml.utils.config import get_config

router = APIRouter()


def require_permission(permission: str):
    """Create dependency enforcing a given permission."""

    async def _verify(credentials: HTTPAuthorizationCredentials = Security(security)):
        return await verify_api_token(credentials, required_permission=permission)

    return _verify


def get_project_manager() -> ProjectManager:
    """Get a project manager rooted at configured projects dir."""
    config = get_config()
    return ProjectManager(str(config.projects_dir))


def get_global_store() -> SQLiteMetadataStore:
    """Metadata store for shared metrics."""
    config = get_config()
    return SQLiteMetadataStore(str(config.metadata_db))


class MetricsLogRequest(BaseModel):
    """Payload for logging production model metrics."""

    project: str = Field(..., description="Project identifier")
    model_name: str = Field(..., description="Name of the model emitting metrics")
    metrics: dict[str, float] = Field(..., description="Dictionary of metric_name -> value")
    run_id: str | None = Field(None, description="Related run identifier (optional)")
    environment: str | None = Field(None, description="Environment label (e.g., prod, staging)")
    tags: dict[str, Any] | None = Field(default_factory=dict, description="Optional metadata tags")


@router.post("/log")
async def log_model_metrics(
    payload: MetricsLogRequest,
    token_data: dict = Depends(require_permission("write")),
):
    """Log production metrics for a model.

    Requires tokens with the `write` permission. Project-scoped tokens
    may only submit metrics for their project.
    """
    if token_data.get("project") and token_data["project"] != payload.project:
        raise HTTPException(
            status_code=403,
            detail=f"Token is scoped to project '{token_data['project']}'",
        )

    if not payload.metrics:
        raise HTTPException(status_code=400, detail="metrics dictionary cannot be empty")

    numeric_metrics = {}
    for name, value in payload.metrics.items():
        try:
            numeric_metrics[name] = float(value)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail=f"Metric '{name}' must be numeric.",
            )

    project_manager = get_project_manager()
    project = project_manager.get_project(payload.project)
    if not project:
        project = project_manager.create_project(payload.project)

    shared_store = get_global_store()
    shared_store.log_model_metrics(
        project=payload.project,
        model_name=payload.model_name,
        metrics=numeric_metrics,
        run_id=payload.run_id,
        environment=payload.environment,
        tags=payload.tags,
    )

    project.log_model_metrics(
        model_name=payload.model_name,
        metrics=numeric_metrics,
        run_id=payload.run_id,
        environment=payload.environment,
        tags=payload.tags,
    )

    return {
        "project": payload.project,
        "model_name": payload.model_name,
        "logged_metrics": list(numeric_metrics.keys()),
        "message": "Metrics logged successfully",
    }


@router.get("")
async def list_model_metrics(
    project: str | None = Query(default=None, description="Filter by project"),
    model_name: str | None = Query(default=None, description="Filter by model"),
    limit: int = Query(default=100, ge=1, le=500),
    token_data: dict = Depends(require_permission("read")),
):
    """Retrieve the latest logged model metrics."""
    if token_data.get("project"):
        if project and token_data["project"] != project:
            raise HTTPException(
                status_code=403,
                detail=f"Token is scoped to project '{token_data['project']}'",
            )
        project = token_data["project"]

    store: SQLiteMetadataStore
    if project:
        project_manager = get_project_manager()
        project_obj = project_manager.get_project(project)
        if not project_obj:
            raise HTTPException(status_code=404, detail=f"Project '{project}' not found")
        store = project_obj.metadata_store
    else:
        store = get_global_store()

    records = store.list_model_metrics(project=project, model_name=model_name, limit=limit)
    return {"metrics": records}


@router.get("/observability/orchestrator")
async def get_orchestrator_metrics():
    """Get orchestrator-level performance metrics."""
    from datetime import datetime, timedelta
    import sqlite3

    store = get_global_store()
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()

    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    cursor.execute("SELECT COUNT(*) FROM runs WHERE created_at >= ?", (thirty_days_ago,))
    total_runs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT status, COUNT(*) FROM runs WHERE created_at >= ? GROUP BY status",
        (thirty_days_ago,),
    )
    status_counts = dict(cursor.fetchall())

    cursor.execute(
        "SELECT AVG(duration) FROM runs WHERE created_at >= ? AND duration IS NOT NULL",
        (thirty_days_ago,),
    )
    avg_duration = cursor.fetchone()[0] or 0

    conn.close()

    completed = status_counts.get("completed", 0)
    success_rate = completed / total_runs if total_runs > 0 else 0

    return {
        "total_runs": total_runs,
        "success_rate": success_rate,
        "avg_duration_seconds": avg_duration,
        "status_distribution": status_counts,
        "period_days": 30,
    }


@router.get("/observability/cache")
async def get_cache_metrics():
    """Get cache performance metrics."""
    from datetime import datetime, timedelta
    import sqlite3
    import json as json_lib

    store = get_global_store()
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()

    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    cursor.execute("SELECT metadata FROM runs WHERE created_at >= ?", (thirty_days_ago,))

    total_steps, cached_steps = 0, 0
    for row in cursor.fetchall():
        if not row[0]:
            continue
        try:
            metadata = json_lib.loads(row[0])
            for step_data in metadata.get("steps", {}).values():
                total_steps += 1
                if step_data.get("cached"):
                    cached_steps += 1
        except Exception:
            continue

    conn.close()
    cache_hit_rate = cached_steps / total_steps if total_steps > 0 else 0

    return {
        "total_steps": total_steps,
        "cached_steps": cached_steps,
        "cache_hit_rate": cache_hit_rate,
        "period_days": 30,
    }

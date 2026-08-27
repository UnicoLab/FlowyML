"""Pipeline execution API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Any
from flowyml.ui.backend.auth import verify_api_token, security
import importlib
import platform
import time

from loguru import logger

router = APIRouter()

#: Process start time, captured at import, used to report server uptime.
_SERVER_START_TIME = time.time()


def _format_uptime(seconds: float) -> str:
    """Render a duration as a compact human-readable string (e.g. "2d 3h 4m")."""
    total = int(seconds)
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def require_permission(permission: str):
    """Create a dependency for checking permissions."""

    async def _verify(credentials: HTTPAuthorizationCredentials = Security(security)):
        return await verify_api_token(credentials, required_permission=permission)

    return _verify


class PipelineExecutionRequest(BaseModel):
    """Pipeline execution request."""

    pipeline_module: str  # e.g., "my_pipelines.training"
    pipeline_name: str  # e.g., "training_pipeline"
    parameters: dict[str, Any] = {}
    project: str | None = None
    dry_run: bool = False  # If True, validate but don't execute
    retry_count: int = 0  # Number of retries on failure (0-5)


class TokenRequest(BaseModel):
    """API token creation request."""

    name: str
    project: str | None = None
    permissions: list = ["read", "write", "execute"]


@router.post("/execute")
async def execute_pipeline(
    request: PipelineExecutionRequest,
    token_data: dict = Depends(require_permission("execute")),
):
    """Execute a pipeline.

    Requires 'execute' permission.

    Example request:
    ```json
    {
        "pipeline_module": "my_pipelines.training",
        "pipeline_name": "training_pipeline",
        "parameters": {"epochs": 10},
        "project": "my_project",
        "dry_run": false
    }
    ```
    """
    try:
        # Check project scope if token is project-specific
        if token_data.get("project") and token_data["project"] != request.project:
            raise HTTPException(
                status_code=403,
                detail=f"Token is scoped to project '{token_data['project']}'",
            )

        if request.dry_run:
            return {
                "status": "validated",
                "pipeline": request.pipeline_name,
                "module": request.pipeline_module,
                "parameters": request.parameters,
                "message": "Pipeline configuration is valid (dry run)",
            }

        # Import the pipeline module
        try:
            module = importlib.import_module(request.pipeline_module)
        except ImportError as e:
            raise HTTPException(
                status_code=404,
                detail=f"Pipeline module not found: {request.pipeline_module}. Error: {str(e)}",
            )

        # Get the pipeline object
        if not hasattr(module, request.pipeline_name):
            raise HTTPException(
                status_code=404,
                detail=f"Pipeline '{request.pipeline_name}' not found in module '{request.pipeline_module}'",
            )

        pipeline = getattr(module, request.pipeline_name)

        # Execute the pipeline with retry policy if specified
        run_kwargs = request.parameters.copy()

        if request.retry_count > 0:
            from flowyml.core.retry_policy import OrchestratorRetryPolicy

            run_kwargs["retry_policy"] = OrchestratorRetryPolicy(
                max_attempts=min(request.retry_count, 5),  # Cap at 5
            )

        result = pipeline.run(**run_kwargs)

        return {
            "status": "completed",
            "run_id": result.run_id if hasattr(result, "run_id") else None,
            "pipeline": request.pipeline_name,
            "retry_count": request.retry_count,
            "message": "Pipeline executed successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}",
        )


@router.post("/tokens")
async def create_token(
    request: TokenRequest,
    token_data: dict = Depends(require_permission("admin")),
):
    """Create a new API token.

    Requires 'admin' permission or can be called without auth for initial setup.
    """
    from flowyml.ui.backend.auth import token_manager

    try:
        token = token_manager.create_token(
            name=request.name,
            project=request.project,
            permissions=request.permissions,
        )

        return {
            "token": token,
            "name": request.name,
            "project": request.project,
            "permissions": request.permissions,
            "message": "Token created successfully. Save this token - it won't be shown again!",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create token: {str(e)}",
        )


@router.get("/tokens")
async def list_tokens():
    """List all API tokens (without revealing token values).

    Deliberately unauthenticated: the UI calls this before any token exists in
    order to decide whether to offer first-time setup, and the auth middleware
    already gates the whole API in production. Token *values* are never
    returned - only labels, scopes and timestamps.
    """
    from flowyml.ui.backend.auth import token_manager

    return {"tokens": token_manager.list_tokens()}


@router.delete("/tokens/{token_ref}")
async def revoke_token(token_ref: str):
    """Revoke an API token by its public id, or by name.

    ``token_ref`` is matched against the opaque ``id`` returned by
    ``GET /tokens`` first; if nothing matches it is treated as a token *name*,
    which revokes every token carrying that label. Names are user-supplied and
    need not be unique, so the response reports how many were removed.
    """
    from flowyml.ui.backend.auth import token_manager

    if token_manager.revoke_token_by_id(token_ref):
        return {"revoked": 1, "message": f"Token '{token_ref}' revoked"}

    revoked = token_manager.revoke_tokens_by_name(token_ref)
    if revoked == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No API token matches id or name '{token_ref}'",
        )

    return {
        "revoked": revoked,
        "message": f"Revoked {revoked} token(s) named '{token_ref}'",
    }


@router.get("/info")
async def get_server_info():
    """Report runtime facts about this server for the Settings page.

    Every field is derived from the live process. The UI previously fell back
    to hard-coded placeholders here (version "0.1.0", database "PostgreSQL"),
    which misreported both the release and the storage backend in use.
    """
    from flowyml import __version__
    from flowyml.ui.backend.security import is_production

    database = "unknown"
    try:
        from flowyml.ui.backend.dependencies import get_store

        store = get_store()
        engine = getattr(store, "engine", None)
        if engine is not None:
            database = engine.dialect.name
        else:  # pragma: no cover - store implementations without a SQLAlchemy engine
            database = type(store).__name__
    except Exception as exc:  # pragma: no cover - never fail the settings page
        logger.warning(f"Could not determine database backend: {exc}")

    uptime_seconds = max(0.0, time.time() - _SERVER_START_TIME)

    return {
        "version": __version__,
        "environment": "production" if is_production() else "development",
        "database": database,
        "uptime": _format_uptime(uptime_seconds),
        "uptime_seconds": round(uptime_seconds, 3),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }


@router.post("/tokens/init")
async def initialize_first_token():
    """Create the first admin token (no auth required).

    This endpoint can only be used if no tokens exist yet.
    """
    from flowyml.ui.backend.auth import token_manager

    if token_manager.list_tokens():
        raise HTTPException(
            status_code=403,
            detail="Tokens already exist. Use /api/execution/tokens with admin token to create more.",
        )

    token = token_manager.create_token(
        name="Initial Admin Token",
        project=None,
        permissions=["read", "write", "execute", "admin"],
    )

    return {
        "token": token,
        "message": "Initial admin token created. Save this token - it won't be shown again!",
        "next_steps": "Use this token to create additional tokens via /api/execution/tokens",
    }

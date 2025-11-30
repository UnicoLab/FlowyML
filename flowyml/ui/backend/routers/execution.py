"""Pipeline execution API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Any
from flowyml.ui.backend.auth import verify_api_token, security
import importlib

router = APIRouter()


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
            from flowyml.core.retry import OrchestratorRetryPolicy

            run_kwargs["retry_policy"] = OrchestratorRetryPolicy(
                max_retries=min(request.retry_count, 5),  # Cap at 5
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
    """List all API tokens (without revealing token values)."""
    from flowyml.ui.backend.auth import token_manager

    # Allow listing tokens without auth (for UI to check if any exist)
    return {"tokens": token_manager.list_tokens()}


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

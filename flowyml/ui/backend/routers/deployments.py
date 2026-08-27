"""Deployment management API for model serving."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import anyio
import secrets

from flowyml.ui.backend.artifact_paths import ArtifactPathError, resolve_within_root
from flowyml.utils.packages import InvalidPackageNameError, validate_requirement

router = APIRouter(prefix="/deployments", tags=["deployments"])

#: Upper bound on how many log lines a single request may pull back.
MAX_LOG_LINES = 10000


def _artifact_file_exists(artifact_path: str | None) -> bool:
    """Whether an artifact's file is present in the configured artifacts directory.

    The previous implementation joined the path onto a hard-coded
    "/app/artifacts", which is only correct inside the project's Docker image.
    Anyone running ``flowyml ui`` from a pip install has their artifacts under
    the configured artifacts directory, so this always returned False and the
    deployments page labelled every model "Missing".

    Resolution is confined to the artifacts root, so an artifact path pointing
    outside it reports False instead of probing the host filesystem.
    """
    if not artifact_path:
        return False

    from flowyml.utils.config import get_config

    try:
        resolved = resolve_within_root(artifact_path, Path(get_config().artifacts_dir))
    except ArtifactPathError:
        return False

    return resolved.exists()


# ==================== Schemas ====================

# Common ML framework dependencies that can be installed on-demand
ML_DEPENDENCIES = {
    "keras": ["keras", "tensorflow"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["torch", "torchvision"],
    "sklearn": ["scikit-learn"],
    "xgboost": ["xgboost"],
    "lightgbm": ["lightgbm"],
    "onnx": ["onnx", "onnxruntime"],
}


class DeploymentConfig(BaseModel):
    """Configuration for a model deployment."""

    rate_limit: int = Field(default=100, description="Requests per minute")
    timeout_seconds: int = Field(default=30, description="Request timeout")
    max_batch_size: int = Field(default=1, description="Max batch size for predictions")
    enable_cors: bool = Field(default=True, description="Enable CORS")
    ttl_seconds: int | None = Field(None, description="Auto-destroy after N seconds (None = never)")
    install_dependencies: list[str] = Field(
        default_factory=list,
        description="ML dependencies to install on server (e.g., ['keras', 'sklearn'])",
    )


class DeploymentCreate(BaseModel):
    """Request to create a new deployment."""

    name: str = Field(..., description="Human-readable name for the deployment")
    model_artifact_id: str = Field(..., description="ID of the model artifact to deploy")
    model_version: str | None = Field(None, description="Specific version to deploy")
    port: int | None = Field(None, description="Port to serve on (auto-assigned if not provided)")
    config: DeploymentConfig = Field(default_factory=DeploymentConfig)


class DeploymentResponse(BaseModel):
    """Deployment details response."""

    id: str  # noqa: A003
    name: str
    model_artifact_id: str
    model_version: str | None
    status: str  # pending, starting, running, stopping, stopped, error
    port: int
    api_token: str
    endpoint_url: str
    config: DeploymentConfig
    created_at: str
    started_at: str | None
    stopped_at: str | None
    expires_at: str | None = None
    error_message: str | None = None


class PredictRequest(BaseModel):
    """Prediction request for deployed model."""

    data: dict = Field(..., description="Input data for prediction")


class PredictResponse(BaseModel):
    """Prediction response from deployed model."""

    prediction: dict
    latency_ms: float
    model_version: str


# ==================== In-Memory State (for MVP) ====================
# TODO: Move to database for production

_deployments: dict[str, dict] = {}
_next_port = 9000  # Start port allocation from 9000


def _generate_token() -> str:
    """Generate a secure API token."""
    return f"flowy_{secrets.token_urlsafe(32)}"


def _allocate_port() -> int:
    """Allocate the next available port."""
    global _next_port
    port = _next_port
    _next_port += 1
    return port


# ==================== Endpoints ====================


@router.get("/")
async def list_deployments() -> list[DeploymentResponse]:
    """List all deployments."""
    return [DeploymentResponse(**d) for d in _deployments.values()]


@router.post("/", status_code=201)
async def create_deployment(
    request: DeploymentCreate,
    background_tasks: BackgroundTasks,
) -> DeploymentResponse:
    """Create a new model deployment."""
    from datetime import timedelta

    deployment_id = str(uuid4())
    port = request.port or _allocate_port()
    api_token = _generate_token()

    # Calculate expiry time if TTL is set
    created_at = datetime.now()
    expires_at = None
    ttl_seconds = request.config.ttl_seconds
    if ttl_seconds and ttl_seconds > 0:
        expires_at = (created_at + timedelta(seconds=ttl_seconds)).isoformat()

    deployment = {
        "id": deployment_id,
        "name": request.name,
        "model_artifact_id": request.model_artifact_id,
        "model_version": request.model_version,
        "status": "pending",
        "port": port,
        "api_token": api_token,
        "endpoint_url": f"http://localhost:{port}",
        "config": request.config.model_dump(),
        "created_at": created_at.isoformat(),
        "started_at": None,
        "stopped_at": None,
        "expires_at": expires_at,
        "error_message": None,
    }

    _deployments[deployment_id] = deployment

    # Start the deployment in background
    background_tasks.add_task(_start_deployment, deployment_id)

    # Schedule auto-expiry if TTL is set
    if ttl_seconds and ttl_seconds > 0:
        background_tasks.add_task(_monitor_expiry, deployment_id, ttl_seconds)

    return DeploymentResponse(**deployment)


@router.get("/available-models")
async def get_available_models() -> list[dict]:
    """Get list of models available for deployment."""
    # Import here to avoid circular imports
    from flowyml.ui.backend.dependencies import get_store

    store = get_store()
    try:
        # Get all artifacts (assets)
        artifacts = store.list_assets()

        # Model-related type keywords
        model_keywords = (
            "model",
            "keras",
            "sklearn",
            "pytorch",
            "tensorflow",
            "xgboost",
            "lightgbm",
            "catboost",
            "onnx",
            "joblib",
            "pickle",
            "h5",
            "saved_model",
            "nn",
            "classifier",
            "regressor",
        )

        # First pass: look for explicitly model-typed artifacts
        models = []
        for a in artifacts:
            # Asset structure uses 'type' not 'asset_type'
            asset_type = (a.get("type") or "").lower()
            name = (a.get("name") or "").lower()
            path = a.get("path")

            # Check if this looks like a model
            is_model = any(kw in asset_type for kw in model_keywords) or any(kw in name for kw in model_keywords)

            # Skip if no file path (inline values can't be deployed as model servers)
            has_file = bool(path)
            # Filesystem probes are blocking, so they run off the event loop.
            file_exists = await anyio.to_thread.run_sync(_artifact_file_exists, path)

            if is_model:
                # Generate artifact_id if not present
                artifact_id = a.get("artifact_id") or f"{a.get('run_id')}_{a.get('step')}_{a.get('name')}"
                models.append(
                    {
                        "artifact_id": artifact_id,
                        "name": a.get("name"),
                        "version": a.get("version"),
                        "type": a.get("type") or "model",
                        "created_at": a.get("created_at"),
                        "run_id": a.get("run_id"),
                        "project": a.get("project"),
                        "has_file": has_file,
                        "file_exists": file_exists,
                        "path": path,
                    },
                )

        # If no models found, return all artifacts with paths as potential models
        if not models and artifacts:
            fallback_exists = [await anyio.to_thread.run_sync(_artifact_file_exists, a.get("path")) for a in artifacts]
            models = [
                {
                    "artifact_id": a.get("artifact_id") or f"{a.get('run_id')}_{a.get('step')}_{a.get('name')}",
                    "name": a.get("name"),
                    "version": a.get("version"),
                    "type": a.get("type") or "unknown",
                    "created_at": a.get("created_at"),
                    "run_id": a.get("run_id"),
                    "project": a.get("project"),
                    "has_file": bool(a.get("path")),
                    "file_exists": fallback_exists[index],
                    "path": a.get("path"),
                }
                for index, a in enumerate(artifacts)
            ]

        return models
    except Exception:
        # Return empty list on error
        return []


@router.get("/{deployment_id}")
async def get_deployment(deployment_id: str) -> DeploymentResponse:
    """Get deployment details."""
    if deployment_id not in _deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return DeploymentResponse(**_deployments[deployment_id])


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """Stop and delete a deployment."""
    if deployment_id not in _deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment = _deployments[deployment_id]
    deployment["status"] = "stopping"

    # Stop in background
    background_tasks.add_task(_stop_deployment, deployment_id)

    return {"status": "stopping", "id": deployment_id}


@router.post("/{deployment_id}/start")
async def start_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """Start a stopped deployment."""
    if deployment_id not in _deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment = _deployments[deployment_id]
    if deployment["status"] == "running":
        raise HTTPException(status_code=400, detail="Deployment already running")

    deployment["status"] = "starting"
    background_tasks.add_task(_start_deployment, deployment_id)

    return {"status": "starting", "id": deployment_id}


@router.post("/{deployment_id}/stop")
async def stop_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    """Stop a running deployment."""
    if deployment_id not in _deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment = _deployments[deployment_id]
    if deployment["status"] != "running":
        raise HTTPException(status_code=400, detail="Deployment not running")

    deployment["status"] = "stopping"
    background_tasks.add_task(_stop_deployment, deployment_id)

    return {"status": "stopping", "id": deployment_id}


@router.get("/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: str,
    lines: int = Query(100, ge=1, le=MAX_LOG_LINES),
) -> dict:
    """Get deployment logs."""
    if deployment_id not in _deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment = _deployments[deployment_id]

    # Try to get real logs from model server
    try:
        from flowyml.serving.model_server import get_server_logs

        logs = get_server_logs(deployment_id, lines)
        if logs:
            return {
                "deployment_id": deployment_id,
                "logs": logs,
            }
    except Exception:
        pass

    # Fallback to basic status logs
    return {
        "deployment_id": deployment_id,
        "logs": [
            {
                "timestamp": deployment.get("created_at", datetime.now().isoformat()),
                "level": "INFO",
                "message": f"Deployment '{deployment['name']}' created",
            },
            {
                "timestamp": deployment.get("started_at") or datetime.now().isoformat(),
                "level": "INFO",
                "message": f"Model {deployment['model_artifact_id']} loaded",
            },
            {
                "timestamp": deployment.get("started_at") or datetime.now().isoformat(),
                "level": "INFO",
                "message": f"Server configured on port {deployment['port']}",
            },
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": f"Current status: {deployment['status']}",
            },
        ],
    }


@router.post("/{deployment_id}/test")
async def test_deployment(
    deployment_id: str,
    request: PredictRequest,
) -> PredictResponse:
    """Test a deployed model with sample input."""
    if deployment_id not in _deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment = _deployments[deployment_id]
    if deployment["status"] != "running":
        raise HTTPException(status_code=400, detail="Deployment not running")

    import time

    start = time.time()

    try:
        # Use real model server prediction
        from flowyml.serving.model_server import predict, get_server

        server = get_server(deployment_id)
        if server is None:
            raise HTTPException(status_code=500, detail="Model server not available")

        # Run prediction
        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: predict(deployment_id, request.data),
        )

        latency = (time.time() - start) * 1000

        return PredictResponse(
            prediction=result,
            latency_ms=latency,
            model_version=deployment["model_version"] or "latest",
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# ==================== Background Tasks ====================

_server_processes: dict[str, any] = {}


async def _start_deployment(deployment_id: str):
    """Start the model server for a deployment."""
    import asyncio

    if deployment_id not in _deployments:
        return

    deployment = _deployments[deployment_id]

    try:
        deployment["status"] = "starting"

        # Import the real model server
        from flowyml.serving.model_server import (
            start_model_server,
            ServerConfig,
        )

        # Create server config from deployment config
        config = ServerConfig(
            port=deployment["port"],
            api_token=deployment["api_token"],
            rate_limit=deployment["config"].get("rate_limit", 100),
            timeout_seconds=deployment["config"].get("timeout_seconds", 30),
            max_batch_size=deployment["config"].get("max_batch_size", 1),
            enable_cors=deployment["config"].get("enable_cors", True),
        )

        # Start the model server (this loads the model)
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        server = await loop.run_in_executor(
            None,
            lambda: start_model_server(
                deployment_id=deployment_id,
                model_artifact_id=deployment["model_artifact_id"],
                config=config,
            ),
        )

        _server_processes[deployment_id] = server

        deployment["status"] = "running"
        deployment["started_at"] = datetime.now().isoformat()
        deployment["error_message"] = None

    except Exception as e:
        deployment["status"] = "error"
        deployment["error_message"] = str(e)


async def _stop_deployment(deployment_id: str):
    """Stop the model server for a deployment."""
    import asyncio

    if deployment_id not in _deployments:
        return

    deployment = _deployments[deployment_id]

    try:
        # Import the real model server
        from flowyml.serving.model_server import stop_model_server

        # Stop the server (this cleans up loaded models)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: stop_model_server(deployment_id),
        )

        # Clean up local reference
        if deployment_id in _server_processes:
            del _server_processes[deployment_id]

        deployment["status"] = "stopped"
        deployment["stopped_at"] = datetime.now().isoformat()

        # Remove from deployments on delete
        if deployment.get("_pending_delete"):
            del _deployments[deployment_id]

    except Exception as e:
        deployment["status"] = "error"
        deployment["error_message"] = str(e)


async def _monitor_expiry(deployment_id: str, ttl_seconds: int):
    """Monitor deployment and auto-stop after TTL expires."""
    import asyncio

    # Wait for TTL duration
    await asyncio.sleep(ttl_seconds)

    # Check if deployment still exists and is running
    if deployment_id not in _deployments:
        return

    deployment = _deployments[deployment_id]

    # Only stop if still running
    if deployment["status"] == "running":
        deployment["status"] = "stopping"

        # Add expiry reason to logs
        try:
            from flowyml.serving.model_server import get_server

            server = get_server(deployment_id)
            if server:
                server.log_buffer.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO",
                        "message": f"Auto-stopping: TTL of {ttl_seconds}s expired",
                    },
                )
        except Exception:
            pass

        # Stop the deployment
        await _stop_deployment(deployment_id)


# ==================== Dependency Installation ====================


class InstallDependenciesRequest(BaseModel):
    """Request to install ML framework dependencies."""

    frameworks: list[str] = Field(
        ...,
        description="List of frameworks to install (keras, tensorflow, pytorch, sklearn, etc.)",
    )


@router.get("/dependencies/available")
async def list_available_dependencies() -> dict:
    """List available ML framework dependencies that can be installed."""
    return {
        "available": ML_DEPENDENCIES,
        "description": "Pass framework keys to the install endpoint to install dependencies",
    }


@router.post("/dependencies/install")
async def install_dependencies(
    request: InstallDependenciesRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """Install ML framework dependencies on the server.

    This lightweight approach allows deploying Keras/TensorFlow/PyTorch models
    without needing a heavy Triton Inference Server container.
    """

    # Collect all packages to install
    packages = []
    for framework in request.frameworks:
        framework_lower = framework.lower()
        if framework_lower in ML_DEPENDENCIES:
            packages.extend(ML_DEPENDENCIES[framework_lower])
        else:
            # A direct package name is still allowed, but it must actually look
            # like one: pip reads an argument such as "--index-url=http://..."
            # as an option, which would let a caller redirect the installer at
            # an arbitrary package index.
            try:
                packages.append(validate_requirement(framework))
            except InvalidPackageNameError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not packages:
        raise HTTPException(status_code=400, detail="No valid frameworks specified")

    # Deduplicate
    packages = list(set(packages))

    # Queue the installation in background
    background_tasks.add_task(_install_packages_sync, packages)

    return {
        "status": "installing",
        "packages": packages,
        "message": f"Installing {len(packages)} package(s) in background",
    }


def _install_packages_sync(packages: list[str]):
    """Background task to install packages via pip."""
    import subprocess
    import sys
    import logging

    logger = logging.getLogger(__name__)

    for package in packages:
        try:
            # Validated again at the point of use: this function also runs from
            # a background task, decoupled from the request that queued it.
            target = validate_requirement(package)
        except InvalidPackageNameError as exc:
            logger.error(f"Refusing to install {package!r}: {exc}")
            continue

        try:
            logger.info(f"Installing {target}...")
            result = subprocess.run(
                # `sys.executable -m pip` rather than a bare `pip`, which
                # resolves from PATH and can install into a different
                # interpreter than the one serving requests - reporting success
                # while the import still fails.
                [sys.executable, "-m", "pip", "install", target],
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout per package
                check=False,
            )
            if result.returncode == 0:
                logger.info(f"Successfully installed {target}")
            else:
                logger.warning(f"Failed to install {target}: {result.stderr}")
        except Exception as e:
            logger.error(f"Error installing {target}: {e}")


@router.get("/dependencies/status")
async def check_installed_dependencies() -> dict:
    """Check which ML frameworks are currently installed."""
    import importlib.util

    installed = {}
    checks = {
        "keras": "keras",
        "tensorflow": "tensorflow",
        "pytorch": "torch",
        "sklearn": "sklearn",
        "xgboost": "xgboost",
        "lightgbm": "lightgbm",
        "onnx": "onnx",
        "onnxruntime": "onnxruntime",
        "numpy": "numpy",
        "pandas": "pandas",
    }

    for name, module in checks.items():
        try:
            spec = importlib.util.find_spec(module)
            installed[name] = spec is not None
        except (ImportError, ModuleNotFoundError):
            installed[name] = False

    return {
        "installed": installed,
        "ready_frameworks": [k for k, v in installed.items() if v],
    }

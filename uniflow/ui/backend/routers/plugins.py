"""API router for plugin management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
import sys
import subprocess

from uniflow.stacks.plugins import get_component_registry
from uniflow.stacks.migration import StackMigrator

router = APIRouter(prefix="/plugins", tags=["plugins"])


class PluginInfo(BaseModel):
    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    downloads: str
    stars: str
    tags: list[str]
    installed: bool


class InstallRequest(BaseModel):
    plugin_id: str


class ImportStackRequest(BaseModel):
    stack_name: str


@router.get("/available", response_model=list[PluginInfo])
async def get_available_plugins():
    """Get list of available plugins."""
    import importlib.metadata

    # Helper to check if package is installed
    def is_installed(package_name: str) -> bool:
        try:
            importlib.metadata.distribution(package_name)
            return True
        except importlib.metadata.PackageNotFoundError:
            return False

    # Mock data for now - in production this would query a plugin registry
    plugins = [
        PluginInfo(
            plugin_id="zenml-kubernetes",
            name="zenml-kubernetes",
            version="0.45.0",
            author="ZenML",
            description="Kubernetes orchestrator integration from ZenML ecosystem.",
            downloads="12k",
            stars="450",
            tags=["orchestrator", "kubernetes", "zenml"],
            installed=is_installed("zenml-kubernetes"),
        ),
        PluginInfo(
            plugin_id="zenml-mlflow",
            name="zenml-mlflow",
            version="0.45.0",
            author="ZenML",
            description="MLflow integration for experiment tracking and model deployment.",
            downloads="8.5k",
            stars="320",
            tags=["tracking", "mlflow", "zenml"],
            installed=is_installed("zenml-mlflow"),
        ),
        PluginInfo(
            plugin_id="airflow-providers-google",
            name="airflow-providers-google",
            version="10.1.0",
            author="Apache Airflow",
            description="Google Cloud Platform providers for Airflow.",
            downloads="50k",
            stars="1.2k",
            tags=["orchestrator", "gcp", "airflow"],
            installed=is_installed("airflow-providers-google"),
        ),
        PluginInfo(
            plugin_id="aws-s3",
            name="aws-s3",
            version="1.0.0",
            author="AWS",
            description="S3 artifact store integration.",
            downloads="15k",
            stars="200",
            tags=["artifact-store", "aws"],
            installed=is_installed("aws-s3"),
        ),
    ]

    return plugins


@router.get("/installed", response_model=list[dict[str, Any]])
async def get_installed_plugins():
    """Get list of installed plugins."""
    import importlib.metadata

    # Get all installed packages that could be plugins
    installed = []

    # List of known plugin packages (you can expand this)
    potential_plugins = [
        "zenml",
        "zenml-kubernetes",
        "zenml-mlflow",
        "zenml-s3",
        "airflow",
        "airflow-providers-google",
        "airflow-providers-aws",
        "aws-s3",
        "boto3",
        "kubernetes",
    ]

    for package_name in potential_plugins:
        try:
            dist = importlib.metadata.distribution(package_name)
            installed.append(
                {
                    "id": package_name,
                    "name": package_name,
                    "version": dist.version,
                    "description": dist.metadata.get("Summary", ""),
                    "status": "active",
                },
            )
        except importlib.metadata.PackageNotFoundError:
            pass

    return installed


@router.post("/install")
async def install_plugin(request: InstallRequest):
    """Install a plugin."""
    registry = get_component_registry()

    try:
        success = registry.install_plugin(request.plugin_id)
        if success:
            return {"success": True, "message": f"Plugin {request.plugin_id} installed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Installation failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uninstall/{plugin_id}")
async def uninstall_plugin(plugin_id: str):
    """Uninstall a plugin."""
    import asyncio

    try:
        # Run subprocess in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            subprocess.check_call,
            [sys.executable, "-m", "pip", "uninstall", "-y", plugin_id],
        )
        return {"success": True, "message": f"Plugin {plugin_id} uninstalled successfully"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-stack")
async def import_zenml_stack(request: ImportStackRequest):
    """Import a ZenML stack."""
    migrator = StackMigrator()

    try:
        migration_data = migrator.migrate_zenml_stack(request.stack_name)
        return {
            "success": True,
            "message": "Stack imported successfully",
            "components": [
                {"type": comp_type, "name": comp.name if hasattr(comp, "name") else str(comp)}
                for comp_type, comp in migration_data["stack"]["components"].items()
            ],
        }
    except ImportError:
        raise HTTPException(status_code=400, detail="ZenML is not installed")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

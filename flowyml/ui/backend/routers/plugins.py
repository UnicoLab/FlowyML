"""API router for plugin management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
import sys
import subprocess

from flowyml.stacks.plugins import get_component_registry
from flowyml.stacks.migration import StackMigrator

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
    """Get list of available FlowyML plugins."""
    import importlib.metadata

    # Helper to check if package is installed
    def is_installed(package_name: str) -> bool:
        try:
            importlib.metadata.distribution(package_name)
            return True
        except importlib.metadata.PackageNotFoundError:
            return False

    # FlowyML Native Plugins
    plugins = [
        PluginInfo(
            plugin_id="flowyml-gcp",
            name="FlowyML GCP",
            version="1.8.0",
            author="FlowyML",
            description="Google Cloud Platform integration: Vertex AI orchestrator, GCS artifact store, and Cloud Run deployer.",
            downloads="5.2k",
            stars="180",
            tags=["orchestrator", "artifact-store", "gcp", "vertex-ai"],
            installed=is_installed("google-cloud-aiplatform"),
        ),
        PluginInfo(
            plugin_id="flowyml-aws",
            name="FlowyML AWS",
            version="1.8.0",
            author="FlowyML",
            description="AWS integration: SageMaker orchestrator, S3 artifact store, and ECR container registry.",
            downloads="4.8k",
            stars="165",
            tags=["orchestrator", "artifact-store", "aws", "sagemaker"],
            installed=is_installed("boto3"),
        ),
        PluginInfo(
            plugin_id="flowyml-kubernetes",
            name="FlowyML Kubernetes",
            version="1.8.0",
            author="FlowyML",
            description="Kubernetes orchestrator for running pipelines on K8s clusters with auto-scaling.",
            downloads="3.5k",
            stars="145",
            tags=["orchestrator", "kubernetes", "container"],
            installed=is_installed("kubernetes"),
        ),
        PluginInfo(
            plugin_id="flowyml-mlflow",
            name="FlowyML MLflow",
            version="1.8.0",
            author="FlowyML",
            description="MLflow integration for experiment tracking, model registry, and deployment.",
            downloads="6.1k",
            stars="220",
            tags=["tracking", "model-registry", "mlflow"],
            installed=is_installed("mlflow"),
        ),
        PluginInfo(
            plugin_id="flowyml-wandb",
            name="FlowyML Weights & Biases",
            version="1.8.0",
            author="FlowyML",
            description="W&B integration for experiment tracking, artifact versioning, and collaboration.",
            downloads="4.2k",
            stars="195",
            tags=["tracking", "wandb", "experiment"],
            installed=is_installed("wandb"),
        ),
        PluginInfo(
            plugin_id="flowyml-pytorch",
            name="FlowyML PyTorch",
            version="1.8.0",
            author="FlowyML",
            description="PyTorch integration with automatic model serialization and distributed training support.",
            downloads="8.5k",
            stars="310",
            tags=["framework", "pytorch", "deep-learning"],
            installed=is_installed("torch"),
        ),
        PluginInfo(
            plugin_id="flowyml-tensorflow",
            name="FlowyML TensorFlow",
            version="1.8.0",
            author="FlowyML",
            description="TensorFlow/Keras integration with automatic callbacks and model tracking.",
            downloads="7.8k",
            stars="290",
            tags=["framework", "tensorflow", "keras"],
            installed=is_installed("tensorflow"),
        ),
        PluginInfo(
            plugin_id="flowyml-sklearn",
            name="FlowyML Scikit-Learn",
            version="1.8.0",
            author="FlowyML",
            description="Scikit-learn integration with automatic model serialization and metrics extraction.",
            downloads="9.2k",
            stars="340",
            tags=["framework", "sklearn", "ml"],
            installed=is_installed("scikit-learn"),
        ),
    ]

    return plugins


@router.get("/installed", response_model=list[dict[str, Any]])
async def get_installed_plugins():
    """Get list of installed FlowyML plugins and integrations."""
    import importlib.metadata

    # Get all installed packages that could be plugins
    installed = []

    # FlowyML-related plugin packages
    potential_plugins = [
        # Cloud providers
        ("google-cloud-aiplatform", "FlowyML GCP"),
        ("google-cloud-storage", "GCS Storage"),
        ("boto3", "FlowyML AWS"),
        ("sagemaker", "AWS SageMaker"),
        # Orchestrators
        ("kubernetes", "FlowyML Kubernetes"),
        ("kfp", "Kubeflow Pipelines"),
        # Tracking & Registry
        ("mlflow", "FlowyML MLflow"),
        ("wandb", "FlowyML W&B"),
        # ML Frameworks
        ("torch", "FlowyML PyTorch"),
        ("tensorflow", "FlowyML TensorFlow"),
        ("keras", "FlowyML Keras"),
        ("scikit-learn", "FlowyML Scikit-Learn"),
        # Core
        ("flowyml", "FlowyML Core"),
    ]

    for package_name, display_name in potential_plugins:
        try:
            dist = importlib.metadata.distribution(package_name)
            installed.append(
                {
                    "id": package_name,
                    "name": display_name,
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
            return {
                "success": True,
                "message": f"Plugin {request.plugin_id} installed successfully",
            }
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

"""API router for plugin management and stack templates."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
import sys
import subprocess

from flowyml.utils.packages import (
    InvalidPackageNameError,
    validate_requirement,
    validate_uninstall_target,
)

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
    category: str = "integration"


class StackTemplate(BaseModel):
    template_id: str
    name: str
    description: str
    cloud: str  # "local", "gcp", "aws", "azure", "kubernetes"
    components: list[dict[str, str]]
    estimated_cost: str
    difficulty: str  # "beginner", "intermediate", "advanced"
    tags: list[str]


class InstallRequest(BaseModel):
    plugin_id: str


class ImportStackRequest(BaseModel):
    stack_name: str


class ProvisionStackRequest(BaseModel):
    template_id: str
    stack_name: str
    config: dict[str, Any] = {}


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

    # FlowyML Native Plugins - Comprehensive Catalog
    plugins = [
        # ── Cloud Providers ──────────────────────────────────────────
        PluginInfo(
            plugin_id="flowyml-gcp",
            name="FlowyML GCP",
            version="1.8.0",
            author="FlowyML",
            description="Google Cloud Platform integration: Vertex AI orchestrator, GCS artifact store, Cloud Run deployer, and BigQuery analytics.",
            downloads="5.2k",
            stars="180",
            tags=["orchestrator", "artifact-store", "gcp", "vertex-ai"],
            installed=is_installed("google-cloud-aiplatform"),
            category="cloud",
        ),
        PluginInfo(
            plugin_id="flowyml-aws",
            name="FlowyML AWS",
            version="1.8.0",
            author="FlowyML",
            description="AWS integration: SageMaker orchestrator, S3 artifact store, ECR container registry, and Bedrock GenAI support.",
            downloads="4.8k",
            stars="165",
            tags=["orchestrator", "artifact-store", "aws", "sagemaker"],
            installed=is_installed("boto3"),
            category="cloud",
        ),
        PluginInfo(
            plugin_id="flowyml-azure",
            name="FlowyML Azure",
            version="1.8.0",
            author="FlowyML",
            description="Azure integration: Azure ML orchestrator, Blob Storage artifacts, ACR container registry, and Azure OpenAI.",
            downloads="3.1k",
            stars="120",
            tags=["orchestrator", "artifact-store", "azure", "azureml"],
            installed=is_installed("azure-ai-ml"),
            category="cloud",
        ),
        # ── Orchestrators ────────────────────────────────────────────
        PluginInfo(
            plugin_id="flowyml-kubernetes",
            name="FlowyML Kubernetes",
            version="1.8.0",
            author="FlowyML",
            description="Kubernetes orchestrator for running pipelines on K8s clusters with auto-scaling and resource management.",
            downloads="3.5k",
            stars="145",
            tags=["orchestrator", "kubernetes", "container"],
            installed=is_installed("kubernetes"),
            category="orchestrator",
        ),
        PluginInfo(
            plugin_id="flowyml-airflow",
            name="FlowyML Airflow",
            version="1.8.0",
            author="FlowyML",
            description="Apache Airflow integration for DAG-based pipeline orchestration with existing Airflow infrastructure.",
            downloads="4.5k",
            stars="175",
            tags=["orchestrator", "airflow", "dag"],
            installed=is_installed("apache-airflow"),
            category="orchestrator",
        ),
        PluginInfo(
            plugin_id="flowyml-kubeflow",
            name="FlowyML Kubeflow",
            version="1.8.0",
            author="FlowyML",
            description="Kubeflow Pipelines integration for cloud-native ML workflow orchestration on Kubernetes.",
            downloads="2.8k",
            stars="110",
            tags=["orchestrator", "kubeflow", "kubernetes"],
            installed=is_installed("kfp"),
            category="orchestrator",
        ),
        # ── Experiment Tracking ──────────────────────────────────────
        PluginInfo(
            plugin_id="flowyml-mlflow",
            name="FlowyML MLflow",
            version="1.8.0",
            author="FlowyML",
            description="MLflow integration for experiment tracking, model registry, and deployment with full metric sync.",
            downloads="6.1k",
            stars="220",
            tags=["tracking", "model-registry", "mlflow"],
            installed=is_installed("mlflow"),
            category="tracking",
        ),
        PluginInfo(
            plugin_id="flowyml-wandb",
            name="FlowyML Weights & Biases",
            version="1.8.0",
            author="FlowyML",
            description="W&B integration for experiment tracking, artifact versioning, hyperparameter sweeps, and collaboration.",
            downloads="4.2k",
            stars="195",
            tags=["tracking", "wandb", "experiment"],
            installed=is_installed("wandb"),
            category="tracking",
        ),
        PluginInfo(
            plugin_id="flowyml-neptune",
            name="FlowyML Neptune",
            version="1.8.0",
            author="FlowyML",
            description="Neptune.ai integration for experiment tracking, model registry, and team collaboration dashboards.",
            downloads="1.9k",
            stars="85",
            tags=["tracking", "neptune", "experiment"],
            installed=is_installed("neptune"),
            category="tracking",
        ),
        PluginInfo(
            plugin_id="flowyml-comet",
            name="FlowyML Comet ML",
            version="1.8.0",
            author="FlowyML",
            description="Comet ML integration for experiment management, model production monitoring, and data visualization.",
            downloads="1.5k",
            stars="72",
            tags=["tracking", "comet", "monitoring"],
            installed=is_installed("comet-ml"),
            category="tracking",
        ),
        # ── ML Frameworks ────────────────────────────────────────────
        PluginInfo(
            plugin_id="flowyml-pytorch",
            name="FlowyML PyTorch",
            version="1.8.0",
            author="FlowyML",
            description="PyTorch integration with automatic model serialization, distributed training, and Lightning support.",
            downloads="8.5k",
            stars="310",
            tags=["framework", "pytorch", "deep-learning"],
            installed=is_installed("torch"),
            category="framework",
        ),
        PluginInfo(
            plugin_id="flowyml-tensorflow",
            name="FlowyML TensorFlow",
            version="1.8.0",
            author="FlowyML",
            description="TensorFlow/Keras integration with automatic callbacks, SavedModel tracking, and TFX pipeline support.",
            downloads="7.8k",
            stars="290",
            tags=["framework", "tensorflow", "keras"],
            installed=is_installed("tensorflow"),
            category="framework",
        ),
        PluginInfo(
            plugin_id="flowyml-sklearn",
            name="FlowyML Scikit-Learn",
            version="1.8.0",
            author="FlowyML",
            description="Scikit-learn integration with automatic model serialization, metrics extraction, and pipeline tracking.",
            downloads="9.2k",
            stars="340",
            tags=["framework", "sklearn", "ml"],
            installed=is_installed("scikit-learn"),
            category="framework",
        ),
        PluginInfo(
            plugin_id="flowyml-xgboost",
            name="FlowyML XGBoost",
            version="1.8.0",
            author="FlowyML",
            description="XGBoost integration with automatic parameter tracking, feature importance logging, and model serialization.",
            downloads="5.4k",
            stars="190",
            tags=["framework", "xgboost", "gradient-boosting"],
            installed=is_installed("xgboost"),
            category="framework",
        ),
        # ── GenAI & LLM ─────────────────────────────────────────────
        PluginInfo(
            plugin_id="flowyml-huggingface",
            name="FlowyML Hugging Face",
            version="1.8.0",
            author="FlowyML",
            description="Hugging Face integration: Transformers model tracking, Hub push/pull, dataset versioning, and Spaces deployment.",
            downloads="7.2k",
            stars="305",
            tags=["genai", "huggingface", "transformers", "llm"],
            installed=is_installed("transformers"),
            category="genai",
        ),
        PluginInfo(
            plugin_id="flowyml-langchain",
            name="FlowyML LangChain",
            version="1.8.0",
            author="FlowyML",
            description="LangChain integration for agent observability, chain tracing, token cost tracking, and prompt versioning.",
            downloads="6.8k",
            stars="280",
            tags=["genai", "langchain", "agents", "llm"],
            installed=is_installed("langchain"),
            category="genai",
        ),
        PluginInfo(
            plugin_id="flowyml-llamaindex",
            name="FlowyML LlamaIndex",
            version="1.8.0",
            author="FlowyML",
            description="LlamaIndex integration for RAG pipeline observability, index tracking, and retrieval quality metrics.",
            downloads="3.9k",
            stars="155",
            tags=["genai", "llamaindex", "rag", "llm"],
            installed=is_installed("llama-index"),
            category="genai",
        ),
        PluginInfo(
            plugin_id="flowyml-openai",
            name="FlowyML OpenAI",
            version="1.8.0",
            author="FlowyML",
            description="OpenAI API integration with automatic token tracking, cost analytics, prompt logging, and GPT function calls.",
            downloads="8.1k",
            stars="320",
            tags=["genai", "openai", "gpt", "llm"],
            installed=is_installed("openai"),
            category="genai",
        ),
        # ── Model Serving ────────────────────────────────────────────
        PluginInfo(
            plugin_id="flowyml-bentoml",
            name="FlowyML BentoML",
            version="1.8.0",
            author="FlowyML",
            description="BentoML integration for model packaging, API serving, and deployment with built-in performance monitoring.",
            downloads="2.6k",
            stars="105",
            tags=["serving", "bentoml", "deployment"],
            installed=is_installed("bentoml"),
            category="serving",
        ),
        PluginInfo(
            plugin_id="flowyml-seldon",
            name="FlowyML Seldon Core",
            version="1.8.0",
            author="FlowyML",
            description="Seldon Core integration for Kubernetes-native model serving with A/B testing and canary deployments.",
            downloads="1.8k",
            stars="88",
            tags=["serving", "seldon", "kubernetes"],
            installed=is_installed("seldon-core"),
            category="serving",
        ),
        # ── Data & Feature Stores ────────────────────────────────────
        PluginInfo(
            plugin_id="flowyml-feast",
            name="FlowyML Feast",
            version="1.8.0",
            author="FlowyML",
            description="Feast feature store integration for feature serving, point-in-time joins, and feature drift monitoring.",
            downloads="2.2k",
            stars="95",
            tags=["feature-store", "feast", "data"],
            installed=is_installed("feast"),
            category="data",
        ),
        PluginInfo(
            plugin_id="flowyml-great-expectations",
            name="FlowyML Great Expectations",
            version="1.8.0",
            author="FlowyML",
            description="Great Expectations integration for automated data quality validation, profiling, and documentation.",
            downloads="3.3k",
            stars="130",
            tags=["data-quality", "validation", "testing"],
            installed=is_installed("great_expectations"),
            category="data",
        ),
        PluginInfo(
            plugin_id="flowyml-dvc",
            name="FlowyML DVC",
            version="1.8.0",
            author="FlowyML",
            description="DVC (Data Version Control) integration for data/model versioning, remote storage, and pipeline reproducibility.",
            downloads="3.7k",
            stars="140",
            tags=["versioning", "dvc", "data"],
            installed=is_installed("dvc"),
            category="data",
        ),
        # ── Optimization ─────────────────────────────────────────────
        PluginInfo(
            plugin_id="flowyml-optuna",
            name="FlowyML Optuna",
            version="1.8.0",
            author="FlowyML",
            description="Optuna integration for hyperparameter optimization with automatic trial tracking and visualization.",
            downloads="4.0k",
            stars="160",
            tags=["optimization", "optuna", "hyperparameter"],
            installed=is_installed("optuna"),
            category="optimization",
        ),
        PluginInfo(
            plugin_id="flowyml-ray",
            name="FlowyML Ray",
            version="1.8.0",
            author="FlowyML",
            description="Ray integration for distributed computing, Ray Tune hyperparameter search, and Ray Serve model deployment.",
            downloads="3.2k",
            stars="135",
            tags=["distributed", "ray", "scaling"],
            installed=is_installed("ray"),
            category="optimization",
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
        ("azure-ai-ml", "FlowyML Azure"),
        # Orchestrators
        ("kubernetes", "FlowyML Kubernetes"),
        ("kfp", "Kubeflow Pipelines"),
        ("apache-airflow", "Apache Airflow"),
        # Tracking & Registry
        ("mlflow", "FlowyML MLflow"),
        ("wandb", "FlowyML W&B"),
        ("neptune", "FlowyML Neptune"),
        ("comet-ml", "FlowyML Comet"),
        # ML Frameworks
        ("torch", "FlowyML PyTorch"),
        ("tensorflow", "FlowyML TensorFlow"),
        ("keras", "FlowyML Keras"),
        ("scikit-learn", "FlowyML Scikit-Learn"),
        ("xgboost", "FlowyML XGBoost"),
        # GenAI & LLM
        ("transformers", "Hugging Face Transformers"),
        ("langchain", "LangChain"),
        ("llama-index", "LlamaIndex"),
        ("openai", "OpenAI"),
        # Model Serving
        ("bentoml", "BentoML"),
        ("seldon-core", "Seldon Core"),
        # Data & Feature Stores
        ("feast", "Feast Feature Store"),
        ("great_expectations", "Great Expectations"),
        ("dvc", "DVC"),
        # Optimization
        ("optuna", "Optuna"),
        ("ray", "Ray"),
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


# =============================================================================
# Stack Templates — Preconfigured production-ready stacks
# =============================================================================


@router.get("/stacks/templates", response_model=list[StackTemplate])
async def get_stack_templates():
    """Get preconfigured stack templates for quick deployment."""
    templates = [
        StackTemplate(
            template_id="local-dev",
            name="Local Development",
            description="Lightweight local stack for development and testing. Uses SQLite metadata, local filesystem artifacts, and the built-in orchestrator.",
            cloud="local",
            components=[
                {"type": "Orchestrator", "name": "Local Process Orchestrator"},
                {"type": "Artifact Store", "name": "Local Filesystem Store"},
                {"type": "Metadata", "name": "SQLite"},
            ],
            estimated_cost="Free",
            difficulty="beginner",
            tags=["local", "development", "quick-start"],
        ),
        StackTemplate(
            template_id="docker-compose",
            name="Docker Compose Stack",
            description="Self-hosted stack using Docker Compose with PostgreSQL, Prometheus, and Grafana. Ideal for small teams or on-premise deployment.",
            cloud="local",
            components=[
                {"type": "Orchestrator", "name": "Local Orchestrator"},
                {"type": "Artifact Store", "name": "Local Volume Store"},
                {"type": "Metadata", "name": "PostgreSQL"},
                {"type": "Monitoring", "name": "Prometheus + Grafana"},
            ],
            estimated_cost="Free (self-hosted)",
            difficulty="beginner",
            tags=["docker", "self-hosted", "postgres"],
        ),
        StackTemplate(
            template_id="gcp-production",
            name="GCP Production",
            description="Production-grade Google Cloud stack with Cloud Run, Cloud SQL (PostgreSQL), Vertex AI, GCS artifact storage, and Secret Manager.",
            cloud="gcp",
            components=[
                {"type": "Compute", "name": "Cloud Run (scale-to-zero)"},
                {"type": "Database", "name": "Cloud SQL (PostgreSQL 15)"},
                {"type": "Orchestrator", "name": "Vertex AI Pipelines"},
                {"type": "Artifact Store", "name": "Google Cloud Storage"},
                {"type": "Container Registry", "name": "Artifact Registry"},
                {"type": "Secrets", "name": "Secret Manager"},
                {"type": "Monitoring", "name": "Cloud Monitoring + Alerting"},
            ],
            estimated_cost="~$7-10/mo (idle)",
            difficulty="intermediate",
            tags=["gcp", "production", "serverless", "vertex-ai"],
        ),
        StackTemplate(
            template_id="aws-production",
            name="AWS Production",
            description="Production-grade AWS stack with App Runner, RDS PostgreSQL, SageMaker, S3 artifact storage, and Secrets Manager.",
            cloud="aws",
            components=[
                {"type": "Compute", "name": "App Runner (auto-scaling)"},
                {"type": "Database", "name": "RDS PostgreSQL"},
                {"type": "Orchestrator", "name": "SageMaker Pipelines"},
                {"type": "Artifact Store", "name": "Amazon S3"},
                {"type": "Container Registry", "name": "ECR"},
                {"type": "Secrets", "name": "Secrets Manager"},
                {"type": "Monitoring", "name": "CloudWatch"},
            ],
            estimated_cost="~$50/mo",
            difficulty="intermediate",
            tags=["aws", "production", "sagemaker"],
        ),
        StackTemplate(
            template_id="azure-production",
            name="Azure Production",
            description="Production-grade Azure stack with Container Apps, PostgreSQL Flexible Server, Azure ML, Blob Storage, and Key Vault.",
            cloud="azure",
            components=[
                {"type": "Compute", "name": "Container Apps (scale-to-zero)"},
                {"type": "Database", "name": "PostgreSQL Flexible Server"},
                {"type": "Orchestrator", "name": "Azure ML Pipelines"},
                {"type": "Artifact Store", "name": "Azure Blob Storage"},
                {"type": "Container Registry", "name": "Azure Container Registry"},
                {"type": "Secrets", "name": "Key Vault"},
                {"type": "Monitoring", "name": "Log Analytics"},
            ],
            estimated_cost="~$15-20/mo (idle)",
            difficulty="intermediate",
            tags=["azure", "production", "azureml"],
        ),
        StackTemplate(
            template_id="kubernetes-advanced",
            name="Kubernetes MLOps",
            description="Advanced Kubernetes-native stack with Kubeflow Pipelines, MinIO artifact storage, Seldon model serving, and Prometheus monitoring.",
            cloud="kubernetes",
            components=[
                {"type": "Orchestrator", "name": "Kubeflow Pipelines"},
                {"type": "Artifact Store", "name": "MinIO (S3-compatible)"},
                {"type": "Model Serving", "name": "Seldon Core"},
                {"type": "Feature Store", "name": "Feast"},
                {"type": "Monitoring", "name": "Prometheus + Grafana"},
                {"type": "Container Registry", "name": "Harbor"},
            ],
            estimated_cost="Varies (cluster costs)",
            difficulty="advanced",
            tags=["kubernetes", "kubeflow", "seldon", "mlops"],
        ),
        StackTemplate(
            template_id="genai-starter",
            name="GenAI Observability",
            description="Optimized stack for LLM/GenAI application monitoring. Includes the @observe decorator, token cost tracking, trace visualization, and quality evaluation.",
            cloud="local",
            components=[
                {"type": "Observability", "name": "@observe Decorator"},
                {"type": "Tracing", "name": "GenAI Trace Collector"},
                {"type": "Cost Tracking", "name": "Token & Cost Analytics"},
                {"type": "Evaluation", "name": "Built-in Scorers"},
                {"type": "Dashboard", "name": "GenAI Traces UI"},
            ],
            estimated_cost="Free (built-in)",
            difficulty="beginner",
            tags=["genai", "llm", "observability", "traces"],
        ),
        StackTemplate(
            template_id="mlops-complete",
            name="Full MLOps Platform",
            description="Complete MLOps lifecycle stack: experiment tracking, model registry, CI/CD, feature store, data validation, hyperparameter optimization, and production monitoring.",
            cloud="gcp",
            components=[
                {"type": "Orchestrator", "name": "Vertex AI Pipelines"},
                {"type": "Tracking", "name": "FlowyML + MLflow"},
                {"type": "Feature Store", "name": "Feast on BigQuery"},
                {"type": "Data Validation", "name": "Great Expectations"},
                {"type": "Optimization", "name": "Optuna + Ray Tune"},
                {"type": "Model Serving", "name": "Cloud Run Endpoints"},
                {"type": "Monitoring", "name": "Full Observability Suite"},
            ],
            estimated_cost="~$50-100/mo",
            difficulty="advanced",
            tags=["mlops", "production", "enterprise", "complete"],
        ),
    ]

    return templates


@router.post("/stacks/provision")
async def provision_stack(request: ProvisionStackRequest):
    """Provision a stack from a template."""
    from flowyml.stacks import (
        LocalStack,
        GCPStack,
        AWSStack,
        AzureMLStack,
        get_registry,
    )

    template_map = {
        "local-dev": "local",
        "docker-compose": "local",
        "gcp-production": "gcp",
        "aws-production": "aws",
        "azure-production": "azure",
        "kubernetes-advanced": "kubernetes",
        "genai-starter": "local",
        "mlops-complete": "gcp",
    }

    cloud = template_map.get(request.template_id)
    if not cloud:
        raise HTTPException(status_code=404, detail=f"Unknown template: {request.template_id}")

    try:
        registry = get_registry()

        # Create appropriate stack based on template
        if cloud == "local":
            stack = LocalStack(name=request.stack_name)
        elif cloud == "gcp":
            stack = GCPStack(name=request.stack_name, **request.config)
        elif cloud == "aws":
            stack = AWSStack(name=request.stack_name, **request.config)
        elif cloud == "azure":
            stack = AzureMLStack(name=request.stack_name, **request.config)
        else:
            # Kubernetes and other advanced templates
            stack = LocalStack(name=request.stack_name)

        registry.register(request.stack_name, stack)
        registry.set_active(request.stack_name)

        return {
            "success": True,
            "message": f"Stack '{request.stack_name}' provisioned from template '{request.template_id}'",
            "stack_name": request.stack_name,
            "template_id": request.template_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install")
async def install_plugin(request: InstallRequest):
    """Install a plugin."""
    registry = get_component_registry()

    try:
        package = validate_requirement(request.plugin_id)
    except InvalidPackageNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        success = registry.install_plugin(package)
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

    # pip cannot distinguish a package named "--index-url=..." from the option
    # of the same spelling, and uninstalling flowyml itself would stop the
    # server mid-request.
    try:
        target = validate_uninstall_target(plugin_id)
    except InvalidPackageNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        # Run subprocess in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            subprocess.check_call,
            [sys.executable, "-m", "pip", "uninstall", "-y", target],
        )
        return {"success": True, "message": f"Plugin {target} uninstalled successfully"}
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

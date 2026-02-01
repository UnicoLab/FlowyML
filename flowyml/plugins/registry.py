"""FlowyML Plugin Registry - Plugin Catalog and Discovery.

This module defines the catalog of available plugins and provides
discovery mechanisms for finding and loading plugins.

Usage:
    from flowyml.plugins.registry import PLUGIN_CATALOG, get_plugin_info

    # Get info about a plugin
    info = get_plugin_info("mlflow")

    # List all available plugins
    plugins = list_plugins()
"""

from dataclasses import dataclass, field
from enum import Enum

from flowyml.plugins.base import PluginType


class PluginStatus(Enum):
    """Status of a plugin."""

    AVAILABLE = "available"  # Plugin is in catalog, packages not installed
    INSTALLED = "installed"  # Packages are installed
    LOADED = "loaded"  # Plugin class has been loaded
    DEPRECATED = "deprecated"  # Plugin is deprecated


@dataclass
class PluginInfo:
    """Information about a plugin in the catalog."""

    # Basic info
    name: str
    description: str
    plugin_type: PluginType

    # Package requirements
    packages: list[str] = field(default_factory=list)

    # Plugin class location
    wrapper_path: str = ""  # e.g., "flowyml.plugins.trackers.mlflow:MLflowTracker"

    # Metadata
    version: str = "1.0.0"
    author: str = "FlowyML"
    documentation_url: str = ""
    tags: list[str] = field(default_factory=list)

    # Status
    status: PluginStatus = PluginStatus.AVAILABLE

    # Optional extras
    optional_packages: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate and normalize fields."""
        if isinstance(self.plugin_type, str):
            self.plugin_type = PluginType(self.plugin_type)
        if isinstance(self.status, str):
            self.status = PluginStatus(self.status)


# ============================================================================
# OFFICIAL PLUGIN CATALOG
# ============================================================================

PLUGIN_CATALOG: dict[str, PluginInfo] = {
    # -------------------------------------------------------------------------
    # EXPERIMENT TRACKERS
    # -------------------------------------------------------------------------
    "mlflow": PluginInfo(
        name="mlflow",
        description="MLflow experiment tracking and model registry",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        packages=["mlflow>=2.0"],
        wrapper_path="flowyml.plugins.trackers.mlflow:MLflowTracker",
        documentation_url="https://mlflow.org/docs/latest/index.html",
        tags=["experiment-tracking", "model-registry", "popular"],
    ),
    "wandb": PluginInfo(
        name="wandb",
        description="Weights & Biases experiment tracking",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        packages=["wandb>=0.15"],
        wrapper_path="flowyml.plugins.trackers.wandb:WandbTracker",
        documentation_url="https://docs.wandb.ai/",
        tags=["experiment-tracking", "visualization", "popular"],
    ),
    "neptune": PluginInfo(
        name="neptune",
        description="Neptune.ai experiment tracking",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        packages=["neptune>=1.0"],
        wrapper_path="flowyml.plugins.trackers.neptune:NeptuneTracker",
        documentation_url="https://docs.neptune.ai/",
        tags=["experiment-tracking", "visualization"],
    ),
    "tensorboard": PluginInfo(
        name="tensorboard",
        description="TensorBoard visualization and logging",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        packages=["tensorboard>=2.10"],
        wrapper_path="flowyml.plugins.trackers.tensorboard:TensorBoardTracker",
        documentation_url="https://www.tensorflow.org/tensorboard",
        tags=["experiment-tracking", "visualization", "tensorflow"],
    ),
    # -------------------------------------------------------------------------
    # ARTIFACT STORES - Cloud
    # -------------------------------------------------------------------------
    "s3": PluginInfo(
        name="s3",
        description="AWS S3 artifact storage",
        plugin_type=PluginType.ARTIFACT_STORE,
        packages=["boto3>=1.28", "s3fs>=2023.0"],
        wrapper_path="flowyml.plugins.stores.s3:S3ArtifactStore",
        documentation_url="https://docs.aws.amazon.com/s3/",
        tags=["artifact-store", "aws", "cloud", "popular"],
    ),
    "gcs": PluginInfo(
        name="gcs",
        description="Google Cloud Storage artifact storage",
        plugin_type=PluginType.ARTIFACT_STORE,
        packages=["google-cloud-storage>=2.0", "gcsfs>=2023.0"],
        wrapper_path="flowyml.plugins.stores.gcs:GCSArtifactStore",
        documentation_url="https://cloud.google.com/storage/docs",
        tags=["artifact-store", "gcp", "cloud", "popular"],
    ),
    "azure_blob": PluginInfo(
        name="azure_blob",
        description="Azure Blob Storage artifact storage",
        plugin_type=PluginType.ARTIFACT_STORE,
        packages=["azure-storage-blob>=12.0", "adlfs>=2023.0"],
        wrapper_path="flowyml.plugins.stores.azure:AzureBlobArtifactStore",
        documentation_url="https://docs.microsoft.com/azure/storage/blobs/",
        tags=["artifact-store", "azure", "cloud"],
    ),
    # -------------------------------------------------------------------------
    # ORCHESTRATORS
    # -------------------------------------------------------------------------
    "kubernetes": PluginInfo(
        name="kubernetes",
        description="Kubernetes orchestration for pipeline execution",
        plugin_type=PluginType.ORCHESTRATOR,
        packages=["kubernetes>=25.0"],
        wrapper_path="flowyml.plugins.orchestrators.kubernetes:KubernetesOrchestrator",
        documentation_url="https://kubernetes.io/docs/",
        tags=["orchestrator", "kubernetes", "cloud", "popular"],
    ),
    "airflow": PluginInfo(
        name="airflow",
        description="Apache Airflow DAG-based orchestration",
        plugin_type=PluginType.ORCHESTRATOR,
        packages=["apache-airflow>=2.5"],
        wrapper_path="flowyml.plugins.orchestrators.airflow:AirflowOrchestrator",
        documentation_url="https://airflow.apache.org/docs/",
        tags=["orchestrator", "airflow", "dag"],
    ),
    "kubeflow": PluginInfo(
        name="kubeflow",
        description="Kubeflow Pipelines orchestration",
        plugin_type=PluginType.ORCHESTRATOR,
        packages=["kfp>=2.0"],
        wrapper_path="flowyml.plugins.orchestrators.kubeflow:KubeflowOrchestrator",
        documentation_url="https://www.kubeflow.org/docs/",
        tags=["orchestrator", "kubeflow", "kubernetes"],
    ),
    "ray": PluginInfo(
        name="ray",
        description="Ray distributed computing orchestration",
        plugin_type=PluginType.ORCHESTRATOR,
        packages=["ray>=2.0"],
        wrapper_path="flowyml.plugins.orchestrators.ray:RayOrchestrator",
        documentation_url="https://docs.ray.io/",
        tags=["orchestrator", "ray", "distributed"],
    ),
    "vertex_ai": PluginInfo(
        name="vertex_ai",
        description="Google Cloud Vertex AI Pipelines orchestration",
        plugin_type=PluginType.ORCHESTRATOR,
        packages=["google-cloud-aiplatform>=1.25", "kfp>=2.0"],
        wrapper_path="flowyml.plugins.orchestrators.vertex_ai:VertexAIOrchestrator",
        documentation_url="https://cloud.google.com/vertex-ai/docs/pipelines",
        tags=["orchestrator", "gcp", "cloud", "vertex-ai"],
    ),
    "sagemaker": PluginInfo(
        name="sagemaker",
        description="AWS SageMaker Pipelines orchestration",
        plugin_type=PluginType.ORCHESTRATOR,
        packages=["sagemaker>=2.100"],
        wrapper_path="flowyml.plugins.orchestrators.sagemaker:SageMakerOrchestrator",
        documentation_url="https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html",
        tags=["orchestrator", "aws", "cloud", "sagemaker"],
    ),
    # -------------------------------------------------------------------------
    # CONTAINER REGISTRIES
    # -------------------------------------------------------------------------
    "docker": PluginInfo(
        name="docker",
        description="Local Docker registry support",
        plugin_type=PluginType.CONTAINER_REGISTRY,
        packages=["docker>=6.0"],
        wrapper_path="flowyml.plugins.registries.docker:DockerRegistry",
        documentation_url="https://docs.docker.com/registry/",
        tags=["container-registry", "docker", "local"],
    ),
    "ecr": PluginInfo(
        name="ecr",
        description="AWS Elastic Container Registry",
        plugin_type=PluginType.CONTAINER_REGISTRY,
        packages=["boto3>=1.28"],
        wrapper_path="flowyml.plugins.registries.ecr:ECRRegistry",
        documentation_url="https://docs.aws.amazon.com/ecr/",
        tags=["container-registry", "aws", "cloud"],
    ),
    "gcr": PluginInfo(
        name="gcr",
        description="Google Container Registry / Artifact Registry",
        plugin_type=PluginType.CONTAINER_REGISTRY,
        packages=["google-cloud-artifact-registry>=1.0"],
        wrapper_path="flowyml.plugins.registries.gcr:GCRRegistry",
        documentation_url="https://cloud.google.com/artifact-registry/docs",
        tags=["container-registry", "gcp", "cloud"],
    ),
    "acr": PluginInfo(
        name="acr",
        description="Azure Container Registry",
        plugin_type=PluginType.CONTAINER_REGISTRY,
        packages=["azure-mgmt-containerregistry>=10.0"],
        wrapper_path="flowyml.plugins.registries.acr:ACRRegistry",
        documentation_url="https://docs.microsoft.com/azure/container-registry/",
        tags=["container-registry", "azure", "cloud"],
    ),
    # -------------------------------------------------------------------------
    # FEATURE STORES
    # -------------------------------------------------------------------------
    "feast": PluginInfo(
        name="feast",
        description="Feast feature store",
        plugin_type=PluginType.FEATURE_STORE,
        packages=["feast>=0.30"],
        wrapper_path="flowyml.plugins.stores.feast:FeastFeatureStore",
        documentation_url="https://docs.feast.dev/",
        tags=["feature-store", "ml-features", "popular"],
    ),
    # -------------------------------------------------------------------------
    # DATA VALIDATORS
    # -------------------------------------------------------------------------
    "great_expectations": PluginInfo(
        name="great_expectations",
        description="Great Expectations data validation",
        plugin_type=PluginType.DATA_VALIDATOR,
        packages=["great_expectations>=0.17"],
        wrapper_path="flowyml.plugins.validators.great_expectations:GEValidator",
        documentation_url="https://docs.greatexpectations.io/",
        tags=["data-validation", "testing", "popular"],
    ),
    "pandera": PluginInfo(
        name="pandera",
        description="Pandera DataFrame validation",
        plugin_type=PluginType.DATA_VALIDATOR,
        packages=["pandera>=0.15"],
        wrapper_path="flowyml.plugins.validators.pandera:PanderaValidator",
        documentation_url="https://pandera.readthedocs.io/",
        tags=["data-validation", "pandas", "schema"],
    ),
    "deepchecks": PluginInfo(
        name="deepchecks",
        description="Deepchecks Data Validator",
        plugin_type=PluginType.DATA_VALIDATOR,
        packages=["deepchecks>=0.17.0"],
        wrapper_path="flowyml.plugins.validators.deepchecks:DeepchecksValidator",
        documentation_url="https://docs.deepchecks.com/stable/general/usage/tabular/index.html",
        tags=["data-validation", "drift", "integrity"],
    ),
    # -------------------------------------------------------------------------
    # ALERTERS
    # -------------------------------------------------------------------------
    "slack": PluginInfo(
        name="slack",
        description="Slack notifications",
        plugin_type=PluginType.ALERTER,
        packages=["slack-sdk>=3.0"],
        wrapper_path="flowyml.plugins.alerters.slack:SlackAlerter",
        documentation_url="https://api.slack.com/",
        tags=["alerter", "notifications", "popular"],
    ),
    "discord": PluginInfo(
        name="discord",
        description="Discord webhook notifications",
        plugin_type=PluginType.ALERTER,
        packages=["discord-webhook>=1.0"],
        wrapper_path="flowyml.plugins.alerters.discord:DiscordAlerter",
        documentation_url="https://discord.com/developers/docs/resources/webhook",
        tags=["alerter", "notifications"],
    ),
    "pagerduty": PluginInfo(
        name="pagerduty",
        description="PagerDuty incident management",
        plugin_type=PluginType.ALERTER,
        packages=["pdpyras>=4.0"],
        wrapper_path="flowyml.plugins.alerters.pagerduty:PagerDutyAlerter",
        documentation_url="https://developer.pagerduty.com/",
        tags=["alerter", "incident-management", "enterprise"],
    ),
    # -------------------------------------------------------------------------
    # MODEL REGISTRIES
    # -------------------------------------------------------------------------
    "vertex_model_registry": PluginInfo(
        name="vertex_model_registry",
        description="Google Cloud Vertex AI Model Registry",
        plugin_type=PluginType.CUSTOM,  # MODEL_REGISTRY type
        packages=["google-cloud-aiplatform>=1.25"],
        wrapper_path="flowyml.plugins.model_registries.vertex:VertexModelRegistry",
        documentation_url="https://cloud.google.com/vertex-ai/docs/model-registry",
        tags=["model-registry", "gcp", "cloud", "vertex-ai"],
    ),
    "sagemaker_model_registry": PluginInfo(
        name="sagemaker_model_registry",
        description="AWS SageMaker Model Registry",
        plugin_type=PluginType.CUSTOM,  # MODEL_REGISTRY type
        packages=["boto3>=1.28", "sagemaker>=2.100"],
        wrapper_path="flowyml.plugins.model_registries.sagemaker:SageMakerModelRegistry",
        documentation_url="https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html",
        tags=["model-registry", "aws", "cloud", "sagemaker"],
    ),
    # -------------------------------------------------------------------------
    # MODEL DEPLOYERS
    # -------------------------------------------------------------------------
    "vertex_endpoint": PluginInfo(
        name="vertex_endpoint",
        description="Google Cloud Vertex AI Endpoint Deployer",
        plugin_type=PluginType.CUSTOM,  # MODEL_DEPLOYER type
        packages=["google-cloud-aiplatform>=1.25"],
        wrapper_path="flowyml.plugins.deployers.vertex:VertexEndpointDeployer",
        documentation_url="https://cloud.google.com/vertex-ai/docs/predictions",
        tags=["model-deployer", "gcp", "cloud", "vertex-ai", "inference"],
    ),
    "sagemaker_endpoint": PluginInfo(
        name="sagemaker_endpoint",
        description="AWS SageMaker Endpoint Deployer",
        plugin_type=PluginType.CUSTOM,  # MODEL_DEPLOYER type
        packages=["boto3>=1.28"],
        wrapper_path="flowyml.plugins.deployers.sagemaker:SageMakerEndpointDeployer",
        documentation_url="https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html",
        tags=["model-deployer", "aws", "cloud", "sagemaker", "inference"],
    ),
    "gcp_cloud_run": PluginInfo(
        name="gcp_cloud_run",
        description="Google Cloud Run Deployer",
        plugin_type=PluginType.CUSTOM,  # MODEL_DEPLOYER type
        packages=["google-cloud-run>=0.10.0"],
        wrapper_path="flowyml.plugins.deployers.gcp_cloud_run:GCPCloudRunDeployer",
        documentation_url="https://cloud.google.com/run/docs",
        tags=["model-deployer", "gcp", "serverless", "container"],
    ),
    "mlflow_registry": PluginInfo(
        name="mlflow_registry",
        description="MLflow Model Registry",
        plugin_type=PluginType.CUSTOM,  # MODEL_REGISTRY type
        packages=["mlflow>=2.0"],
        wrapper_path="flowyml.plugins.model_registries.mlflow:MLflowModelRegistry",
        documentation_url="https://mlflow.org/docs/latest/model-registry.html",
        tags=["model-registry", "mlflow", "versioning"],
    ),
}


# ============================================================================
# REGISTRY FUNCTIONS
# ============================================================================


def get_plugin_info(name: str) -> PluginInfo | None:
    """Get information about a plugin by name.

    Args:
        name: Plugin name.

    Returns:
        PluginInfo if found, None otherwise.
    """
    return PLUGIN_CATALOG.get(name)


def list_plugins(
    plugin_type: PluginType = None,
    tag: str = None,
    status: PluginStatus = None,
) -> list[PluginInfo]:
    """List plugins with optional filtering.

    Args:
        plugin_type: Filter by plugin type.
        tag: Filter by tag.
        status: Filter by status.

    Returns:
        List of matching PluginInfo objects.
    """
    results = list(PLUGIN_CATALOG.values())

    if plugin_type:
        results = [p for p in results if p.plugin_type == plugin_type]

    if tag:
        results = [p for p in results if tag in p.tags]

    if status:
        results = [p for p in results if p.status == status]

    return results


def list_plugin_names(plugin_type: PluginType = None) -> list[str]:
    """List plugin names with optional type filtering.

    Args:
        plugin_type: Optional filter by plugin type.

    Returns:
        List of plugin names.
    """
    if plugin_type:
        return [name for name, info in PLUGIN_CATALOG.items() if info.plugin_type == plugin_type]
    return list(PLUGIN_CATALOG.keys())


def register_plugin(info: PluginInfo) -> None:
    """Register a new plugin in the catalog.

    This allows community plugins to register themselves.

    Args:
        info: PluginInfo for the new plugin.
    """
    PLUGIN_CATALOG[info.name] = info


def unregister_plugin(name: str) -> bool:
    """Unregister a plugin from the catalog.

    Args:
        name: Plugin name to remove.

    Returns:
        True if plugin was removed.
    """
    if name in PLUGIN_CATALOG:
        del PLUGIN_CATALOG[name]
        return True
    return False

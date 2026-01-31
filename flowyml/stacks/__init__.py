"""Stack management for flowyml."""

from flowyml.stacks.base import Stack, StackConfig
from flowyml.stacks.local import LocalStack
from flowyml.stacks.gcp import GCPStack, VertexAIOrchestrator, GCSArtifactStore, GCRContainerRegistry
from flowyml.stacks.aws import AWSStack, AWSBatchOrchestrator, S3ArtifactStore, ECRContainerRegistry
from flowyml.stacks.azure import AzureMLStack, AzureMLOrchestrator, AzureBlobArtifactStore, ACRContainerRegistry
from flowyml.stacks.components import (
    ResourceConfig,
    DockerConfig,
    Orchestrator,
    ArtifactStore,
    ContainerRegistry,
)
from flowyml.stacks.registry import StackRegistry, get_registry, get_active_stack, set_active_stack
from flowyml.stacks.plugins import (
    get_component_registry,
    register_component,
    load_component,
)


# ZenML integration - lazy imports to avoid errors when ZenML is not installed
def get_zenml_bridge():
    """Get a ZenML bridge for importing ZenML components."""
    from flowyml.stacks.zenml_bridge import ZenMLBridge

    return ZenMLBridge()


def import_all_zenml():
    """Import all components from all installed ZenML integrations.

    This is the easiest way to make all ZenML components available
    in FlowyML with a single call.

    Example:
        >>> from flowyml.stacks import import_all_zenml
        >>> components = import_all_zenml()
    """
    from flowyml.stacks.zenml_bridge import import_all_zenml as _import_all

    return _import_all()


__all__ = [
    "Stack",
    "StackConfig",
    "LocalStack",
    "GCPStack",
    "AWSStack",
    "AzureMLStack",
    "VertexAIOrchestrator",
    "AWSBatchOrchestrator",
    "AzureMLOrchestrator",
    "GCSArtifactStore",
    "S3ArtifactStore",
    "AzureBlobArtifactStore",
    "GCRContainerRegistry",
    "ECRContainerRegistry",
    "ACRContainerRegistry",
    "ResourceConfig",
    "DockerConfig",
    "Orchestrator",
    "ArtifactStore",
    "ContainerRegistry",
    "StackRegistry",
    "get_registry",
    "get_active_stack",
    "set_active_stack",
    # Plugin system
    "get_component_registry",
    "register_component",
    "load_component",
    # ZenML integration
    "get_zenml_bridge",
    "import_all_zenml",
]

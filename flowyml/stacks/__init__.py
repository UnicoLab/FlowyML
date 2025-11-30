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
]

"""FlowyML Model Registry Plugins - Native implementations for ML model registries.

This module provides model registry plugin implementations for:
- Vertex AI Model Registry (GCP)
- SageMaker Model Registry (AWS)

Usage:
    from flowyml.plugins.model_registries import VertexModelRegistry

    # Or via config
    # model_registry:
    #   type: vertex_model_registry
    #   project: my-gcp-project
"""

from flowyml.plugins.model_registries.vertex import VertexModelRegistry
from flowyml.plugins.model_registries.sagemaker import SageMakerModelRegistry

__all__ = [
    "VertexModelRegistry",
    "SageMakerModelRegistry",
]

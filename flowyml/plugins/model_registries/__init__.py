"""FlowyML Model Registry Plugins - Native implementations for ML model registries.

This module provides model registry plugin implementations for:
- MLflow Model Registry
- Azure ML Model Registry
- Vertex AI Model Registry (GCP)
- SageMaker Model Registry (AWS)

Usage:
    from flowyml.plugins.model_registries import AzureMLModelRegistry

    # Or via config
    # model_registry:
    #   type: azureml_registry
    #   subscription_id: ...
    #   resource_group: ...
    #   workspace_name: ...
"""

from __future__ import annotations

from flowyml.plugins.model_registries.azureml import AzureMLModelRegistry
from flowyml.plugins.model_registries.mlflow import MLflowModelRegistry
from flowyml.plugins.model_registries.sagemaker import SageMakerModelRegistry
from flowyml.plugins.model_registries.vertex import VertexModelRegistry

__all__ = [
    "MLflowModelRegistry",
    "AzureMLModelRegistry",
    "VertexModelRegistry",
    "SageMakerModelRegistry",
]

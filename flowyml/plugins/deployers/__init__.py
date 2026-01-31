"""FlowyML Model Deployer Plugins - Native implementations for model deployment.

This module provides model deployer plugin implementations for:
- Vertex AI Endpoints (GCP)
- SageMaker Endpoints (AWS)

Usage:
    from flowyml.plugins.deployers import VertexEndpointDeployer, SageMakerEndpointDeployer

    # Or via config
    # model_deployer:
    #   type: vertex_endpoint
    #   project: my-gcp-project
"""

from flowyml.plugins.deployers.vertex import VertexEndpointDeployer
from flowyml.plugins.deployers.sagemaker import SageMakerEndpointDeployer

__all__ = [
    "VertexEndpointDeployer",
    "SageMakerEndpointDeployer",
]

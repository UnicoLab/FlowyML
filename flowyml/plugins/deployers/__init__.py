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

from __future__ import annotations

from flowyml.plugins.deployers.gcp_cloud_run import GCPCloudRunDeployer
from flowyml.plugins.deployers.sagemaker import SageMakerEndpointDeployer
from flowyml.plugins.deployers.vertex import VertexEndpointDeployer

__all__ = [
    "VertexEndpointDeployer",
    "SageMakerEndpointDeployer",
    "GCPCloudRunDeployer",
]

"""Verification tests for deployment and logging enhancements."""
import pytest
from unittest.mock import MagicMock
import sys

# Mock external cloud libs for import check
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.aiplatform"] = MagicMock()
sys.modules["google.cloud.storage"] = MagicMock()
sys.modules["google.cloud.logging"] = MagicMock()
sys.modules["boto3"] = MagicMock()

from flowyml.plugins.base import PluginType
from flowyml.stacks.components import ComponentType, Orchestrator
from flowyml.stacks.gcp import GCPStack
from flowyml.stacks.aws import AWSStack
from flowyml.plugins.deployers.gcp_cloud_run import GCPCloudRunDeployer


def test_enums():
    """Verify enums updated."""
    assert hasattr(PluginType, "MODEL_DEPLOYER")
    assert PluginType.MODEL_DEPLOYER.value == "model_deployer"

    assert hasattr(ComponentType, "MODEL_DEPLOYER")
    assert ComponentType.MODEL_DEPLOYER.value == "model_deployer"


def test_base_class():
    """Verify get_run_logs in base class."""
    assert hasattr(Orchestrator, "get_run_logs")


def test_cloud_run_deployer():
    """Verify Cloud Run deployer structure."""
    deployer = GCPCloudRunDeployer(project_id="test", region="us-central1")
    assert deployer.plugin_type == PluginType.MODEL_DEPLOYER


def test_gcp_stack():
    """Verify GCP Stack log retrieval and deployer."""
    stack = GCPStack(
        name="test-gcp",
        project_id="p",
        bucket_name="b",
        registry_uri="r",
        service_account="sa",
    )
    assert stack.model_deployer is not None
    assert isinstance(stack.model_deployer, GCPCloudRunDeployer)
    assert hasattr(stack.orchestrator, "get_run_logs")


def test_aws_stack():
    """Verify AWS Stack log retrieval and deployer."""
    stack = AWSStack(
        name="test-aws",
        region="us-east-1",
        bucket_name="b",
        account_id="123",
        role_arn="role",
    )
    # Default is sagemaker endpoint deployer from AWSStack init
    assert stack.model_deployer is not None
    assert hasattr(stack.orchestrator, "get_run_logs")

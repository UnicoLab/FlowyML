"""Verification script for deployment and logging enhancements."""
import sys
import unittest
from unittest.mock import MagicMock

# Mock external cloud libs for import check
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.aiplatform"] = MagicMock()
sys.modules["google.cloud.storage"] = MagicMock()
sys.modules["google.cloud.logging"] = MagicMock()
sys.modules["boto3"] = MagicMock()

try:
    from flowyml.plugins.base import PluginType
    from flowyml.stacks.components import ComponentType, Orchestrator
    from flowyml.stacks.gcp import GCPStack
    from flowyml.stacks.aws import AWSStack
    from flowyml.plugins.deployers.gcp_cloud_run import GCPCloudRunDeployer

    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


class TestDeploymentAndLogging(unittest.TestCase):
    def test_enums(self):
        """Verify enums updated."""
        self.assertTrue(hasattr(PluginType, "MODEL_DEPLOYER"))
        self.assertEqual(PluginType.MODEL_DEPLOYER.value, "model_deployer")

        self.assertTrue(hasattr(ComponentType, "MODEL_DEPLOYER"))
        self.assertEqual(ComponentType.MODEL_DEPLOYER.value, "model_deployer")
        print("✅ Enums verified")

    def test_base_class(self):
        """Verify get_run_logs in base class."""
        self.assertTrue(hasattr(Orchestrator, "get_run_logs"))
        print("✅ Base class verified")

    def test_cloud_run_deployer(self):
        """Verify Cloud Run deployer structure."""
        deployer = GCPCloudRunDeployer(project_id="test", region="us-central1")
        self.assertEqual(deployer.plugin_type, PluginType.MODEL_DEPLOYER)
        print("✅ Cloud Run deployer verified")

    def test_gcp_stack(self):
        """Verify GCP Stack log retrieval and deployer."""
        stack = GCPStack(
            name="test-gcp",
            project_id="p",
            bucket_name="b",
            registry_uri="r",
            service_account="sa",
        )
        self.assertIsNotNone(stack.model_deployer)
        self.assertTrue(isinstance(stack.model_deployer, GCPCloudRunDeployer))
        self.assertTrue(hasattr(stack.orchestrator, "get_run_logs"))
        print("✅ GCP Stack verified")

    def test_aws_stack(self):
        """Verify AWS Stack log retrieval and deployer."""
        stack = AWSStack(
            name="test-aws",
            region="us-east-1",
            bucket_name="b",
            account_id="123",
            role_arn="role",
        )
        # Default is sagemaker endpoint deployer from AWSStack init
        self.assertIsNotNone(stack.model_deployer)
        self.assertTrue(hasattr(stack.orchestrator, "get_run_logs"))
        print("✅ AWS Stack verified")


if __name__ == "__main__":
    unittest.main()

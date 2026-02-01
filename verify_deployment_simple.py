"""Simplified verification script for deployment and logging enhancements."""
import sys
from unittest.mock import MagicMock

# Mock external cloud libs for import check
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.aiplatform"] = MagicMock()
sys.modules["google.cloud.storage"] = MagicMock()
sys.modules["google.cloud.logging"] = MagicMock()
sys.modules["boto3"] = MagicMock()


def verify():
    print("🚀 Starting verification...")
    try:
        from flowyml.plugins.base import PluginType
        from flowyml.stacks.components import ComponentType, Orchestrator
        from flowyml.stacks.gcp import GCPStack
        from flowyml.stacks.aws import AWSStack
        from flowyml.plugins.deployers.gcp_cloud_run import GCPCloudRunDeployer

        print("✅ All imports successful")

        # Verify Enums
        if not hasattr(PluginType, "MODEL_DEPLOYER") or PluginType.MODEL_DEPLOYER.value != "model_deployer":
            print("❌ PluginType enum failed")
            return
        if not hasattr(ComponentType, "MODEL_DEPLOYER") or ComponentType.MODEL_DEPLOYER.value != "model_deployer":
            print("❌ ComponentType enum failed")
            return
        print("✅ Enums verified")

        # Verify Base Class
        if not hasattr(Orchestrator, "get_run_logs"):
            print("❌ Orchestrator.get_run_logs missing")
            return
        print("✅ Orchestrator base class verified")

        # Verify Cloud Run Deployer
        deployer = GCPCloudRunDeployer(project_id="test", region="us-central1")
        if deployer.plugin_type != PluginType.MODEL_DEPLOYER:
            print(f"❌ Cloud Run deployer type mismatch: {deployer.plugin_type}")
            return
        print("✅ Cloud Run deployer verified")

        # Verify GCP Stack
        stack = GCPStack(
            name="test-gcp",
            project_id="p",
            bucket_name="b",
            registry_uri="r",
            service_account="sa",
        )
        if not isinstance(stack.model_deployer, GCPCloudRunDeployer):
            print("❌ GCP Stack model deployer type mismatch")
            return
        if not hasattr(stack.orchestrator, "get_run_logs"):
            print("❌ GCP Orchestrator missing get_run_logs")
            return
        print("✅ GCP Stack verified")

        # Verify AWS Stack
        stack_aws = AWSStack(
            name="test-aws",
            region="us-east-1",
            bucket_name="b",
            account_id="123",
            role_arn="role",
        )
        if stack_aws.model_deployer is None:
            print("❌ AWS Stack model deployer missing")
            return
        if not hasattr(stack_aws.orchestrator, "get_run_logs"):
            print("❌ AWS Orchestrator missing get_run_logs")
            return
        print("✅ AWS Stack verified")

        print("🎉 All checks passed!")

    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    verify()

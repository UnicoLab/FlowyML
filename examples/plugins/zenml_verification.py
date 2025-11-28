"""Verification script for ZenML integration via GenericBridge."""

import sys
from unittest.mock import MagicMock

from uniflow.stacks.components import ArtifactStore, Orchestrator
from uniflow.stacks.plugins import get_component_registry

# Mock ZenML modules since we might not have them installed
mock_zenml = MagicMock()
mock_k8s = MagicMock()
mock_s3 = MagicMock()


# Define mock classes
class KubernetesOrchestrator:
    def __init__(self, **kwargs):
        self.config = kwargs

    def run(self, pipeline, **kwargs):
        print(f"🚀 [ZenML K8s] Running pipeline {pipeline} with config {self.config}")
        return "run_id_123"


class S3ArtifactStore:
    def __init__(self, **kwargs):
        self.config = kwargs

    def save(self, artifact, path):
        print(f"💾 [ZenML S3] Saving to {path}")

    def load(self, path):
        print(f"📂 [ZenML S3] Loading from {path}")

    def exists(self, path):
        return True


mock_k8s.KubernetesOrchestrator = KubernetesOrchestrator
mock_s3.S3ArtifactStore = S3ArtifactStore

sys.modules["zenml"] = mock_zenml
sys.modules["zenml.integrations.kubernetes.orchestrators"] = mock_k8s
sys.modules["zenml.integrations.s3.artifact_stores"] = mock_s3


def verify_zenml_integration():
    print("🔌 Loading ZenML plugins from config...")
    registry = get_component_registry()
    registry.load_plugins_from_config("examples/plugins/zenml_config.yaml")

    # Verify Orchestrator
    print("\n✅ Verifying Orchestrator...")
    k8s_cls = registry.get_orchestrator("zenml_k8s_orchestrator")
    if k8s_cls:
        orch = k8s_cls(namespace="uniflow-prod")
        if not isinstance(orch, Orchestrator):
            msg = "K8s component is not an Orchestrator instance"
            raise TypeError(msg)
        print(f"   Loaded: {orch.name}")
        orch.run_pipeline("my_pipeline")
    else:
        print("❌ Failed to load orchestrator")

    # Verify Artifact Store
    print("\n✅ Verifying Artifact Store...")
    s3_cls = registry.get_artifact_store("zenml_s3_store")
    if s3_cls:
        store = s3_cls(bucket="my-bucket")
        if not isinstance(store, ArtifactStore):
            msg = "S3 component is not an ArtifactStore instance"
            raise TypeError(msg)
        print(f"   Loaded: {store.name}")
        store.save("data", "s3://path")
    else:
        print("❌ Failed to load artifact store")


if __name__ == "__main__":
    verify_zenml_integration()

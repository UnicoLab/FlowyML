"""
Example: Integrating existing ZenML components.

Shows how to reuse ZenML community components in UniFlow.
"""

# Method 1: Direct wrapping
from uniflow.stacks.plugins import get_component_registry

# Load ZenML component
try:
    from zenml.integrations.kubernetes.orchestrators import KubernetesOrchestrator as ZenMLK8s

    registry = get_component_registry()
    registry.wrap_zenml_component(ZenMLK8s, "k8s")

    print("✅ ZenML Kubernetes orchestrator loaded")
except ImportError:
    print("⚠️  ZenML not installed. Install with: pip install zenml[kubernetes]")


# Method 2: Via configuration (uniflow.yaml)
# Example configuration:
# components:
#   - zenml: zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator
#     name: k8s
#
#   - zenml: zenml.integrations.aws.artifact_stores.S3ArtifactStore
#     name: s3
#
# stacks:
#   k8s_stack:
#     orchestrator:
#       type: k8s
#       kubernetes_context: my-cluster
#       kubernetes_namespace: uniflow
#
#     artifact_store:
#       type: s3
#       bucket: my-bucket
#       region: us-east-1


# Method 3: CLI
# Load ZenML component:
#   uniflow component load zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator
#
# List available:
#   uniflow component list


# Method 4: Complete ZenML stack migration
from uniflow.stacks import Stack
from uniflow.stacks.plugins import get_component_registry


def migrate_zenml_stack():
    """Migrate entire ZenML stack to UniFlow."""
    try:
        from zenml.client import Client as ZenMLClient

        zenml_client = ZenMLClient()
        zenml_stack = zenml_client.active_stack

        registry = get_component_registry()

        # Wrap all components
        registry.wrap_zenml_component(
            zenml_stack.orchestrator,
            "zenml_orchestrator",
        )

        registry.wrap_zenml_component(
            zenml_stack.artifact_store,
            "zenml_artifact_store",
        )

        if zenml_stack.container_registry:
            registry.wrap_zenml_component(
                zenml_stack.container_registry,
                "zenml_registry",
            )

        # Create UniFlow stack
        uniflow_stack = Stack(
            name=f"migrated_{zenml_stack.name}",
            orchestrator=registry.get_orchestrator("zenml_orchestrator"),
            artifact_store=registry.get_artifact_store("zenml_artifact_store"),
            container_registry=registry.get_container_registry("zenml_registry"),
        )

        print(f"✅ Migrated ZenML stack: {zenml_stack.name}")
        return uniflow_stack

    except ImportError:
        print("⚠️  ZenML not installed")
        return None


if __name__ == "__main__":
    # Example: migrate and use
    stack = migrate_zenml_stack()

    if stack:
        from uniflow import Pipeline, step

        @step
        def hello():
            return {"message": "Hello from migrated stack!"}

        pipeline = Pipeline("test", stack=stack)
        pipeline.add_step(hello)

        result = pipeline.run()
        print(f"Result: {result}")

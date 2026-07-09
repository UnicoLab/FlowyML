"""Wiring tests for the deployment layer as stacks / components / plugins.

These tests assert that the new model deployers and model registries are:

* discoverable through the global ``ComponentRegistry`` by their ``type:`` key,
* constructable from a ``flowyml.yaml``-style config through *both* hydration
  paths (``plugins.stack_config.StackConfig`` and the enterprise
  ``StackDefinition``),
* exposed on a live ``Stack`` via ``.model_deployer`` / ``.model_registry`` so
  ``DeploymentService`` and champion/challenger promotion pick them up, and
* governable through the enterprise ``PolicyEngine`` (allowed-flavor policy).

Cloud SDKs are never imported at construction time (deployers/registries lazy
initialise), so these tests run without azure/mlflow/boto3 installed.
"""

from __future__ import annotations

import pytest

from flowyml.deployment.models import DeploymentSpec, DeploymentTarget, ModelRef
from flowyml.deployment.service import DeploymentService
from flowyml.deployment.targets.kubernetes import KubernetesDeployer, OpenShiftDeployer
from flowyml.deployment.targets.local_docker import LocalDockerDeployer
from flowyml.plugins.model_registries.azureml import AzureMLModelRegistry
from flowyml.plugins.model_registries.mlflow import MLflowModelRegistry
from flowyml.plugins.stack_config import StackConfig
from flowyml.stacks.enterprise.exceptions import PolicyViolationError
from flowyml.stacks.enterprise.models import StackDefinition
from flowyml.stacks.enterprise.policy import PolicyContext, PolicyEngine
from flowyml.stacks.plugins import get_component_registry


# --------------------------------------------------------------------------- #
# Component registry discovery                                                 #
# --------------------------------------------------------------------------- #
# The example flowyml.yaml uses these ``type:`` keys.
_DEPLOYER_TYPES = {
    "local_docker": LocalDockerDeployer,
    "kubernetes": KubernetesDeployer,
    "openshift": OpenShiftDeployer,
}
_REGISTRY_TYPES = {
    "azureml_registry": AzureMLModelRegistry,
    "mlflow_registry": MLflowModelRegistry,
}


@pytest.mark.parametrize("type_key,expected", sorted(_DEPLOYER_TYPES.items()))
def test_deployer_types_resolve_via_registry(type_key: str, expected: type) -> None:
    """Each deployer ``type:`` key resolves to its class through the registry."""
    # Importing the targets module fires the ``@register_component`` decorators.
    import flowyml.deployment.targets  # noqa: F401

    registry = get_component_registry()
    assert registry.get_component(type_key) is expected
    assert registry.get_model_deployer(type_key) is expected
    assert type_key in registry.list_model_deployers()


@pytest.mark.parametrize("type_key,expected", sorted(_REGISTRY_TYPES.items()))
def test_registry_types_resolve_via_registry(type_key: str, expected: type) -> None:
    """Each model registry ``type:`` key resolves through the registry."""
    import flowyml.plugins.model_registries  # noqa: F401

    registry = get_component_registry()
    assert registry.get_component(type_key) is expected
    assert registry.get_model_registry(type_key) is expected
    assert type_key in registry.list_model_registries()


def test_example_yaml_types_all_resolve() -> None:
    """Every ``type:`` key used in examples/production_serving/flowyml.yaml resolves."""
    from flowyml.plugins.stack_config import _ensure_providers_loaded

    registry = get_component_registry()
    for type_key in (
        "local_docker",
        "openshift",
        "kubernetes",
        "azureml_registry",
        "mlflow_registry",
        "azure_blob",
    ):
        _ensure_providers_loaded(type_key)
        assert registry.get_component(type_key) is not None, type_key


# --------------------------------------------------------------------------- #
# Path 1: plugins.stack_config.StackConfig.to_stack()                          #
# --------------------------------------------------------------------------- #
def test_stackconfig_hydrates_deployer_and_registry() -> None:
    """The 'azureml-openshift' example stack hydrates a live Stack with both."""
    cfg = StackConfig.from_dict(
        "azureml-openshift",
        {
            "orchestrator": {"type": "local"},
            "artifact_store": {"type": "local", "path": "./.flowyml/artifacts"},
            "model_registry": {
                "type": "azureml_registry",
                "subscription_id": "sub",
                "resource_group": "rg",
                "workspace_name": "ws",
            },
            "model_deployer": {
                "type": "openshift",
                "namespace": "ml-prod",
                "registry_uri": "registry.example.com/ml-prod",
            },
        },
    )
    stack = cfg.to_stack()

    assert isinstance(stack.model_deployer, OpenShiftDeployer)
    assert stack.model_deployer.target == DeploymentTarget.OPENSHIFT
    assert stack.model_deployer.default_namespace == "ml-prod"
    assert isinstance(stack.model_registry, AzureMLModelRegistry)
    assert stack.model_registry.subscription_id == "sub"


def test_stackconfig_local_docker_and_mlflow() -> None:
    """The local + mlflow variants also resolve through the same path."""
    local = StackConfig.from_dict(
        "local",
        {"orchestrator": {"type": "local"}, "model_deployer": {"type": "local_docker"}},
    )
    assert isinstance(local.to_stack().model_deployer, LocalDockerDeployer)

    mlf = StackConfig.from_dict(
        "azureml-mlflow",
        {
            "model_registry": {"type": "mlflow_registry", "registry_uri": "sqlite:///r.db"},
            "model_deployer": {"type": "kubernetes", "namespace": "ml"},
        },
    )
    live = mlf.to_stack()
    assert isinstance(live.model_registry, MLflowModelRegistry)
    assert isinstance(live.model_deployer, KubernetesDeployer)


def test_deployment_service_uses_active_stack_deployer() -> None:
    """DeploymentService resolves the deployer attached to the active stack."""
    cfg = StackConfig.from_dict(
        "prod",
        {"orchestrator": {"type": "local"}, "model_deployer": {"type": "openshift"}},
    )
    stack = cfg.to_stack()
    service = DeploymentService(stack=stack)
    spec = DeploymentSpec(name="churn", model=ModelRef("churn"), target="openshift")

    resolved = service._resolve_deployer(spec)
    assert resolved is stack.model_deployer


# --------------------------------------------------------------------------- #
# Path 2: enterprise StackDefinition.to_stack() + governance                   #
# --------------------------------------------------------------------------- #
def _governed_def(
    *,
    deployer: str = "openshift",
    registry: str = "azureml_registry",
    allowed_deployers: list[str] | None = None,
    allowed_registries: list[str] | None = None,
) -> StackDefinition:
    """Build a governed StackDefinition with a deployment section."""
    return StackDefinition.from_dict(
        {
            "apiVersion": "flowyml.io/v1",
            "kind": "Stack",
            "metadata": {"name": "aml-openshift", "version": "1.0.0", "owner": "ml-platform"},
            "spec": {
                "backend": "local",
                "deployment": {
                    "modelDeployer": deployer,
                    "modelRegistry": registry,
                    "namespace": "ml-prod",
                },
                "policies": {
                    "allowedModelDeployers": allowed_deployers or [],
                    "allowedModelRegistries": allowed_registries or [],
                },
            },
        },
    )


def test_enterprise_definition_validates_and_hydrates() -> None:
    """A governed enterprise stack validates and attaches deployer/registry."""
    sd = _governed_def()
    assert sd.spec.deployment.model_deployer == "openshift"
    assert sd.spec.deployment.model_registry == "azureml_registry"

    stack = sd.to_stack()
    assert isinstance(stack.model_deployer, OpenShiftDeployer)
    assert stack.model_deployer.default_namespace == "ml-prod"
    assert isinstance(stack.model_registry, AzureMLModelRegistry)


def test_enterprise_definition_rejects_unknown_flavor() -> None:
    """Unknown deployer/registry flavors are rejected at validation time."""
    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
        _governed_def(deployer="not_a_real_deployer")


def test_policy_allows_approved_flavors() -> None:
    """The policy engine passes when the flavors are on the allowlist."""
    sd = _governed_def(
        allowed_deployers=["openshift", "kubernetes"],
        allowed_registries=["azureml_registry"],
    )
    engine = PolicyEngine()
    # Should not raise.
    engine.check(PolicyContext(stack=sd, user="alice", user_groups=["ds"]))


def test_policy_blocks_disallowed_deployer() -> None:
    """The policy engine blocks a deployer that is not on the allowlist."""
    sd = _governed_def(allowed_deployers=["kubernetes"])
    engine = PolicyEngine()
    with pytest.raises(PolicyViolationError):
        engine.check(PolicyContext(stack=sd))


def test_policy_blocks_disallowed_registry() -> None:
    """The policy engine blocks a registry that is not on the allowlist."""
    sd = _governed_def(allowed_registries=["mlflow_registry"])
    engine = PolicyEngine()
    with pytest.raises(PolicyViolationError):
        engine.check(PolicyContext(stack=sd))

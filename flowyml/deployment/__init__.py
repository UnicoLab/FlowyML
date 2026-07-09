"""FlowyML deployment layer.

Transparent packaging, versioning, and serving of registered models across
serving runtimes (FastAPI, Triton, TensorFlow Serving) and targets (local
Docker, Kubernetes, OpenShift), plus champion/challenger promotion.

Typical usage::

    from flowyml.deployment import DeploymentSpec, ModelRef, DeploymentService

    spec = DeploymentSpec(
        name="churn-api",
        model=ModelRef("churn", stage="production"),
        runtime="fastapi",
        target="openshift",
        namespace="ml-prod",
        route_host="churn.apps.example.com",
    )
    result = DeploymentService().deploy(spec)
    print(result.endpoint_url)
"""

from __future__ import annotations

from flowyml.deployment.bundle import ModelBundle, ResolvedModel, build_bundle, resolve_model
from flowyml.deployment.models import (
    Autoscaling,
    DeploymentResult,
    DeploymentSpec,
    DeploymentStatus,
    DeploymentTarget,
    ModelRef,
    ResourceRequests,
    ServingRuntime,
)
from flowyml.deployment.batch import BatchInferenceJob, BatchInferenceResult, run_batch_inference
from flowyml.deployment.promotion import PromotionDecision, promote_if_better
from flowyml.deployment.service import DeploymentService, DeploymentStore, deploy_model

__all__ = [
    # models
    "ServingRuntime",
    "DeploymentTarget",
    "DeploymentStatus",
    "ModelRef",
    "ResourceRequests",
    "Autoscaling",
    "DeploymentSpec",
    "DeploymentResult",
    # packaging
    "ModelBundle",
    "ResolvedModel",
    "build_bundle",
    "resolve_model",
    # orchestration
    "DeploymentService",
    "DeploymentStore",
    "deploy_model",
    # promotion
    "promote_if_better",
    "PromotionDecision",
    # batch
    "run_batch_inference",
    "BatchInferenceJob",
    "BatchInferenceResult",
]


def get_deployment_service(stack=None, registry=None) -> DeploymentService:
    """Return a :class:`DeploymentService` bound to the given/active stack."""
    if stack is None:
        try:
            from flowyml.stacks.registry import get_active_stack

            stack = get_active_stack()
        except Exception:  # noqa: BLE001
            stack = None
    return DeploymentService(stack=stack, registry=registry)

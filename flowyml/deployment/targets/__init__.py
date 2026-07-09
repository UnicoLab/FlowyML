"""Deployment targets (local Docker, Kubernetes, OpenShift)."""

from __future__ import annotations

from flowyml.deployment.targets.kubernetes import KubernetesDeployer, OpenShiftDeployer
from flowyml.deployment.targets.local_docker import LocalDockerDeployer

__all__ = ["LocalDockerDeployer", "KubernetesDeployer", "OpenShiftDeployer"]


def get_deployer(target: str, **config):
    """Instantiate a deployer for a :class:`DeploymentTarget` value/string."""
    from flowyml.deployment.models import DeploymentTarget

    key = target.value if isinstance(target, DeploymentTarget) else str(target)
    mapping = {
        DeploymentTarget.LOCAL_DOCKER.value: LocalDockerDeployer,
        DeploymentTarget.LOCAL.value: LocalDockerDeployer,
        DeploymentTarget.KUBERNETES.value: KubernetesDeployer,
        DeploymentTarget.OPENSHIFT.value: OpenShiftDeployer,
    }
    if key not in mapping:
        raise ValueError(f"Unknown deployment target '{key}'. Available: {sorted(mapping)}")
    return mapping[key](**config)

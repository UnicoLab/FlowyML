"""Local Docker deployment target.

Builds the serving image and runs it as a container on the local Docker daemon.
Ideal for development, CI smoke tests, and the end-to-end tutorial.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flowyml.deployment.base import BaseDeployer
from flowyml.deployment.models import DeploymentResult, DeploymentStatus, DeploymentTarget
from flowyml.stacks.plugins import register_component

if TYPE_CHECKING:
    from flowyml.deployment.bundle import ModelBundle
    from flowyml.deployment.models import DeploymentSpec


@register_component(name="local_docker")
class LocalDockerDeployer(BaseDeployer):
    """Deploy a model as a local Docker container."""

    target = DeploymentTarget.LOCAL_DOCKER

    def _container_name(self, spec_or_name: Any) -> str:
        name = spec_or_name.dns_name if hasattr(spec_or_name, "dns_name") else str(spec_or_name)
        from flowyml.deployment.models import _sanitize_name

        return f"flowyml-{_sanitize_name(name)}"

    def deploy(self, spec: DeploymentSpec, bundle: ModelBundle) -> DeploymentResult:
        from flowyml.deployment import docker_utils

        if not docker_utils.docker_available():
            raise RuntimeError("Docker is not available on PATH; cannot use the local_docker target.")

        if not docker_utils.daemon_running():
            raise RuntimeError(
                "Docker daemon is not running. Start Docker Desktop (or the docker "
                "service) and retry the local_docker deployment.",
            )

        image, ctx = self.build_serving_image(spec, bundle, push=False)
        container = self._container_name(spec)
        docker_utils.stop_container(container)  # idempotent redeploy

        host_port = spec.port
        docker_utils.run_container(
            image,
            container,
            ports={host_port: ctx.port},
            env={**ctx.env, **spec.env},
        )

        endpoint = f"http://localhost:{host_port}"
        return self._result(
            spec,
            bundle,
            DeploymentStatus.RUNNING,
            image=image,
            endpoint_url=endpoint,
            predict_url=endpoint.rstrip("/") + ctx.predict_path,
            message=f"Container {container} running on {endpoint}",
            details={"container": container, "container_port": ctx.port},
        )

    def get_status(self, name: str, namespace: str | None = None) -> DeploymentResult:
        from flowyml.deployment import docker_utils

        container = self._container_name(name)
        state = docker_utils.container_status(container)
        if state is None:
            return DeploymentResult(
                name=name,
                status=DeploymentStatus.STOPPED,
                target=self.target.value,
                runtime="unknown",
                message="No container found",
            )
        running = state.get("Running", False)
        ports = docker_utils.container_published_ports(container)
        host_port = next(iter(ports.values()), None)
        endpoint = f"http://localhost:{host_port}" if host_port else None
        return DeploymentResult(
            name=name,
            status=DeploymentStatus.RUNNING if running else DeploymentStatus.STOPPED,
            target=self.target.value,
            runtime="unknown",
            endpoint_url=endpoint,
            predict_url=(endpoint.rstrip("/") + "/predict") if endpoint else None,
            details={"container": container, "state": state},
        )

    def undeploy(self, name: str, namespace: str | None = None) -> bool:
        from flowyml.deployment import docker_utils

        return docker_utils.stop_container(self._container_name(name))

"""Base class for deployment targets.

A :class:`BaseDeployer` is a first-class stack component (``ComponentType.MODEL_DEPLOYER``)
that knows how to take a :class:`~flowyml.deployment.models.DeploymentSpec` plus a
packaged :class:`~flowyml.deployment.bundle.ModelBundle` and run it somewhere
(local docker, OpenShift, Kubernetes, ...).

Targets share image build/push logic via helpers here; subclasses implement the
scheduling/placement specifics.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from flowyml.deployment.models import DeploymentResult, DeploymentStatus, DeploymentTarget
from flowyml.deployment.runtimes.base import BuildContext, get_serving_builder
from flowyml.stacks.components import ComponentType, StackComponent

if TYPE_CHECKING:
    from flowyml.deployment.bundle import ModelBundle
    from flowyml.deployment.models import DeploymentSpec


class BaseDeployer(StackComponent):
    """Abstract base for all deployment targets."""

    target: DeploymentTarget

    def __init__(self, name: str = "deployer", **config: Any) -> None:
        super().__init__(name)
        self.config = config

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.MODEL_DEPLOYER

    # ---- lifecycle (subclasses implement) --------------------------------- #
    @abstractmethod
    def deploy(self, spec: DeploymentSpec, bundle: ModelBundle) -> DeploymentResult:
        """Build (if needed), schedule, and expose the model. Returns a result."""

    @abstractmethod
    def get_status(self, name: str, namespace: str | None = None) -> DeploymentResult:
        """Return the current status of a deployment by name."""

    @abstractmethod
    def undeploy(self, name: str, namespace: str | None = None) -> bool:
        """Tear down a deployment. Returns True on success."""

    def list_deployments(self, namespace: str | None = None) -> list[DeploymentResult]:
        """List deployments managed by this target (best-effort)."""
        return []

    def predict(self, name: str, data: Any, namespace: str | None = None) -> Any:
        """Call a running deployment's predict endpoint over HTTP."""
        import requests

        status = self.get_status(name, namespace=namespace)
        url = status.predict_url or ((status.endpoint_url.rstrip("/") + "/predict") if status.endpoint_url else None)
        if not url:
            raise RuntimeError(f"Deployment '{name}' has no reachable predict URL (status={status.status.value})")
        payload = data if isinstance(data, dict) else {"inputs": data}
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ---- shared build/push helpers ---------------------------------------- #
    def build_serving_image(
        self,
        spec: DeploymentSpec,
        bundle: ModelBundle,
        *,
        build_dir: str | None = None,
        push: bool = False,
    ) -> tuple[str, BuildContext]:
        """Prepare a build context via the runtime builder and build the image.

        Returns ``(image_ref, build_context)``. If ``spec.image`` is set the
        build is skipped and that image is returned. When ``push`` is True and a
        registry is configured, the image is tagged and pushed.
        """
        import tempfile

        from flowyml.deployment import docker_utils

        builder = get_serving_builder(spec.runtime)
        build_dir = build_dir or tempfile.mkdtemp(prefix=f"flowyml-build-{spec.dns_name}-")
        ctx = builder.prepare(spec, bundle, build_dir)

        if spec.image:
            return spec.image, ctx

        registry = spec.registry_uri or self.config.get("registry_uri")
        image_tag = ctx.image_name
        if registry:
            image_tag = f"{registry.rstrip('/')}/{ctx.image_name}"

        docker_utils.build_image(
            ctx.build_dir,
            image_tag,
            dockerfile=ctx.dockerfile,
            platform=self.config.get("platform", "linux/amd64"),
        )
        if push and registry:
            docker_utils.push_image(image_tag)
        return image_tag, ctx

    # ---- StackComponent contract ------------------------------------------ #
    def validate(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "component_type": self.component_type.value,
            "target": getattr(self, "target", DeploymentTarget.LOCAL_DOCKER).value,
            "config": self.config,
        }

    def _result(
        self,
        spec: DeploymentSpec,
        bundle: ModelBundle | None,
        status: DeploymentStatus,
        **kwargs: Any,
    ) -> DeploymentResult:
        from datetime import datetime

        return DeploymentResult(
            name=spec.name,
            status=status,
            target=self.target.value,
            runtime=spec.runtime.value,
            model_name=bundle.name if bundle else spec.model.name,
            model_version=bundle.version if bundle else spec.model.version,
            namespace=spec.namespace,
            replicas=spec.replicas,
            created_at=datetime.now().isoformat(),
            **kwargs,
        )

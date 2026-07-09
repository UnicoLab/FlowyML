"""Kubernetes and OpenShift deployment targets.

These build/push the serving image and apply generated manifests via the
cluster CLI (``kubectl`` for Kubernetes, ``oc`` for OpenShift).  Manifest
generation is delegated to :mod:`flowyml.deployment.targets.manifests` and is
side-effect free, so ``--dry-run`` renders YAML without touching a cluster.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import TYPE_CHECKING, Any

from flowyml.deployment.base import BaseDeployer
from flowyml.deployment.models import DeploymentResult, DeploymentStatus, DeploymentTarget
from flowyml.deployment.targets import manifests as m
from flowyml.stacks.plugins import register_component

if TYPE_CHECKING:
    from flowyml.deployment.bundle import ModelBundle
    from flowyml.deployment.models import DeploymentSpec

logger = logging.getLogger(__name__)


class _KubeCliError(RuntimeError):
    pass


@register_component(name="kubernetes")
class KubernetesDeployer(BaseDeployer):
    """Deploy models to a Kubernetes cluster via ``kubectl``."""

    target = DeploymentTarget.KUBERNETES
    cli = "kubectl"
    openshift = False

    def __init__(self, name: str = "kubernetes", **config: Any) -> None:
        super().__init__(name, **config)
        self.cli = config.get("cli", self.cli)
        self.default_namespace = config.get("namespace")

    # ---- CLI helpers ------------------------------------------------------ #
    def _ns_args(self, namespace: str | None) -> list[str]:
        ns = namespace or self.default_namespace
        return ["-n", ns] if ns else []

    def _run(
        self,
        args: list[str],
        *,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        cmd = [self.cli, *args]
        logger.debug("exec: %s", " ".join(cmd))
        try:
            return subprocess.run(cmd, input=input_text, capture_output=True, text=True, check=check)
        except FileNotFoundError as exc:
            raise _KubeCliError(f"'{self.cli}' not found on PATH") from exc
        except subprocess.CalledProcessError as exc:
            raise _KubeCliError(f"{' '.join(cmd)} failed: {exc.stderr or exc.stdout}") from exc

    # ---- lifecycle -------------------------------------------------------- #
    def render(self, spec: DeploymentSpec, image: str, container_port: int, health_path: str) -> str:
        """Render manifests to YAML (no cluster interaction)."""
        return m.to_yaml(
            m.render_manifests(spec, image, container_port, health_path, openshift=self.openshift),
        )

    def deploy(self, spec: DeploymentSpec, bundle: ModelBundle) -> DeploymentResult:
        dry_run = bool(spec.extra.get("dry_run"))

        # Build & push image (a registry is required for a real cluster deploy).
        if spec.image:
            image, ctx_port, health_path, predict_path = spec.image, spec.port, "/health", "/predict"
            from flowyml.deployment.runtimes.base import get_serving_builder  # for ctx only
            import tempfile

            ctx = get_serving_builder(spec.runtime).prepare(spec, bundle, tempfile.mkdtemp())
            ctx_port, health_path, predict_path = ctx.port, ctx.health_path, ctx.predict_path
        else:
            push = not dry_run
            image, ctx = self.build_serving_image(spec, bundle, push=push)
            ctx_port, health_path, predict_path = ctx.port, ctx.health_path, ctx.predict_path

        manifests_yaml = self.render(spec, image, ctx_port, health_path)

        if dry_run:
            return self._result(
                spec,
                bundle,
                DeploymentStatus.PENDING,
                image=image,
                message="Dry run — manifests rendered but not applied",
                details={"manifests": manifests_yaml},
            )

        self._run(["apply", "-f", "-", *self._ns_args(spec.namespace)], input_text=manifests_yaml)
        # Wait for rollout (best-effort)
        try:
            self._run(
                ["rollout", "status", f"deployment/{spec.dns_name}", "--timeout=180s", *self._ns_args(spec.namespace)],
            )
        except _KubeCliError as exc:
            logger.warning("Rollout wait failed: %s", exc)

        endpoint = self._resolve_endpoint(spec)
        return self._result(
            spec,
            bundle,
            DeploymentStatus.RUNNING,
            image=image,
            endpoint_url=endpoint,
            predict_url=(endpoint.rstrip("/") + predict_path) if endpoint else None,
            message=f"Applied to {self.cli} cluster",
            details={"manifests": manifests_yaml},
        )

    def _resolve_endpoint(self, spec: DeploymentSpec) -> str | None:
        if spec.route_host:
            return f"https://{spec.route_host}"
        return None

    def get_status(self, name: str, namespace: str | None = None) -> DeploymentResult:
        from flowyml.deployment.models import _sanitize_name

        dns = _sanitize_name(name)
        try:
            result = self._run(["get", "deployment", dns, "-o", "json", *self._ns_args(namespace)])
        except _KubeCliError:
            return DeploymentResult(
                name=name,
                status=DeploymentStatus.UNKNOWN,
                target=self.target.value,
                runtime="unknown",
                message="Not found",
            )
        data = json.loads(result.stdout)
        status = data.get("status", {})
        ready = status.get("readyReplicas", 0)
        desired = status.get("replicas", 0)
        state = DeploymentStatus.RUNNING if ready and ready == desired else DeploymentStatus.DEPLOYING
        return DeploymentResult(
            name=name,
            status=state,
            target=self.target.value,
            runtime="unknown",
            replicas=desired,
            namespace=namespace or self.default_namespace,
            details={"ready_replicas": ready, "replicas": desired},
        )

    def undeploy(self, name: str, namespace: str | None = None) -> bool:
        from flowyml.deployment.models import _sanitize_name

        dns = _sanitize_name(name)
        ok = True
        for kind in ("deployment", "service", "horizontalpodautoscaler", self._route_kind()):
            try:
                self._run(["delete", kind, dns, "--ignore-not-found", *self._ns_args(namespace)])
            except _KubeCliError as exc:
                logger.warning("Failed to delete %s/%s: %s", kind, dns, exc)
                ok = False
        return ok

    def _route_kind(self) -> str:
        return "route" if self.openshift else "ingress"


@register_component(name="openshift")
class OpenShiftDeployer(KubernetesDeployer):
    """Deploy models to OpenShift via ``oc`` (adds Route + edge TLS)."""

    target = DeploymentTarget.OPENSHIFT
    cli = "oc"
    openshift = True

    def __init__(self, name: str = "openshift", **config: Any) -> None:
        super().__init__(name, **config)
        self.cli = config.get("cli", "oc")

    def _resolve_endpoint(self, spec: DeploymentSpec) -> str | None:
        if spec.route_host:
            return f"https://{spec.route_host}"
        # Ask OpenShift for the auto-generated route host
        try:
            result = self._run(
                ["get", "route", spec.dns_name, "-o", "jsonpath={.spec.host}", *self._ns_args(spec.namespace)],
            )
            host = result.stdout.strip()
            return f"https://{host}" if host else None
        except _KubeCliError:
            return None

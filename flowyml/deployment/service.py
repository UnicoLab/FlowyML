"""High-level deployment orchestration.

:class:`DeploymentService` is the single entry point that ties everything
together: it packages a model from the registry (transparent fetch/version),
selects a deployment target (from the spec or the active stack's
``model_deployer``), deploys it, and records the deployment so it can be listed,
inspected, predicted against, and torn down later.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from flowyml.deployment.bundle import build_bundle
from flowyml.deployment.models import DeploymentResult, DeploymentSpec

logger = logging.getLogger(__name__)


class DeploymentStore:
    """Small JSON-backed store of deployment records."""

    def __init__(self, path: str | Path = ".flowyml/deployments.json") -> None:
        self.path = Path(path)

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, default=str))

    def save(self, result: DeploymentResult, spec: DeploymentSpec | None = None) -> None:
        data = self._read()
        record = result.to_dict()
        if spec is not None:
            record["spec"] = spec.to_dict()
        data[result.name] = record
        self._write(data)

    def get(self, name: str) -> dict[str, Any] | None:
        return self._read().get(name)

    def list(self) -> list[dict[str, Any]]:  # noqa: A003
        return list(self._read().values())

    def delete(self, name: str) -> None:
        data = self._read()
        data.pop(name, None)
        self._write(data)


class DeploymentService:
    """Orchestrates packaging + deployment across targets and runtimes."""

    def __init__(
        self,
        *,
        stack: Any = None,
        registry: Any = None,
        store: DeploymentStore | None = None,
    ) -> None:
        self.stack = stack
        self.registry = registry
        self.store = store or DeploymentStore()

    # ---- target resolution ------------------------------------------------ #
    def _resolve_deployer(self, spec: DeploymentSpec):
        from flowyml.deployment.base import BaseDeployer
        from flowyml.deployment.targets import get_deployer

        # 1. A deployer explicitly attached to the active stack takes precedence
        #    *only* when it matches the requested target (or the spec left it default).
        stack_deployer = getattr(self.stack, "model_deployer", None) if self.stack else None
        if isinstance(stack_deployer, BaseDeployer):
            if getattr(stack_deployer, "target", None) == spec.target:
                return stack_deployer

        # 2. Otherwise instantiate the deployer for the requested target.
        config: dict[str, Any] = {}
        if spec.namespace:
            config["namespace"] = spec.namespace
        if spec.registry_uri:
            config["registry_uri"] = spec.registry_uri
        return get_deployer(spec.target, **config)

    # ---- lifecycle -------------------------------------------------------- #
    def deploy(self, spec: DeploymentSpec, *, bundle_dir: str | None = None) -> DeploymentResult:
        """Package the referenced model and deploy it per ``spec``."""
        logger.info(
            "Deploying '%s' (model=%s runtime=%s target=%s)",
            spec.name,
            spec.model.name,
            spec.runtime.value,
            spec.target.value,
        )
        bundle = build_bundle(
            spec.model,
            output_dir=bundle_dir,
            registry=self.registry,
            extra_requirements=spec.requirements or None,
        )
        deployer = self._resolve_deployer(spec)
        result = deployer.deploy(spec, bundle)
        self.store.save(result, spec)
        return result

    def status(self, name: str) -> DeploymentResult:
        record = self.store.get(name)
        if record is None:
            raise ValueError(f"No deployment named '{name}' is recorded")
        spec = DeploymentSpec.from_dict(record["spec"]) if record.get("spec") else None
        deployer = self._resolve_deployer(spec) if spec else None
        if deployer is None:
            from flowyml.deployment.targets import get_deployer

            deployer = get_deployer(record.get("target", "local_docker"))
        namespace = spec.namespace if spec else record.get("namespace")
        result = deployer.get_status(name, namespace=namespace)
        self.store.save(result, spec)
        return result

    def undeploy(self, name: str) -> bool:
        record = self.store.get(name)
        if record is None:
            raise ValueError(f"No deployment named '{name}' is recorded")
        spec = DeploymentSpec.from_dict(record["spec"]) if record.get("spec") else None
        if spec is not None:
            deployer = self._resolve_deployer(spec)
            namespace = spec.namespace
        else:
            from flowyml.deployment.targets import get_deployer

            deployer = get_deployer(record.get("target", "local_docker"))
            namespace = record.get("namespace")
        ok = deployer.undeploy(name, namespace=namespace)
        if ok:
            self.store.delete(name)
        return ok

    def predict(self, name: str, data: Any) -> Any:
        record = self.store.get(name)
        if record is None:
            raise ValueError(f"No deployment named '{name}' is recorded")
        spec = DeploymentSpec.from_dict(record["spec"]) if record.get("spec") else None
        deployer = self._resolve_deployer(spec) if spec else None
        if deployer is None:
            from flowyml.deployment.targets import get_deployer

            deployer = get_deployer(record.get("target", "local_docker"))
        namespace = spec.namespace if spec else record.get("namespace")
        return deployer.predict(name, data, namespace=namespace)

    def list(self) -> list[dict[str, Any]]:  # noqa: A003
        return self.store.list()


def deploy_model(
    model: str | dict | Any,
    *,
    name: str | None = None,
    runtime: str = "fastapi",
    target: str = "local_docker",
    stack: Any = None,
    registry: Any = None,
    **spec_kwargs: Any,
) -> DeploymentResult:
    """Convenience one-liner to deploy a model by name/ref.

    Example:
        >>> deploy_model("churn", stage="production", runtime="fastapi", target="openshift")
    """
    from flowyml.deployment.models import ModelRef

    if isinstance(model, str):
        model_ref = ModelRef(name=model, **{k: spec_kwargs.pop(k) for k in ("version", "stage") if k in spec_kwargs})
    elif isinstance(model, dict):
        model_ref = ModelRef.from_dict(model)
    else:
        model_ref = model

    spec = DeploymentSpec(
        name=name or f"{model_ref.name}-endpoint",
        model=model_ref,
        runtime=runtime,
        target=target,
        **spec_kwargs,
    )
    return DeploymentService(stack=stack, registry=registry).deploy(spec)

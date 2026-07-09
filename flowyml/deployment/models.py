"""Core data models for the FlowyML deployment layer.

These models describe *what* to deploy (a versioned model), *how* to serve it
(a serving runtime), and *where* to run it (a deployment target).  They are
intentionally plain dataclasses (mirroring ``ServerConfig``/``ResourceConfig``
elsewhere in the codebase) so they can be serialized to/from ``flowyml.yaml``
and passed transparently through pipelines, the CLI, and the stack system.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ServingRuntime(str, Enum):
    """How a model is served inside its container/process."""

    FASTAPI = "fastapi"
    TRITON = "triton"
    TENSORFLOW_SERVING = "tensorflow_serving"
    TORCHSERVE = "torchserve"
    CUSTOM = "custom"


class DeploymentTarget(str, Enum):
    """Where a serving container/process runs."""

    LOCAL = "local"  # in-process, for development
    LOCAL_DOCKER = "local_docker"  # docker run on the local machine
    OPENSHIFT = "openshift"
    KUBERNETES = "kubernetes"


class DeploymentStatus(str, Enum):
    """Lifecycle status of a deployment."""

    PENDING = "pending"
    BUILDING = "building"
    PUSHING = "pushing"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


def _sanitize_name(name: str) -> str:
    """Return a DNS-1123 compliant name (valid for k8s/openshift objects)."""
    sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized or "flowyml-model"


@dataclass
class ResourceRequests:
    """Compute resource requests/limits for a serving workload."""

    cpu: str = "500m"
    memory: str = "1Gi"
    gpu: int = 0
    cpu_limit: str | None = None
    memory_limit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ResourceRequests:
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Autoscaling:
    """Horizontal autoscaling configuration (HPA on k8s/openshift)."""

    enabled: bool = False
    min_replicas: int = 1
    max_replicas: int = 3
    target_cpu_utilization: int = 70

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Autoscaling:
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ModelRef:
    """A transparent handle to a model living in a registry.

    This is the crux of "packaging/fetching/versioning is transparent": the
    user references a model by ``name`` plus either an explicit ``version`` or a
    ``stage`` (e.g. ``production``), and the deployment layer resolves, fetches,
    and packages the concrete artifact.

    Attributes:
        name: Registered model name.
        version: Explicit version (e.g. ``"v3"``). Mutually exclusive with stage.
        stage: Stage to resolve the version from (e.g. ``"production"``).
        registry: Registry backend name. ``None`` uses the stack default or the
            built-in SQL registry.
        uri: Optional direct artifact URI, bypassing registry resolution.
        framework: Optional framework hint (usually resolved from the registry).
    """

    name: str
    version: str | None = None
    stage: str | None = None
    registry: str | None = None
    uri: str | None = None
    framework: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelRef:
        if isinstance(data, str):
            return cls(name=data)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DeploymentSpec:
    """Full specification of a deployment.

    A ``DeploymentSpec`` is portable and declarative: it can be constructed in
    Python, loaded from ``flowyml.yaml``, or produced by a champion/challenger
    promotion step, and then handed to a ``DeploymentService``.
    """

    name: str
    model: ModelRef
    runtime: ServingRuntime = ServingRuntime.FASTAPI
    target: DeploymentTarget = DeploymentTarget.LOCAL_DOCKER

    # Runtime / container
    port: int = 8080
    image: str | None = None  # pre-built image (skips build)
    base_image: str | None = None  # override the runtime's default base image
    registry_uri: str | None = None  # container registry to push the serving image to
    env: dict[str, str] = field(default_factory=dict)
    requirements: list[str] = field(default_factory=list)  # extra pip deps baked in
    # Local Python files/dirs to bake into the serving image so custom model code
    # (rule-based classes, Bayesian predict fns, ...) is importable at serve time.
    code_paths: list[str] = field(default_factory=list)

    # Scaling / resources
    replicas: int = 1
    resources: ResourceRequests = field(default_factory=ResourceRequests)
    autoscaling: Autoscaling = field(default_factory=Autoscaling)

    # Cluster placement (k8s / openshift)
    namespace: str | None = None
    service_account: str | None = None
    route_host: str | None = None  # OpenShift Route host / k8s Ingress host
    expose: bool = True  # create a Route/Ingress
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    image_pull_secret: str | None = None

    # Escape hatch for target/runtime-specific knobs
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.model, dict):
            self.model = ModelRef.from_dict(self.model)
        if isinstance(self.model, str):
            self.model = ModelRef(name=self.model)
        self.runtime = ServingRuntime(self.runtime)
        self.target = DeploymentTarget(self.target)
        if isinstance(self.resources, dict):
            self.resources = ResourceRequests.from_dict(self.resources)
        if isinstance(self.autoscaling, dict):
            self.autoscaling = Autoscaling.from_dict(self.autoscaling)

    @property
    def dns_name(self) -> str:
        """Kubernetes/OpenShift-safe object name."""
        return _sanitize_name(self.name)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["runtime"] = self.runtime.value
        data["target"] = self.target.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeploymentSpec:
        data = dict(data)
        model = data.pop("model", None)
        name = data.pop("name")
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        extra = {k: v for k, v in data.items() if k not in cls.__dataclass_fields__}
        if extra:
            known.setdefault("extra", {}).update(extra)
        return cls(name=name, model=ModelRef.from_dict(model), **known)

    @classmethod
    def from_yaml(cls, path: str) -> DeploymentSpec:
        import yaml

        with open(path) as f:
            return cls.from_dict(yaml.safe_load(f))


@dataclass
class DeploymentResult:
    """Result of a deploy/status operation."""

    name: str
    status: DeploymentStatus
    target: str
    runtime: str
    endpoint_url: str | None = None
    predict_url: str | None = None
    image: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    namespace: str | None = None
    replicas: int = 1
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None

    def __post_init__(self) -> None:
        self.status = DeploymentStatus(self.status)

    @property
    def is_running(self) -> bool:
        return self.status == DeploymentStatus.RUNNING

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

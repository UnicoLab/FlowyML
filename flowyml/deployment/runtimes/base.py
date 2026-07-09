"""Serving-runtime image builders.

A :class:`ServingImageBuilder` turns a :class:`~flowyml.deployment.bundle.ModelBundle`
into a *build context*: a directory containing everything needed to build a
container image that serves the model with a particular runtime (FastAPI,
Triton, TensorFlow Serving, ...).  Deployment targets then build/push that
image and schedule it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flowyml.deployment.bundle import ModelBundle
    from flowyml.deployment.models import DeploymentSpec, ServingRuntime


@dataclass
class BuildContext:
    """Everything a target needs to build a serving image."""

    build_dir: str
    dockerfile: str  # path to the Dockerfile (relative to build_dir or absolute)
    image_name: str  # suggested image name:tag (without registry prefix)
    port: int
    runtime: str
    labels: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    # Health/readiness probe paths (HTTP GET)
    health_path: str = "/health"
    predict_path: str = "/predict"


class ServingImageBuilder(ABC):
    """Base class for serving-runtime image builders."""

    runtime: ServingRuntime

    @abstractmethod
    def prepare(self, spec: DeploymentSpec, bundle: ModelBundle, build_dir: str) -> BuildContext:
        """Populate ``build_dir`` and return the :class:`BuildContext`."""

    def supports(self, framework: str) -> bool:  # noqa: D401 - simple predicate
        """Whether this runtime can serve ``framework`` models."""
        return True


_BUILDER_REGISTRY: dict[str, type[ServingImageBuilder]] = {}


def register_serving_builder(runtime: str, cls: type[ServingImageBuilder]) -> None:
    _BUILDER_REGISTRY[str(runtime)] = cls


def get_serving_builder(runtime: Any) -> ServingImageBuilder:
    """Return an instance of the builder for ``runtime``."""
    from flowyml.deployment.models import ServingRuntime

    key = runtime.value if isinstance(runtime, ServingRuntime) else str(runtime)
    # Lazily import built-ins so registration happens on first use
    from flowyml.deployment import runtimes as _runtimes  # noqa: F401

    if key not in _BUILDER_REGISTRY:
        raise ValueError(
            f"No serving runtime builder registered for '{key}'. " f"Available: {sorted(_BUILDER_REGISTRY)}",
        )
    return _BUILDER_REGISTRY[key]()

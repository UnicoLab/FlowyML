"""Model packaging: resolve a versioned model from a registry and build a
portable, self-describing *model bundle*.

A bundle is a directory with a stable, framework-agnostic layout::

    <bundle>/
        model/                 # the raw model artifact (file or dir, verbatim)
        metadata.json          # name, version, framework, metrics, signature...
        requirements.txt       # runtime dependencies (best-effort)

Bundles are the unit that serving-runtime builders (FastAPI/Triton/TF Serving)
and deployment targets consume, which is what makes packaging/fetching/
versioning transparent to user code.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from flowyml.deployment.models import ModelRef

logger = logging.getLogger(__name__)


@dataclass
class ResolvedModel:
    """A model version resolved from a registry, pointing at raw artifact files."""

    name: str
    version: str
    framework: str
    model_path: str
    stage: str = "none"
    metrics: dict[str, float] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    signature: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ModelBundle:
    """A portable, self-describing package of a resolved model."""

    name: str
    version: str
    framework: str
    path: str  # bundle root directory
    model_subpath: str = "model"  # relative to path
    metrics: dict[str, float] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    signature: dict[str, Any] = field(default_factory=dict)
    requirements: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def model_path(self) -> str:
        return str(Path(self.path) / self.model_subpath)

    def to_metadata(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("path", None)
        return data


def _default_registry():
    """Return the built-in SQL-backed model registry."""
    from flowyml.registry.model_registry import ModelRegistry

    return ModelRegistry()


def resolve_model(model_ref: ModelRef, registry: Any = None) -> ResolvedModel:
    """Resolve a :class:`ModelRef` to concrete artifact files + metadata.

    Args:
        model_ref: The model reference to resolve.
        registry: Optional registry object. Must expose ``get_version`` /
            ``get_latest_version`` compatible with the built-in ``ModelRegistry``.
            When ``None`` the built-in SQL registry is used.

    Returns:
        A :class:`ResolvedModel`.

    Raises:
        ValueError: If the model/version cannot be found.
    """
    from flowyml.registry.model_registry import ModelStage

    reg = registry if registry is not None else _default_registry()

    stage = None
    if model_ref.stage:
        stage = ModelStage(model_ref.stage) if not isinstance(model_ref.stage, ModelStage) else model_ref.stage

    if model_ref.version:
        mv = reg.get_version(model_ref.name, model_ref.version)
    else:
        mv = reg.get_latest_version(model_ref.name, stage=stage)

    if mv is None:
        raise ValueError(
            f"Model '{model_ref.name}' "
            f"(version={model_ref.version}, stage={model_ref.stage}) not found in registry",
        )

    return ResolvedModel(
        name=mv.name,
        version=mv.version,
        framework=model_ref.framework or mv.framework,
        model_path=mv.model_path,
        stage=mv.stage.value if hasattr(mv.stage, "value") else str(mv.stage),
        metrics=dict(mv.metrics or {}),
        tags=dict(mv.tags or {}),
        signature=dict(mv.schema or {}),
        description=mv.description or "",
    )


def _infer_requirements(framework: str, extra: list[str] | None = None) -> list[str]:
    """Best-effort runtime requirements for a framework."""
    base: dict[str, list[str]] = {
        "sklearn": ["scikit-learn", "joblib", "numpy"],
        "scikit-learn": ["scikit-learn", "joblib", "numpy"],
        "pytorch": ["torch", "numpy"],
        "torch": ["torch", "numpy"],
        "tensorflow": ["tensorflow", "numpy"],
        "keras": ["keras", "tensorflow", "numpy"],
        "xgboost": ["xgboost", "numpy"],
        "lightgbm": ["lightgbm", "numpy"],
        "pymc": ["pymc", "arviz", "numpy", "cloudpickle"],
        "bayesian": ["pymc", "arviz", "numpy", "cloudpickle"],
        "rule_based": ["numpy", "cloudpickle"],
        "onnx": ["onnxruntime", "numpy"],
    }
    reqs = list(base.get((framework or "").lower(), ["numpy", "cloudpickle"]))
    for pkg in extra or []:
        if pkg not in reqs:
            reqs.append(pkg)
    return reqs


def build_bundle(
    model_ref: ModelRef | str,
    output_dir: str | Path | None = None,
    *,
    registry: Any = None,
    extra_requirements: list[str] | None = None,
) -> ModelBundle:
    """Resolve, fetch, and package a model into a portable bundle directory.

    Args:
        model_ref: A :class:`ModelRef` or a model name string.
        output_dir: Destination directory. A temp dir is used when ``None``.
        registry: Optional registry object (see :func:`resolve_model`).
        extra_requirements: Extra pip packages to record in the bundle.

    Returns:
        A :class:`ModelBundle` describing the packaged model.
    """
    if isinstance(model_ref, str):
        model_ref = ModelRef(name=model_ref)

    resolved = resolve_model(model_ref, registry=registry)

    if output_dir is None:
        import tempfile

        output_dir = tempfile.mkdtemp(prefix=f"flowyml-bundle-{resolved.name}-")
    bundle_dir = Path(output_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Copy raw model artifact (file or directory) verbatim into <bundle>/model
    src = Path(resolved.model_path)
    dst = bundle_dir / "model"
    if dst.exists():
        shutil.rmtree(dst) if dst.is_dir() else dst.unlink()

    if src.is_dir():
        shutil.copytree(src, dst)
    elif src.exists():
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst / src.name)
    else:
        raise FileNotFoundError(f"Model artifact not found on disk: {src}")

    requirements = _infer_requirements(resolved.framework, extra_requirements)

    bundle = ModelBundle(
        name=resolved.name,
        version=resolved.version,
        framework=resolved.framework,
        path=str(bundle_dir),
        model_subpath="model",
        metrics=resolved.metrics,
        tags=resolved.tags,
        signature=resolved.signature,
        requirements=requirements,
        description=resolved.description,
    )

    (bundle_dir / "metadata.json").write_text(json.dumps(bundle.to_metadata(), indent=2, default=str))
    (bundle_dir / "requirements.txt").write_text("\n".join(requirements) + "\n")

    logger.info("Built model bundle for %s:%s at %s", bundle.name, bundle.version, bundle.path)
    return bundle

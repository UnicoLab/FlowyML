"""TensorFlow Serving runtime builder.

Serves TensorFlow SavedModel artifacts via the official ``tensorflow/serving``
image.  Requires the bundle to contain a SavedModel (a directory with
``saved_model.pb``); other frameworks should use the FastAPI or Triton runtime.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from flowyml.deployment.models import ServingRuntime, _sanitize_name
from flowyml.deployment.runtimes.base import (
    BuildContext,
    ServingImageBuilder,
    register_serving_builder,
)

if TYPE_CHECKING:
    from flowyml.deployment.bundle import ModelBundle
    from flowyml.deployment.models import DeploymentSpec

_DEFAULT_TFS_IMAGE = "tensorflow/serving:2.15.0"

# TF Serving reads MODEL_NAME and serves REST on 8501 / gRPC on 8500.
_DOCKERFILE = """\
FROM {base_image}

ENV MODEL_NAME={model_name}
COPY models /models

EXPOSE 8500 8501
"""


def _saved_model_root(model_dir: Path) -> Path:
    if (model_dir / "saved_model.pb").exists():
        return model_dir
    for candidate in model_dir.rglob("saved_model.pb"):
        return candidate.parent
    return model_dir


class TensorFlowServingBuilder(ServingImageBuilder):
    """Serve TensorFlow SavedModels via TensorFlow Serving."""

    runtime = ServingRuntime.TENSORFLOW_SERVING

    def supports(self, framework: str) -> bool:
        return (framework or "").lower() in ("tensorflow", "keras")

    def prepare(self, spec: DeploymentSpec, bundle: ModelBundle, build_dir: str) -> BuildContext:
        framework = (bundle.framework or "").lower()
        if framework not in ("tensorflow", "keras"):
            raise ValueError(
                f"TensorFlow Serving requires a TensorFlow SavedModel; got framework='{framework}'. "
                "Use the FastAPI or Triton runtime for this model.",
            )

        build_path = Path(build_dir)
        build_path.mkdir(parents=True, exist_ok=True)

        model_name = _sanitize_name(bundle.name).replace("-", "_")
        saved = _saved_model_root(Path(bundle.model_path))
        if not (saved / "saved_model.pb").exists():
            raise ValueError(
                f"No saved_model.pb found under {bundle.model_path}. "
                "The model must be exported as a TensorFlow SavedModel.",
            )

        # TF Serving expects /models/<name>/<version>/<savedmodel contents>
        dst = build_path / "models" / model_name / "1"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(saved, dst)

        base_image = spec.base_image or _DEFAULT_TFS_IMAGE
        (build_path / "Dockerfile").write_text(
            _DOCKERFILE.format(base_image=base_image, model_name=model_name),
        )

        return BuildContext(
            build_dir=str(build_path),
            dockerfile=str(build_path / "Dockerfile"),
            image_name=f"flowyml-tfserving-{bundle.name}:{bundle.version}",
            port=8501,
            runtime=self.runtime.value,
            labels={
                "flowyml.model": bundle.name,
                "flowyml.version": str(bundle.version),
                "flowyml.runtime": self.runtime.value,
            },
            env={"MODEL_NAME": model_name},
            health_path=f"/v1/models/{model_name}",
            predict_path=f"/v1/models/{model_name}:predict",
        )


register_serving_builder(ServingRuntime.TENSORFLOW_SERVING.value, TensorFlowServingBuilder)

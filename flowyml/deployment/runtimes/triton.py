"""NVIDIA Triton Inference Server runtime builder.

Builds a Triton *model repository* from a bundle and a Dockerfile based on the
official ``tritonserver`` image.  Native backends are used for ONNX,
TensorFlow (SavedModel), and TorchScript models; everything else falls back to
the Triton **Python backend** (loading the artifact with joblib/cloudpickle),
which covers sklearn, PyMC/Bayesian, and rule-based models.

Repository layout produced::

    model_repository/<name>/
        config.pbtxt
        1/<artifact | model.py>
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

_DEFAULT_TRITON_IMAGE = "nvcr.io/nvidia/tritonserver:24.08-py3"

_DOCKERFILE = """\
FROM {base_image}

COPY model_repository /models
{pip_line}
EXPOSE 8000 8001 8002

CMD ["tritonserver", "--model-repository=/models", "--strict-model-config=false"]
"""

# Triton Python backend model.py for non-native frameworks
_PYTHON_BACKEND = """\
import json
import os

import numpy as np
import triton_python_backend_utils as pb_utils


def _load_model(model_dir):
    candidates = []
    for root, _dirs, files in os.walk(model_dir):
        for f in files:
            candidates.append(os.path.join(root, f))
    for path in candidates:
        for loader in ("joblib", "cloudpickle", "pickle"):
            try:
                if loader == "joblib":
                    import joblib
                    return joblib.load(path)
                if loader == "cloudpickle":
                    import cloudpickle
                    with open(path, "rb") as fh:
                        return cloudpickle.load(fh)
                import pickle
                with open(path, "rb") as fh:
                    return pickle.load(fh)
            except Exception:
                continue
    raise RuntimeError("Could not load model artifact from " + model_dir)


class TritonPythonModel:
    def initialize(self, args):
        model_dir = os.path.join(args["model_repository"], args["model_version"])
        self.model = _load_model(model_dir)

    def execute(self, requests):
        responses = []
        for request in requests:
            in_tensor = pb_utils.get_input_tensor_by_name(request, "INPUT0")
            x = in_tensor.as_numpy()
            if hasattr(self.model, "predict"):
                y = self.model.predict(x)
            else:
                y = self.model(x)
            y = np.asarray(y, dtype=np.float32)
            out = pb_utils.Tensor("OUTPUT0", y)
            responses.append(pb_utils.InferenceResponse(output_tensors=[out]))
        return responses
"""

_CONFIG_PYTHON = """\
name: "{name}"
backend: "python"
max_batch_size: 0
input [
  {{
    name: "INPUT0"
    data_type: TYPE_FP32
    dims: [ -1, -1 ]
  }}
]
output [
  {{
    name: "OUTPUT0"
    data_type: TYPE_FP32
    dims: [ -1 ]
  }}
]
instance_group [{{ kind: KIND_CPU }}]
"""

_CONFIG_ONNX = """\
name: "{name}"
backend: "onnxruntime"
max_batch_size: 0
"""

_CONFIG_TF = """\
name: "{name}"
platform: "tensorflow_savedmodel"
max_batch_size: 0
"""

_CONFIG_PT = """\
name: "{name}"
platform: "pytorch_libtorch"
max_batch_size: 0
input [
  {{
    name: "INPUT0"
    data_type: TYPE_FP32
    dims: [ -1, -1 ]
  }}
]
output [
  {{
    name: "OUTPUT0"
    data_type: TYPE_FP32
    dims: [ -1 ]
  }}
]
"""


def _find_artifact(model_dir: Path) -> Path:
    files = [p for p in model_dir.rglob("*") if p.is_file()]
    return files[0] if files else model_dir


class TritonServingBuilder(ServingImageBuilder):
    """Serve models via NVIDIA Triton Inference Server."""

    runtime = ServingRuntime.TRITON

    def prepare(self, spec: DeploymentSpec, bundle: ModelBundle, build_dir: str) -> BuildContext:
        build_path = Path(build_dir)
        build_path.mkdir(parents=True, exist_ok=True)

        model_name = _sanitize_name(bundle.name).replace("-", "_")
        repo = build_path / "model_repository" / model_name
        version_dir = repo / "1"
        version_dir.mkdir(parents=True, exist_ok=True)

        framework = (bundle.framework or "").lower()
        model_src = Path(bundle.model_path)
        pip_line = ""

        if framework == "onnx":
            artifact = _find_artifact(model_src)
            shutil.copy2(artifact, version_dir / "model.onnx")
            (repo / "config.pbtxt").write_text(_CONFIG_ONNX.format(name=model_name))
        elif framework == "tensorflow":
            # SavedModel directory
            saved = model_src if (model_src / "saved_model.pb").exists() else _saved_model_root(model_src)
            shutil.copytree(saved, version_dir / "model.savedmodel")
            (repo / "config.pbtxt").write_text(_CONFIG_TF.format(name=model_name))
        elif framework in ("pytorch", "torch"):
            artifact = _find_artifact(model_src)
            shutil.copy2(artifact, version_dir / "model.pt")
            (repo / "config.pbtxt").write_text(_CONFIG_PT.format(name=model_name))
        else:
            # Python backend fallback (sklearn, pymc, bayesian, rule_based, ...)
            if model_src.is_dir():
                shutil.copytree(model_src, version_dir / "artifact")
            else:
                (version_dir / "artifact").mkdir(exist_ok=True)
                shutil.copy2(model_src, version_dir / "artifact" / model_src.name)
            (version_dir / "model.py").write_text(_PYTHON_BACKEND)
            (repo / "config.pbtxt").write_text(_CONFIG_PYTHON.format(name=model_name))
            deps = " ".join(bundle.requirements + list(spec.requirements))
            if deps:
                pip_line = f"RUN pip install --no-cache-dir {deps}\n"

        base_image = spec.base_image or _DEFAULT_TRITON_IMAGE
        (build_path / "Dockerfile").write_text(
            _DOCKERFILE.format(base_image=base_image, pip_line=pip_line),
        )

        return BuildContext(
            build_dir=str(build_path),
            dockerfile=str(build_path / "Dockerfile"),
            image_name=f"flowyml-triton-{bundle.name}:{bundle.version}",
            port=8000,
            runtime=self.runtime.value,
            labels={
                "flowyml.model": bundle.name,
                "flowyml.version": str(bundle.version),
                "flowyml.runtime": self.runtime.value,
            },
            health_path=f"/v2/models/{model_name}/ready",
            predict_path=f"/v2/models/{model_name}/infer",
        )


def _saved_model_root(model_dir: Path) -> Path:
    """Find the directory containing saved_model.pb within a bundle model dir."""
    for candidate in model_dir.rglob("saved_model.pb"):
        return candidate.parent
    return model_dir


register_serving_builder(ServingRuntime.TRITON.value, TritonServingBuilder)

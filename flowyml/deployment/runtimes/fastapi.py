"""FastAPI serving-runtime image builder.

Produces a build context that serves *any* FlowyML model bundle through the
self-contained :mod:`flowyml.deployment.serving_app` (copied in as ``serve.py``
so the resulting image does not depend on flowyml itself).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from flowyml.deployment.models import ServingRuntime
from flowyml.deployment.runtimes.base import (
    BuildContext,
    ServingImageBuilder,
    register_serving_builder,
)

if TYPE_CHECKING:
    from flowyml.deployment.bundle import ModelBundle
    from flowyml.deployment.models import DeploymentSpec

_DOCKERFILE = """\
FROM {base_image}

ENV PYTHONUNBUFFERED=1 \\
    MODEL_BUNDLE_DIR=/models \\
    PYTHONPATH=/app:/app/code \\
    PORT={port}

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY serve.py /app/serve.py
COPY code /app/code
COPY model_bundle /models

EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\
    CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','{port}')+'/health')" || exit 1

CMD ["python", "serve.py"]
"""

_SERVE_REQUIREMENTS = ["fastapi>=0.100", "uvicorn[standard]>=0.23", "numpy", "prometheus-client>=0.19"]


class FastAPIServingBuilder(ServingImageBuilder):
    """Serve models via a FastAPI app (framework-agnostic)."""

    runtime = ServingRuntime.FASTAPI

    def prepare(self, spec: DeploymentSpec, bundle: ModelBundle, build_dir: str) -> BuildContext:
        build_path = Path(build_dir)
        build_path.mkdir(parents=True, exist_ok=True)

        # 1. Copy the bundle into the build context
        dst_bundle = build_path / "model_bundle"
        if dst_bundle.exists():
            shutil.rmtree(dst_bundle)
        shutil.copytree(bundle.path, dst_bundle)

        # 2. Copy the self-contained serving app as serve.py
        serving_app_src = Path(__file__).resolve().parent.parent / "serving_app.py"
        shutil.copy2(serving_app_src, build_path / "serve.py")

        # 2b. Bake in user-provided model code so custom classes/functions
        #     (rule-based, Bayesian predict fns) are importable at serve time.
        #     Everything lands in /app/code which is on PYTHONPATH.
        code_dir = build_path / "code"
        code_dir.mkdir(exist_ok=True)
        for code_path in spec.code_paths:
            src = Path(code_path)
            if not src.exists():
                raise FileNotFoundError(f"code_path does not exist: {code_path}")
            dst = code_dir / src.name
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        # 3. Merge requirements: bundle framework deps + serving deps + user extras
        reqs: list[str] = []
        for pkg in [*bundle.requirements, *_SERVE_REQUIREMENTS, *spec.requirements]:
            if pkg not in reqs:
                reqs.append(pkg)
        (build_path / "requirements.txt").write_text("\n".join(reqs) + "\n")

        base_image = spec.base_image or "python:3.11-slim"
        (build_path / "Dockerfile").write_text(
            _DOCKERFILE.format(base_image=base_image, port=spec.port),
        )

        return BuildContext(
            build_dir=str(build_path),
            dockerfile=str(build_path / "Dockerfile"),
            image_name=f"flowyml-serve-{bundle.name}:{bundle.version}",
            port=spec.port,
            runtime=self.runtime.value,
            labels={
                "flowyml.model": bundle.name,
                "flowyml.version": str(bundle.version),
                "flowyml.runtime": self.runtime.value,
            },
            env={"MODEL_BUNDLE_DIR": "/models", "PORT": str(spec.port)},
        )


register_serving_builder(ServingRuntime.FASTAPI.value, FastAPIServingBuilder)

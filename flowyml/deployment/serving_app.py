"""Self-contained FastAPI serving application for a FlowyML model bundle.

This module is intentionally free of ``flowyml`` imports so it can be copied
verbatim into a serving container as ``serve.py`` and run with only
``fastapi``, ``uvicorn``, ``numpy`` and the model's framework installed.

It loads a bundle produced by :func:`flowyml.deployment.bundle.build_bundle`
(a directory with ``metadata.json`` + ``model/``) and exposes:

* ``GET  /health``   liveness/readiness probe
* ``GET  /metadata`` model name/version/framework/signature/metrics
* ``GET  /metrics``  Prometheus metrics (if ``prometheus_client`` is present)
* ``POST /predict``  run inference
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("flowyml.serving")


# --------------------------------------------------------------------------- #
# Model loading (framework-agnostic, pickle/joblib first)                      #
# --------------------------------------------------------------------------- #
def _find_model_file(model_dir: Path) -> Path:
    """Locate the primary model artifact inside a bundle's ``model/`` dir."""
    if model_dir.is_file():
        return model_dir
    # Directory produced by materializers: prefer a single file named "model"
    candidates = sorted(model_dir.rglob("*"))
    files = [c for c in candidates if c.is_file()]
    if not files:
        return model_dir
    # Prefer well-known names / extensions
    preferred = [
        "model.joblib",
        "model.pkl",
        "model.pickle",
        "model",
        "model.pt",
        "model.pth",
        "model.keras",
        "model.h5",
        "model.onnx",
        "model.cloudpickle",
    ]
    by_name = {f.name: f for f in files}
    for name in preferred:
        if name in by_name:
            return by_name[name]
    for ext in (".joblib", ".pkl", ".pickle", ".pt", ".pth", ".keras", ".h5", ".onnx"):
        for f in files:
            if f.suffix == ext:
                return f
    return files[0]


def load_bundle_model(bundle_dir: str | Path) -> tuple[Any, dict[str, Any]]:
    """Load ``(model, metadata)`` from a bundle directory."""
    bundle_dir = Path(bundle_dir)
    metadata: dict[str, Any] = {}
    meta_file = bundle_dir / "metadata.json"
    if meta_file.exists():
        metadata = json.loads(meta_file.read_text())

    model_dir = bundle_dir / metadata.get("model_subpath", "model")
    if not model_dir.exists():
        model_dir = bundle_dir  # bundle_dir may itself be the model dir

    framework = (metadata.get("framework") or "").lower()

    # TensorFlow SavedModel / directory-based formats load from the directory
    if (model_dir / "saved_model.pb").exists() or framework in ("tensorflow",):
        import tensorflow as tf  # noqa: PLC0415

        return tf.saved_model.load(str(model_dir)), metadata

    model_file = _find_model_file(model_dir)
    errors: list[str] = []

    # Universal fallbacks first
    for loader_name, loader in (("joblib", _load_joblib), ("cloudpickle", _load_cloudpickle), ("pickle", _load_pickle)):
        try:
            return loader(model_file), metadata
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{loader_name}: {exc}")

    # Framework-specific
    try:
        if framework in ("keras",):
            import keras  # noqa: PLC0415

            return keras.models.load_model(str(model_file)), metadata
        if framework in ("pytorch", "torch"):
            import torch  # noqa: PLC0415

            return torch.load(str(model_file), map_location="cpu"), metadata
        if framework == "onnx":
            import onnxruntime as ort  # noqa: PLC0415

            return ort.InferenceSession(str(model_file)), metadata
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{framework}: {exc}")

    raise RuntimeError(f"Failed to load model from {model_file}. Tried: {'; '.join(errors)}")


def _load_joblib(path: Path) -> Any:
    import joblib  # noqa: PLC0415

    return joblib.load(str(path))


def _load_cloudpickle(path: Path) -> Any:
    import cloudpickle  # noqa: PLC0415

    with open(path, "rb") as f:
        return cloudpickle.load(f)


def _load_pickle(path: Path) -> Any:
    import pickle  # noqa: PLC0415

    with open(path, "rb") as f:
        return pickle.load(f)  # noqa: S301


# --------------------------------------------------------------------------- #
# Prediction                                                                   #
# --------------------------------------------------------------------------- #
def _to_array(data: Any):
    import numpy as np  # noqa: PLC0415

    payload = data
    if isinstance(data, dict):
        payload = data.get("inputs", data.get("input", data.get("data", data.get("instances", data))))
    arr = np.asarray(payload, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


def predict_with_model(model: Any, data: Any, framework: str = "") -> dict[str, Any]:
    """Run a prediction and return a JSON-serializable dict."""
    framework = (framework or "").lower()

    # Rule-based / arbitrary callables and objects exposing predict()
    if framework in ("rule_based", "pymc", "bayesian", "custom"):
        if hasattr(model, "predict"):
            out = model.predict(_maybe_records(data))
        elif callable(model):
            out = model(_maybe_records(data))
        else:
            raise RuntimeError("Model is neither callable nor has predict()")
        return {"prediction": _jsonify(out)}

    arr = _to_array(data)

    if framework in ("keras", "tensorflow"):
        out = model.predict(arr) if hasattr(model, "predict") else model(arr)
        return {"prediction": _jsonify(out)}
    if framework in ("pytorch", "torch"):
        import torch  # noqa: PLC0415

        with torch.no_grad():
            out = model(torch.tensor(arr, dtype=torch.float32))
        return {"prediction": _jsonify(out)}
    if framework == "onnx":
        input_name = model.get_inputs()[0].name
        output_name = model.get_outputs()[0].name
        import numpy as np  # noqa: PLC0415

        out = model.run([output_name], {input_name: arr.astype(np.float32)})[0]
        return {"prediction": _jsonify(out)}

    # sklearn / xgboost / lightgbm / generic predict
    if hasattr(model, "predict"):
        result: dict[str, Any] = {"prediction": _jsonify(model.predict(arr))}
        if hasattr(model, "predict_proba"):
            with contextlib.suppress(Exception):
                result["probabilities"] = _jsonify(model.predict_proba(arr))
        return result
    if callable(model):
        return {"prediction": _jsonify(model(arr))}
    raise RuntimeError("Model does not support prediction")


def _maybe_records(data: Any) -> Any:
    if isinstance(data, dict):
        return data.get("inputs", data.get("input", data.get("data", data.get("instances", data))))
    return data


def _jsonify(obj: Any) -> Any:
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "numpy"):
        try:
            return obj.numpy().tolist()
        except Exception:  # noqa: BLE001
            pass
    if isinstance(obj, (list, tuple)):
        return [_jsonify(o) for o in obj]
    return obj


# --------------------------------------------------------------------------- #
# FastAPI app factory                                                          #
# --------------------------------------------------------------------------- #
def create_app(bundle_dir: str | Path | None = None):
    """Create a FastAPI app serving the model bundle at ``bundle_dir``.

    ``bundle_dir`` defaults to the ``MODEL_BUNDLE_DIR`` env var or ``/models``.
    """
    from fastapi import Body, FastAPI, HTTPException  # noqa: PLC0415

    bundle_dir = str(bundle_dir or os.environ.get("MODEL_BUNDLE_DIR", "/models"))
    model, metadata = load_bundle_model(bundle_dir)
    framework = (metadata.get("framework") or "").lower()

    app = FastAPI(
        title=f"FlowyML Serving — {metadata.get('name', 'model')}",
        version=str(metadata.get("version", "0")),
    )

    # Optional Prometheus metrics
    counters: dict[str, Any] = {}
    try:
        from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST  # noqa: PLC0415
        from fastapi.responses import Response  # noqa: PLC0415

        counters["requests"] = Counter("flowyml_predict_requests_total", "Prediction requests")
        counters["errors"] = Counter("flowyml_predict_errors_total", "Prediction errors")
        counters["latency"] = Histogram("flowyml_predict_latency_seconds", "Prediction latency")

        @app.get("/metrics")
        def metrics() -> Any:
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    except Exception:  # noqa: BLE001
        logger.info("prometheus_client not available; /metrics disabled")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "model": metadata.get("name"), "version": metadata.get("version")}

    @app.get("/metadata")
    def get_metadata() -> dict[str, Any]:
        return metadata

    @app.post("/predict")
    def do_predict(payload: Any = Body(default=None)) -> dict[str, Any]:
        if counters:
            counters["requests"].inc()
        start = time.time()
        try:
            result = predict_with_model(model, payload if payload is not None else {}, framework)
            result["latency_ms"] = (time.time() - start) * 1000
            result["model"] = metadata.get("name")
            result["version"] = metadata.get("version")
            if counters:
                counters["latency"].observe(time.time() - start)
            return result
        except Exception as exc:  # noqa: BLE001
            if counters:
                counters["errors"].inc()
            logger.exception("Prediction failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


if __name__ == "__main__":  # pragma: no cover - container entrypoint
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)  # noqa: S104

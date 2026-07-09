"""Batch (offline) inference.

Loads a versioned model from the registry (same transparent packaging path as
online serving) and scores a dataset in batches.  Works standalone, inside a
FlowyML ``@step`` for scheduled batch jobs, or on any remote stack (the step
runs wherever the pipeline runs — e.g. Azure ML compute).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from collections.abc import Iterable

from flowyml.deployment.bundle import build_bundle
from flowyml.deployment.models import ModelRef

logger = logging.getLogger(__name__)


@dataclass
class BatchInferenceResult:
    """Summary of a batch inference run."""

    model_name: str
    model_version: str
    num_rows: int
    predictions: list[Any] = field(default_factory=list)
    output_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = self.__dict__.copy()
        # Avoid dumping potentially huge prediction arrays into summaries
        data["predictions"] = f"<{len(self.predictions)} predictions>"
        return data


def _iter_batches(rows: list[Any], batch_size: int) -> Iterable[list[Any]]:
    for i in range(0, len(rows), batch_size):
        yield rows[i : i + batch_size]


def _load_input(data: Any) -> list[Any]:
    """Normalize input into a list of rows.

    Accepts: a list, a numpy array, a pandas DataFrame, or a path to a
    ``.csv``/``.parquet``/``.json`` file.
    """
    if isinstance(data, (str, Path)):
        path = Path(data)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            import pandas as pd

            return pd.read_csv(path).to_numpy().tolist()
        if suffix == ".parquet":
            import pandas as pd

            return pd.read_parquet(path).to_numpy().tolist()
        if suffix == ".json":
            return json.loads(path.read_text())
        raise ValueError(f"Unsupported input file type: {suffix}")
    if hasattr(data, "values") and hasattr(data, "columns"):  # DataFrame
        return data.to_numpy().tolist()
    if hasattr(data, "tolist"):  # numpy array
        return data.tolist()
    if isinstance(data, list):
        return data
    raise TypeError(f"Unsupported batch input type: {type(data)}")


def run_batch_inference(
    model: str | ModelRef,
    data: Any,
    *,
    output_path: str | Path | None = None,
    batch_size: int = 1000,
    registry: Any = None,
    version: str | None = None,
    stage: str | None = None,
) -> BatchInferenceResult:
    """Score ``data`` with a registered model and optionally write predictions.

    Args:
        model: Model name or :class:`ModelRef`.
        data: Input rows (list/ndarray/DataFrame) or a path to csv/parquet/json.
        output_path: If given, predictions are written here (``.json`` or ``.csv``).
        batch_size: Rows per prediction call.
        registry: Optional registry object.
        version: Explicit version (when ``model`` is a name).
        stage: Stage to resolve version from (when ``model`` is a name).

    Returns:
        A :class:`BatchInferenceResult`.
    """
    from flowyml.deployment.serving_app import load_bundle_model, predict_with_model

    model_ref = model if isinstance(model, ModelRef) else ModelRef(name=model, version=version, stage=stage)
    bundle = build_bundle(model_ref, registry=registry)
    loaded, metadata = load_bundle_model(bundle.path)
    framework = (metadata.get("framework") or "").lower()

    rows = _load_input(data)
    predictions: list[Any] = []
    for batch in _iter_batches(rows, batch_size):
        out = predict_with_model(loaded, {"inputs": batch}, framework)
        preds = out.get("prediction", out)
        if isinstance(preds, list):
            predictions.extend(preds)
        else:
            predictions.append(preds)

    logger.info("Batch inference: scored %d rows with %s:%s", len(rows), bundle.name, bundle.version)

    written = None
    if output_path is not None:
        written = _write_output(predictions, output_path)

    return BatchInferenceResult(
        model_name=bundle.name,
        model_version=bundle.version,
        num_rows=len(rows),
        predictions=predictions,
        output_path=written,
    )


def _write_output(predictions: list[Any], output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        import csv

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["prediction"])
            for pred in predictions:
                writer.writerow([pred])
    else:
        path.write_text(json.dumps(predictions, indent=2, default=str))
    return str(path)


class BatchInferenceJob:
    """Reusable batch inference job (handy as a configured pipeline component)."""

    def __init__(
        self,
        model: str | ModelRef,
        *,
        batch_size: int = 1000,
        registry: Any = None,
        version: str | None = None,
        stage: str | None = None,
    ) -> None:
        self.model = model
        self.batch_size = batch_size
        self.registry = registry
        self.version = version
        self.stage = stage

    def run(self, data: Any, output_path: str | Path | None = None) -> BatchInferenceResult:
        return run_batch_inference(
            self.model,
            data,
            output_path=output_path,
            batch_size=self.batch_size,
            registry=self.registry,
            version=self.version,
            stage=self.stage,
        )

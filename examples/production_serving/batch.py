"""Batch (offline) inference for the production serving tutorial.

Score a batch of rows with a registered model — no server required. This uses
the *same* transparent packaging path as online serving (``build_bundle`` +
the FastAPI runtime's loader), so batch and online predictions are identical.

Usage::

    # 1) train + register candidates
    python pipelines/training.py

    # 2) promote a winner to production
    python deploy.py risk-bayesian <version>

    # 3a) batch-score the current *production* model
    python batch.py risk-bayesian

    # 3b) or batch-score a specific version (no promotion needed)
    python batch.py risk-bayesian <version>

Predictions are written to ``./.flowyml/batch_predictions.json``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# Model flavors must be importable so the pickled models reload here, exactly
# as they would inside a serving container.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import models  # noqa: E402,F401  (import registers RiskRules / predict fns)

from flowyml.deployment import run_batch_inference  # noqa: E402


def main(model_name: str, version: str | None = None) -> None:
    """Batch-score a small synthetic dataset with the requested model."""
    rng = np.random.default_rng(7)
    features = rng.random((8, 3))

    output_path = Path(__file__).resolve().parent / ".flowyml" / "batch_predictions.json"

    # With an explicit version we score that version; otherwise we resolve the
    # current 'production' champion (set by deploy.py's promotion gate).
    stage = None if version else "production"
    try:
        result = run_batch_inference(
            model_name,
            features,
            version=version,
            stage=stage,
            output_path=str(output_path),
            batch_size=4,
        )
    except ValueError as exc:
        print(f"⚠️  Could not resolve model to score: {exc}")
        print("    Train + register first:   python pipelines/training.py")
        print("    Then either promote it:    python deploy.py risk-bayesian <version>")
        print("    or pass a version:         python batch.py risk-bayesian <version>")
        raise SystemExit(1) from exc

    print(f"Scored {result.num_rows} rows with {result.model_name}:{result.model_version}")
    for row, pred in zip(features.tolist(), result.predictions, strict=False):
        print(f"  {[round(v, 2) for v in row]} -> {pred}")
    print(f"\nPredictions written to: {result.output_path}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("usage: python batch.py <model_name> [version]")
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)

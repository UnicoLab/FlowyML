"""Training pipeline: train candidate models, register them with lineage.

Run locally:
    flowyml run training                 # uses the 'local' stack
Run on Azure ML:
    flowyml run training --stack azureml-openshift

Exposes ``create_pipeline()`` so the FlowyML CLI can discover it.
"""

from __future__ import annotations

import time

import numpy as np

from flowyml import Pipeline, step
from flowyml.assets import Dataset, Model
from flowyml.registry.model_registry import ModelRegistry, ModelStage

# Import model flavors from an importable module (required for serving).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models import RiskRules, make_bayesian_model  # noqa: E402


def _synthetic(n: int = 500, seed: int = 0):
    rng = np.random.default_rng(seed)
    X = rng.random((n, 3))
    y = ((X[:, 0] + X[:, 1] * 1.5 - X[:, 2]) > 1.0).astype(int)
    return X, y


@step(outputs=["dataset"])
def load_data() -> dict:
    """Create the training dataset as a first-class, lineage-tracked asset."""
    X, y = _synthetic()
    ds = Dataset.create(data={"X": X, "y": y}, name="risk-training-data", version="1")
    return {"X": X.tolist(), "y": y.tolist(), "asset_id": ds.metadata.asset_id}


@step(inputs=["dataset"], outputs=["candidates"])
def train_and_register(dataset: dict) -> dict:
    """Train rule-based + Bayesian models, register both with metrics & lineage."""
    X = np.asarray(dataset["X"])
    y = np.asarray(dataset["y"])
    registry = ModelRegistry()
    version = f"v{int(time.time())}"
    parent = Dataset.create(data={"X": X, "y": y}, name="risk-training-data", version="1")

    candidates: dict[str, str] = {}

    # 1) Rule-based baseline
    rules = RiskRules(cutoff=0.5)
    acc_rules = float((np.asarray(rules.predict(X)) == y).mean())
    Model.create(data=rules, name="risk-rules", trained_on=parent)  # lineage
    registry.register(
        rules,
        name="risk-rules",
        version=version,
        framework="rule_based",
        metrics={"accuracy": acc_rules},
        stage=ModelStage.DEVELOPMENT,
        description="Hand-written risk rules",
    )
    candidates["risk-rules"] = version

    # 2) Bayesian logistic model (fitted coefficients stand in for a PyMC posterior)
    beta = np.array([1.0, 1.5, -1.0])
    bayes = make_bayesian_model(beta=beta, intercept=-1.0)
    acc_bayes = float((np.asarray(bayes.predict(X)) == y).mean())
    Model.create(data=bayes, name="risk-bayesian", trained_on=parent)  # lineage
    registry.register(
        bayes,
        name="risk-bayesian",
        version=version,
        framework="bayesian",
        metrics={"accuracy": acc_bayes},
        stage=ModelStage.DEVELOPMENT,
        description="Bayesian logistic risk model",
    )
    candidates["risk-bayesian"] = version

    return {"candidates": candidates, "metrics": {"risk-rules": acc_rules, "risk-bayesian": acc_bayes}}


def create_pipeline() -> Pipeline:
    p = Pipeline("training")
    p.add_step(load_data).add_step(train_and_register)
    return p


if __name__ == "__main__":
    result = create_pipeline().run()
    candidates = result.outputs["candidates"]["candidates"]
    metrics = result.outputs["candidates"]["metrics"]
    print("\nTraining complete. Registered candidates:")
    for name, ver in candidates.items():
        print(f"  {name}  version={ver}  accuracy={metrics[name]:.3f}")
    print("\nNext step — promote the winner and deploy it, e.g.:")
    for name, ver in candidates.items():
        print(f"  python deploy.py {name} {ver}")

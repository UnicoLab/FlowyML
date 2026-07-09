"""Model flavors used by the production serving tutorial.

These live in an importable module (not a notebook / __main__) so that the
pickled models can be *loaded back* inside a serving container.
"""

from __future__ import annotations

import numpy as np

from flowyml.models import BayesianPredictor, RuleBasedModel


class RiskRules(RuleBasedModel):
    """A hand-written, explainable baseline: flag high-risk rows."""

    def predict(self, X):
        arr = np.asarray(X, dtype=float)
        # rule: risky if feature-0 high AND feature-1 above the configured cutoff
        cutoff = self.params.get("cutoff", 0.5)
        return [(1 if (row[0] > 0.8 and row[1] > cutoff) else 0) for row in arr]


def posterior_mean_predict(idata, X):
    """Module-level predict fn for a Bayesian logistic-style model.

    Must be importable so ``BayesianPredictor`` unpickles in a container.
    """
    X = np.asarray(X, dtype=float)
    # idata here is a lightweight dict of posterior means for the tutorial;
    # with real PyMC this would be an ArviZ InferenceData.
    beta = np.asarray(idata["beta"], dtype=float)
    intercept = float(idata["intercept"])
    logits = X @ beta + intercept
    probs = 1.0 / (1.0 + np.exp(-logits))
    return (probs > 0.5).astype(int)


def make_bayesian_model(beta, intercept) -> BayesianPredictor:
    return BayesianPredictor(
        idata={"beta": list(beta), "intercept": float(intercept)},
        predict_fn=posterior_mean_predict,
        metadata={"kind": "bayesian-logistic"},
    )

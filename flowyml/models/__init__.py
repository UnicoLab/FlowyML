"""First-class model *flavors* for non-standard frameworks.

FlowyML routes/serves models by a ``framework`` string. Deep-learning and
sklearn models are auto-detected, but *rule-based* and *Bayesian/PyMC* models
need a small, portable, picklable wrapper so they package and serve identically
to any other model.  These helpers provide exactly that:

* :class:`RuleBasedModel` — subclass and implement ``predict`` for hand-written
  business rules / heuristics.
* :class:`BayesianPredictor` — wrap a fitted PyMC/ArviZ posterior plus a pure
  ``predict_fn`` into a servable object.

Both expose a scikit-learn-style ``predict(X)`` and are serialized with
cloudpickle by the registry, then served through the FastAPI runtime.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

FRAMEWORK_RULE_BASED = "rule_based"
FRAMEWORK_BAYESIAN = "bayesian"


class RuleBasedModel:
    """Base class for hand-written / heuristic models.

    Subclass and implement :meth:`predict`.  Instances are picklable and expose
    the ``framework = "rule_based"`` attribute so the registry and deployment
    layer treat them as first-class models.

    Example:
        >>> class HighRisk(RuleBasedModel):
        ...     def predict(self, X):
        ...         return [1 if row[0] > 0.8 else 0 for row in X]
    """

    framework: str = FRAMEWORK_RULE_BASED

    def __init__(self, **params: Any) -> None:
        self.params = params

    def predict(self, X: Any) -> Any:  # noqa: D401, N803 - to be overridden
        raise NotImplementedError("RuleBasedModel subclasses must implement predict()")

    def __call__(self, X: Any) -> Any:  # noqa: N803
        return self.predict(X)

    def get_params(self) -> dict[str, Any]:
        return dict(self.params)


class BayesianPredictor:
    """Servable wrapper around a fitted Bayesian posterior.

    Args:
        idata: An ArviZ ``InferenceData`` (or any picklable posterior object).
        predict_fn: A **module-level** callable ``predict_fn(idata, X) -> array``
            that computes point predictions (e.g. posterior-predictive mean).
            It must be importable (not a lambda/closure) so the model unpickles
            inside a serving container.
        metadata: Optional metadata (e.g. model coordinates, feature names).

    Example:
        >>> def predict_mean(idata, X):
        ...     beta = idata.posterior["beta"].mean(("chain", "draw")).values
        ...     return X @ beta
        >>> model = BayesianPredictor(idata, predict_mean)
    """

    framework: str = FRAMEWORK_BAYESIAN

    def __init__(
        self,
        idata: Any,
        predict_fn: Callable[[Any, Any], Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.idata = idata
        self.predict_fn = predict_fn
        self.metadata = metadata or {}

    def predict(self, X: Any) -> Any:  # noqa: N803
        result = self.predict_fn(self.idata, X)
        return result.tolist() if hasattr(result, "tolist") else result

    def __call__(self, X: Any) -> Any:  # noqa: N803
        return self.predict(X)


__all__ = [
    "RuleBasedModel",
    "BayesianPredictor",
    "FRAMEWORK_RULE_BASED",
    "FRAMEWORK_BAYESIAN",
]

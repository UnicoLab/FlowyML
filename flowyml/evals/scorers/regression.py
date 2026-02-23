"""FlowyML Evaluations — Regression Scorers.

Production-ready regression metrics for classical ML evaluation.
Uses scikit-learn when available, falls back to pure-Python (numpy) implementations.
"""

import logging
from typing import Any

import numpy as np

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType

logger = logging.getLogger(__name__)


def _try_sklearn_metric(metric_name: str):
    """Try to import a sklearn metric, return None if unavailable."""
    try:
        from sklearn import metrics

        return getattr(metrics, metric_name, None)
    except ImportError:
        return None


class MSE(Scorer):
    """Mean Squared Error scorer.

    Example:
        >>> scorer = MSE()
        >>> scorer.score(predictions=[2.5, 3.0, 4.5], targets=[3.0, 3.0, 5.0])
        ScorerFeedback(name="mse", value=0.166667)
    """

    name = "mse"
    scorer_type = ScorerType.REGRESSION
    description = "Mean Squared Error"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("MSE requires 'predictions' and 'targets'")

        preds = np.array(predictions, dtype=float)
        tgts = np.array(targets, dtype=float)

        sklearn_fn = _try_sklearn_metric("mean_squared_error")
        if sklearn_fn:
            value = float(sklearn_fn(tgts, preds))
        else:
            value = float(np.mean((preds - tgts) ** 2))

        passed = None
        if self.threshold is not None:
            passed = value <= self.threshold  # Lower is better

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=passed,
            metadata={"n_samples": len(tgts), "lower_is_better": True},
        )


class RMSE(Scorer):
    """Root Mean Squared Error scorer.

    Example:
        >>> scorer = RMSE()
        >>> scorer.score(predictions=[2.5, 3.0, 4.5], targets=[3.0, 3.0, 5.0])
    """

    name = "rmse"
    scorer_type = ScorerType.REGRESSION
    description = "Root Mean Squared Error"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("RMSE requires 'predictions' and 'targets'")

        preds = np.array(predictions, dtype=float)
        tgts = np.array(targets, dtype=float)

        value = float(np.sqrt(np.mean((preds - tgts) ** 2)))

        passed = None
        if self.threshold is not None:
            passed = value <= self.threshold

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=passed,
            metadata={"n_samples": len(tgts), "lower_is_better": True},
        )


class MAE(Scorer):
    """Mean Absolute Error scorer.

    Example:
        >>> scorer = MAE()
        >>> scorer.score(predictions=[2.5, 3.0, 4.5], targets=[3.0, 3.0, 5.0])
    """

    name = "mae"
    scorer_type = ScorerType.REGRESSION
    description = "Mean Absolute Error"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("MAE requires 'predictions' and 'targets'")

        preds = np.array(predictions, dtype=float)
        tgts = np.array(targets, dtype=float)

        sklearn_fn = _try_sklearn_metric("mean_absolute_error")
        if sklearn_fn:
            value = float(sklearn_fn(tgts, preds))
        else:
            value = float(np.mean(np.abs(preds - tgts)))

        passed = None
        if self.threshold is not None:
            passed = value <= self.threshold

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=passed,
            metadata={"n_samples": len(tgts), "lower_is_better": True},
        )


class R2Score(Scorer):
    """R² (coefficient of determination) scorer.

    Example:
        >>> scorer = R2Score()
        >>> scorer.score(predictions=[2.5, 3.0, 4.5], targets=[3.0, 3.0, 5.0])
    """

    name = "r2_score"
    scorer_type = ScorerType.REGRESSION
    description = "R² (coefficient of determination)"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("R2Score requires 'predictions' and 'targets'")

        preds = np.array(predictions, dtype=float)
        tgts = np.array(targets, dtype=float)

        sklearn_fn = _try_sklearn_metric("r2_score")
        if sklearn_fn:
            value = float(sklearn_fn(tgts, preds))
        else:
            ss_res = np.sum((tgts - preds) ** 2)
            ss_tot = np.sum((tgts - np.mean(tgts)) ** 2)
            value = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=value >= self.threshold if self.threshold is not None else None,
            metadata={"n_samples": len(tgts)},
        )


class MAPE(Scorer):
    """Mean Absolute Percentage Error scorer.

    Example:
        >>> scorer = MAPE()
        >>> scorer.score(predictions=[105, 200, 300], targets=[100, 200, 300])
    """

    name = "mape"
    scorer_type = ScorerType.REGRESSION
    description = "Mean Absolute Percentage Error"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("MAPE requires 'predictions' and 'targets'")

        preds = np.array(predictions, dtype=float)
        tgts = np.array(targets, dtype=float)

        # Avoid division by zero
        mask = tgts != 0
        if not np.any(mask):
            return ScorerFeedback(
                name=self.name,
                value=0.0,
                scorer_type=self.scorer_type.value,
                rationale="All targets are zero",
                passed=False,
            )

        value = float(np.mean(np.abs((tgts[mask] - preds[mask]) / tgts[mask]))) * 100

        passed = None
        if self.threshold is not None:
            passed = value <= self.threshold

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=passed,
            metadata={"n_samples": len(tgts), "lower_is_better": True, "unit": "percent"},
        )


class MaxError(Scorer):
    """Maximum error scorer — worst-case prediction error.

    Example:
        >>> scorer = MaxError()
        >>> scorer.score(predictions=[2.5, 3.0, 4.5], targets=[3.0, 3.0, 5.0])
    """

    name = "max_error"
    scorer_type = ScorerType.REGRESSION
    description = "Maximum absolute error (worst case)"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("MaxError requires 'predictions' and 'targets'")

        preds = np.array(predictions, dtype=float)
        tgts = np.array(targets, dtype=float)

        sklearn_fn = _try_sklearn_metric("max_error")
        if sklearn_fn:
            value = float(sklearn_fn(tgts, preds))
        else:
            value = float(np.max(np.abs(preds - tgts)))

        passed = None
        if self.threshold is not None:
            passed = value <= self.threshold

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=passed,
            metadata={"n_samples": len(tgts), "lower_is_better": True},
        )


# Convenience list of all regression scorers
REGRESSION_SCORERS = {
    "mse": MSE,
    "rmse": RMSE,
    "mae": MAE,
    "r2_score": R2Score,
    "mape": MAPE,
    "max_error": MaxError,
}

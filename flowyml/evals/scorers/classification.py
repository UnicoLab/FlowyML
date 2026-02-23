"""FlowyML Evaluations — Classification Scorers.

Production-ready classification metrics for classical ML evaluation.
Uses scikit-learn when available, falls back to pure-Python implementations.
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


class Accuracy(Scorer):
    """Classification accuracy scorer.

    Computes the fraction of predictions that match the targets.

    Example:
        >>> scorer = Accuracy()
        >>> scorer.score(predictions=[1, 0, 1, 1], targets=[1, 0, 0, 1])
        ScorerFeedback(name="accuracy", value=0.75)
    """

    name = "accuracy"
    scorer_type = ScorerType.CLASSIFICATION
    description = "Fraction of correctly classified examples"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("Accuracy requires 'predictions' and 'targets'")

        preds = list(predictions)
        tgts = list(targets)
        if len(preds) != len(tgts):
            raise ValueError(
                f"Length mismatch: predictions={len(preds)}, targets={len(tgts)}",
            )
        if len(preds) == 0:
            raise ValueError("Cannot compute accuracy on empty data")

        sklearn_fn = _try_sklearn_metric("accuracy_score")
        if sklearn_fn:
            value = float(sklearn_fn(tgts, preds))
        else:
            correct = sum(p == t for p, t in zip(preds, tgts, strict=False))
            value = correct / len(tgts)

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=value >= self.threshold if self.threshold is not None else None,
            metadata={"n_samples": len(tgts)},
        )


class Precision(Scorer):
    """Precision scorer for classification.

    Supports binary, macro, micro, and weighted averaging.

    Args:
        average: Averaging method — 'binary', 'macro', 'micro', 'weighted'
        pos_label: Positive class label for binary averaging

    Example:
        >>> scorer = Precision(average="macro")
        >>> scorer.score(predictions=[1, 0, 1, 1], targets=[1, 0, 0, 1])
    """

    name = "precision"
    scorer_type = ScorerType.CLASSIFICATION
    description = "Precision (positive predictive value)"

    def __init__(
        self,
        average: str = "binary",
        pos_label: int = 1,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.average = average
        self.pos_label = pos_label

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("Precision requires 'predictions' and 'targets'")

        preds = list(predictions)
        tgts = list(targets)

        sklearn_fn = _try_sklearn_metric("precision_score")
        if sklearn_fn:
            value = float(
                sklearn_fn(tgts, preds, average=self.average, pos_label=self.pos_label, zero_division=0),
            )
        else:
            # Pure-Python binary precision
            tp = sum(p == self.pos_label and t == self.pos_label for p, t in zip(preds, tgts, strict=False))
            fp = sum(p == self.pos_label and t != self.pos_label for p, t in zip(preds, tgts, strict=False))
            value = tp / (tp + fp) if (tp + fp) > 0 else 0.0

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=value >= self.threshold if self.threshold is not None else None,
            metadata={"average": self.average, "n_samples": len(tgts)},
        )


class Recall(Scorer):
    """Recall (sensitivity) scorer for classification.

    Args:
        average: Averaging method — 'binary', 'macro', 'micro', 'weighted'
        pos_label: Positive class label for binary averaging

    Example:
        >>> scorer = Recall(average="macro")
        >>> scorer.score(predictions=[1, 0, 1, 1], targets=[1, 0, 0, 1])
    """

    name = "recall"
    scorer_type = ScorerType.CLASSIFICATION
    description = "Recall (sensitivity, true positive rate)"

    def __init__(
        self,
        average: str = "binary",
        pos_label: int = 1,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.average = average
        self.pos_label = pos_label

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("Recall requires 'predictions' and 'targets'")

        preds = list(predictions)
        tgts = list(targets)

        sklearn_fn = _try_sklearn_metric("recall_score")
        if sklearn_fn:
            value = float(
                sklearn_fn(tgts, preds, average=self.average, pos_label=self.pos_label, zero_division=0),
            )
        else:
            tp = sum(p == self.pos_label and t == self.pos_label for p, t in zip(preds, tgts, strict=False))
            fn = sum(p != self.pos_label and t == self.pos_label for p, t in zip(preds, tgts, strict=False))
            value = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=value >= self.threshold if self.threshold is not None else None,
            metadata={"average": self.average, "n_samples": len(tgts)},
        )


class F1Score(Scorer):
    """F1 Score (harmonic mean of precision and recall).

    Args:
        average: Averaging method — 'binary', 'macro', 'micro', 'weighted'
        pos_label: Positive class label for binary averaging

    Example:
        >>> scorer = F1Score(average="weighted")
        >>> scorer.score(predictions=[1, 0, 1, 1], targets=[1, 0, 0, 1])
    """

    name = "f1_score"
    scorer_type = ScorerType.CLASSIFICATION
    description = "F1 Score (harmonic mean of precision and recall)"

    def __init__(
        self,
        average: str = "binary",
        pos_label: int = 1,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.average = average
        self.pos_label = pos_label

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("F1Score requires 'predictions' and 'targets'")

        preds = list(predictions)
        tgts = list(targets)

        sklearn_fn = _try_sklearn_metric("f1_score")
        if sklearn_fn:
            value = float(
                sklearn_fn(tgts, preds, average=self.average, pos_label=self.pos_label, zero_division=0),
            )
        else:
            # Pure-Python binary F1
            tp = sum(p == self.pos_label and t == self.pos_label for p, t in zip(preds, tgts, strict=False))
            fp = sum(p == self.pos_label and t != self.pos_label for p, t in zip(preds, tgts, strict=False))
            fn = sum(p != self.pos_label and t == self.pos_label for p, t in zip(preds, tgts, strict=False))
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            value = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=value >= self.threshold if self.threshold is not None else None,
            metadata={"average": self.average, "n_samples": len(tgts)},
        )


class AUCROC(Scorer):
    """Area Under the ROC Curve scorer.

    Requires probability predictions (not class labels).

    Example:
        >>> scorer = AUCROC()
        >>> scorer.score(predictions=[0.9, 0.3, 0.8, 0.1], targets=[1, 0, 1, 0])
    """

    name = "auc_roc"
    scorer_type = ScorerType.CLASSIFICATION
    description = "Area Under the ROC Curve"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("AUCROC requires 'predictions' (probabilities) and 'targets'")

        preds = np.array(predictions, dtype=float)
        tgts = np.array(targets, dtype=float)

        sklearn_fn = _try_sklearn_metric("roc_auc_score")
        if sklearn_fn:
            try:
                value = float(sklearn_fn(tgts, preds))
            except ValueError as e:
                return ScorerFeedback(
                    name=self.name,
                    value=0.0,
                    scorer_type=self.scorer_type.value,
                    rationale=f"Cannot compute AUC-ROC: {e}",
                    passed=False,
                )
        else:
            # Pure-Python AUC-ROC (trapezoidal)
            sorted_indices = np.argsort(-preds)
            sorted_tgts = tgts[sorted_indices]
            n_pos = np.sum(tgts == 1)
            n_neg = np.sum(tgts == 0)
            if n_pos == 0 or n_neg == 0:
                return ScorerFeedback(
                    name=self.name,
                    value=0.0,
                    scorer_type=self.scorer_type.value,
                    rationale="Only one class present in targets",
                    passed=False,
                )
            tp = 0
            fp = 0
            auc = 0.0
            for t in sorted_tgts:
                if t == 1:
                    tp += 1
                else:
                    fp += 1
                    auc += tp
            value = auc / (n_pos * n_neg)

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            passed=value >= self.threshold if self.threshold is not None else None,
            metadata={"n_samples": len(tgts)},
        )


class ConfusionMatrixScorer(Scorer):
    """Confusion matrix scorer.

    Returns the confusion matrix as a dictionary in the metadata.

    Example:
        >>> scorer = ConfusionMatrixScorer()
        >>> result = scorer.score(predictions=[1, 0, 1, 0], targets=[1, 0, 0, 0])
        >>> result.metadata["matrix"]
    """

    name = "confusion_matrix"
    scorer_type = ScorerType.CLASSIFICATION
    description = "Confusion matrix"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("ConfusionMatrix requires 'predictions' and 'targets'")

        preds = list(predictions)
        tgts = list(targets)

        labels = sorted(set(tgts) | set(preds))
        label_to_idx = {label: i for i, label in enumerate(labels)}
        n = len(labels)
        matrix = [[0] * n for _ in range(n)]

        for t, p in zip(tgts, preds, strict=False):
            matrix[label_to_idx[t]][label_to_idx[p]] += 1

        # Compute overall accuracy as the value
        correct = sum(matrix[i][i] for i in range(n))
        total = len(tgts)
        value = correct / total if total > 0 else 0.0

        return ScorerFeedback(
            name=self.name,
            value=round(value, 6),
            scorer_type=self.scorer_type.value,
            metadata={
                "matrix": matrix,
                "labels": [str(label) for label in labels],
                "n_samples": total,
            },
        )


class LogLoss(Scorer):
    """Logarithmic loss (cross-entropy loss) scorer.

    Requires probability predictions.

    Example:
        >>> scorer = LogLoss()
        >>> scorer.score(predictions=[0.9, 0.1, 0.8], targets=[1, 0, 1])
    """

    name = "log_loss"
    scorer_type = ScorerType.CLASSIFICATION
    description = "Logarithmic loss (cross-entropy)"

    def score(
        self,
        *,
        predictions: Any = None,
        targets: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if predictions is None or targets is None:
            raise ValueError("LogLoss requires 'predictions' (probabilities) and 'targets'")

        preds = np.array(predictions, dtype=float)
        tgts = np.array(targets, dtype=float)

        sklearn_fn = _try_sklearn_metric("log_loss")
        if sklearn_fn:
            value = float(sklearn_fn(tgts, preds))
        else:
            # Pure-Python log loss
            eps = 1e-15
            preds_clipped = np.clip(preds, eps, 1 - eps)
            value = float(
                -np.mean(tgts * np.log(preds_clipped) + (1 - tgts) * np.log(1 - preds_clipped)),
            )

        # For log loss, lower is better — invert threshold logic
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


# Convenience list of all classification scorers
CLASSIFICATION_SCORERS = {
    "accuracy": Accuracy,
    "precision": Precision,
    "recall": Recall,
    "f1_score": F1Score,
    "auc_roc": AUCROC,
    "confusion_matrix": ConfusionMatrixScorer,
    "log_loss": LogLoss,
}

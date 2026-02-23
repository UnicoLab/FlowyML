"""FlowyML Evaluations — Core Evaluate Function and EvalResult.

The main entry point for running evaluations. Orchestrates scoring,
aggregation, regression detection, and integration with experiment tracking.
"""

import logging
from dataclasses import dataclass, field  # noqa: F811
from datetime import datetime
from typing import Any
from uuid import uuid4

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType
from flowyml.evals.dataset import EvalDataset

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Aggregated result from an evaluation run.

    Contains per-example scores from each scorer, aggregate summaries,
    and methods for regression detection and conversion to Metrics assets.

    Attributes:
        eval_id: Unique evaluation identifier
        experiment: Optional experiment name
        scores: Per-scorer detailed feedback {scorer_name: [ScorerFeedback, ...]}
        summary: Per-scorer aggregate score {scorer_name: float}
        dataset_name: Name of the evaluated dataset
        dataset_version: Version of the evaluated dataset
        created_at: Timestamp
        metadata: Additional metadata
        scorer_configs: Configuration of scorers used

    Example:
        >>> result = evaluate(data=eval_ds, scorers=[Accuracy(), F1Score()])
        >>> result.summary
        {"accuracy": 0.95, "f1_score": 0.92}
        >>> result.to_metrics()
        Metrics(name="eval_...", data={"accuracy": 0.95, "f1_score": 0.92})
    """

    eval_id: str = field(default_factory=lambda: str(uuid4()))
    experiment: str | None = None
    scores: dict[str, list[ScorerFeedback]] = field(default_factory=dict)
    summary: dict[str, float] = field(default_factory=dict)
    dataset_name: str | None = None
    dataset_version: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    scorer_configs: list[dict] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Whether all scorers with thresholds passed."""
        for feedbacks in self.scores.values():
            for fb in feedbacks:
                if fb.passed is False:
                    return False
        return True

    @property
    def pass_rate(self) -> float:
        """Fraction of examples that passed (across all scorers with thresholds)."""
        total = 0
        passed = 0
        for feedbacks in self.scores.values():
            for fb in feedbacks:
                if fb.passed is not None:
                    total += 1
                    if fb.passed:
                        passed += 1
        return passed / total if total > 0 else 1.0

    @property
    def scorer_names(self) -> list[str]:
        """Names of all scorers used."""
        return list(self.scores.keys())

    def get_scores(self, scorer_name: str) -> list[ScorerFeedback]:
        """Get detailed scores for a specific scorer."""
        return self.scores.get(scorer_name, [])

    def to_metrics(self) -> "Metrics":  # noqa: F821
        """Convert evaluation result to a FlowyML Metrics asset.

        Returns:
            Metrics asset with evaluation scores as metric values
        """
        from flowyml.assets.metrics import Metrics

        metrics_data = dict(self.summary)
        metrics_data["eval_pass_rate"] = self.pass_rate

        return Metrics.create(
            name=f"eval_{self.eval_id[:8]}",
            metrics=metrics_data,
            metadata={
                "eval_id": self.eval_id,
                "dataset": self.dataset_name or "unknown",
                "dataset_version": self.dataset_version or "unknown",
                "experiment": self.experiment or "",
            },
        )

    def regressions_from(
        self,
        baseline: "EvalResult",
        threshold: float = 0.05,
    ) -> dict[str, dict[str, Any]]:
        """Detect regressions compared to a baseline evaluation.

        A regression is detected when a metric drops by more than `threshold`
        compared to the baseline. For "lower-is-better" metrics, a regression
        is when the metric increases by more than the threshold.

        Args:
            baseline: Baseline EvalResult to compare against
            threshold: Minimum change to flag as regression (default: 5%)

        Returns:
            Dict of regressions: {scorer_name: {baseline, current, delta, regressed}}

        Example:
            >>> regressions = result.regressions_from(baseline_result, threshold=0.05)
            >>> if regressions:
            ...     print("⚠️ Regressions detected:", regressions)
        """
        regressions = {}

        for scorer_name, current_value in self.summary.items():
            baseline_value = baseline.summary.get(scorer_name)
            if baseline_value is None:
                continue

            if not isinstance(current_value, (int, float)) or not isinstance(
                baseline_value,
                (int, float),
            ):
                continue

            delta = current_value - baseline_value

            # Check if this is a "lower is better" metric
            lower_is_better = False
            feedbacks = self.scores.get(scorer_name, [])
            if feedbacks:
                lower_is_better = feedbacks[0].metadata.get("lower_is_better", False)

            if lower_is_better:
                regressed = delta > threshold  # Got worse (increased)
            else:
                regressed = delta < -threshold  # Got worse (decreased)

            regressions[scorer_name] = {
                "baseline": baseline_value,
                "current": current_value,
                "delta": round(delta, 6),
                "regressed": regressed,
                "lower_is_better": lower_is_better,
            }

        return {k: v for k, v in regressions.items() if v["regressed"]}

    def notify_if_regression(
        self,
        baseline: "EvalResult",
        threshold: float = 0.05,
        channel: str | None = None,
    ) -> bool:
        """Send a notification if regressions are detected vs a baseline.

        Integrates with FlowyML's NotificationManager to send alerts via
        Slack, email, or console when evaluation quality drops.

        Args:
            baseline: Baseline EvalResult to compare against
            threshold: Minimum drop to flag as regression
            channel: Notification channel ('slack', 'email', 'console', or None for all)

        Returns:
            True if regressions were found and notifications sent
        """
        regressions = self.regressions_from(baseline, threshold=threshold)
        if not regressions:
            return False

        # Build message
        lines = [f"⚠️ Evaluation regression detected in '{self.experiment or 'unknown'}':"]
        for metric, info in regressions.items():
            lines.append(
                f"  - {metric}: {info['baseline']:.4f} → {info['current']:.4f} " f"(Δ{info['delta']:.4f})",
            )

        message = "\n".join(lines)
        title = f"Eval Regression: {self.experiment or self.eval_id[:8]}"

        try:
            from flowyml.monitoring.notifications import get_notifier

            notifier = get_notifier()
            if channel:
                notifier.notify(title=title, message=message, level="warning", channel=channel)
            else:
                notifier.notify(title=title, message=message, level="warning")
        except (ImportError, Exception) as exc:
            logger.warning("Could not send regression notification: %s", exc)
            logger.warning(message)

        return True

    def to_dict(self) -> dict[str, Any]:
        """Full serialization for storage."""
        return {
            "eval_id": self.eval_id,
            "experiment": self.experiment,
            "scores": {name: [fb.to_dict() for fb in feedbacks] for name, feedbacks in self.scores.items()},
            "summary": self.summary,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "scorer_configs": self.scorer_configs,
            "passed": self.passed,
            "pass_rate": self.pass_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalResult":
        """Deserialize from dict."""
        scores = {}
        for name, feedbacks_raw in data.get("scores", {}).items():
            scores[name] = [ScorerFeedback.from_dict(fb) for fb in feedbacks_raw]
        return cls(
            eval_id=data.get("eval_id", str(uuid4())),
            experiment=data.get("experiment"),
            scores=scores,
            summary=data.get("summary", {}),
            dataset_name=data.get("dataset_name"),
            dataset_version=data.get("dataset_version"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
            scorer_configs=data.get("scorer_configs", []),
        )

    def __repr__(self) -> str:
        return f"EvalResult(eval_id='{self.eval_id[:8]}...', " f"scorers={self.scorer_names}, " f"passed={self.passed})"


def evaluate(
    data: EvalDataset | list[dict] | dict,
    scorers: list[Scorer],
    experiment: str | None = None,
    baseline: "EvalResult | None" = None,
    regression_threshold: float = 0.05,
    store: bool = True,
    **kwargs: Any,
) -> EvalResult:
    """Run evaluation scorers against a dataset.

    This is the main entry point for FlowyML evaluations. It orchestrates
    scoring, aggregation, optional regression detection, and persistence.

    Args:
        data: Evaluation data — EvalDataset, list of dicts, or dict
        scorers: List of Scorer instances to run
        experiment: Optional experiment name for tracking
        baseline: Optional baseline EvalResult for regression detection
        regression_threshold: Threshold for regression detection (default: 5%)
        store: Whether to persist results to the metadata store (default: True)
        **kwargs: Additional arguments passed to scorers

    Returns:
        EvalResult with all scores and summary

    Example:
        >>> from flowyml.evals import evaluate, EvalDataset, Accuracy, F1Score
        >>> ds = EvalDataset(
        ...     name="test",
        ...     data={
        ...         "predictions": [1, 0, 1, 1, 0],
        ...         "targets": [1, 0, 0, 1, 0],
        ...     },
        ... )
        >>> result = evaluate(ds, [Accuracy(), F1Score()])
        >>> print(result.summary)
        {"accuracy": 0.8, "f1_score": 0.75}
    """
    # Normalize input
    if isinstance(data, EvalDataset):
        dataset_name = data.name
        dataset_version = data.version
        scorer_args = data.to_scorer_args()
    elif isinstance(data, list):
        dataset_name = kwargs.pop("dataset_name", None)
        dataset_version = kwargs.pop("dataset_version", None)
        scorer_args = data
    elif isinstance(data, dict):
        dataset_name = kwargs.pop("dataset_name", None)
        dataset_version = kwargs.pop("dataset_version", None)
        scorer_args = [data]
    else:
        raise ValueError(f"Unsupported data type: {type(data)}. Use EvalDataset, list, or dict.")

    # Initialize result
    result = EvalResult(
        experiment=experiment,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        scorer_configs=[s.to_dict() for s in scorers],
        metadata=kwargs,
    )

    # Run each scorer
    for scorer in scorers:
        logger.info("Running scorer: %s", scorer.name)
        try:
            if len(scorer_args) == 1 and isinstance(scorer_args[0], dict):
                # Single batch call (classical ML pattern)
                merged_kwargs = {**scorer_args[0], **kwargs}
                feedback = scorer.score(**merged_kwargs)
                feedback.example_index = 0
                if scorer.threshold is not None and isinstance(feedback.value, (int, float)):
                    feedback.passed = feedback.value >= scorer.threshold
                result.scores[scorer.name] = [feedback]
                # Summary is the single score
                result.summary[scorer.name] = feedback.value if isinstance(feedback.value, (int, float)) else 0.0
            else:
                # Per-example scoring (GenAI pattern)
                feedbacks = scorer.score_batch(scorer_args)
                result.scores[scorer.name] = feedbacks
                # Aggregate: mean of numeric scores
                numeric_values = [fb.value for fb in feedbacks if isinstance(fb.value, (int, float))]
                result.summary[scorer.name] = (
                    round(sum(numeric_values) / len(numeric_values), 6) if numeric_values else 0.0
                )
        except Exception as e:
            logger.error("Scorer %s failed: %s", scorer.name, e)
            result.scores[scorer.name] = [
                ScorerFeedback(
                    name=scorer.name,
                    value=0.0,
                    scorer_type=scorer.scorer_type.value
                    if isinstance(scorer.scorer_type, ScorerType)
                    else str(scorer.scorer_type),
                    rationale=f"Scorer failed: {e}",
                    passed=False,
                ),
            ]
            result.summary[scorer.name] = 0.0

    # Regression detection
    if baseline is not None:
        regressions = result.regressions_from(baseline, threshold=regression_threshold)
        result.metadata["baseline_eval_id"] = baseline.eval_id
        result.metadata["regressions"] = regressions
        if regressions:
            logger.warning(
                "⚠️ Regressions detected vs baseline %s: %s",
                baseline.eval_id[:8],
                list(regressions.keys()),
            )

    # Persist to metadata store
    if store:
        try:
            _persist_eval_result(result)
        except Exception as e:
            logger.warning("Failed to persist evaluation result: %s", e)

    logger.info(
        "Evaluation complete: %s scorers, summary=%s",
        len(scorers),
        result.summary,
    )
    return result


def _persist_eval_result(result: EvalResult) -> None:
    """Persist evaluation result to the metadata store."""
    try:
        from flowyml.storage.metadata import SQLMetadataStore

        store = SQLMetadataStore()

        # Save as a run-like entry
        store.save_run(
            run_id=result.eval_id,
            metadata={
                "run_id": result.eval_id,
                "pipeline_name": f"eval_{result.experiment or 'default'}",
                "status": "completed",
                "start_time": result.created_at,
                "end_time": datetime.now().isoformat(),
                "parameters": {
                    "eval_type": "evaluation",
                    "dataset": result.dataset_name,
                    "dataset_version": result.dataset_version,
                    "scorer_names": result.scorer_names,
                },
                "metrics": result.summary,
                "tags": {
                    "type": "evaluation",
                    "passed": str(result.passed),
                    "pass_rate": str(result.pass_rate),
                },
            },
        )

        # Save individual metrics
        for scorer_name, value in result.summary.items():
            if isinstance(value, (int, float)):
                store.save_metric(result.eval_id, scorer_name, float(value))

    except Exception as e:
        logger.debug("Could not persist eval result: %s", e)

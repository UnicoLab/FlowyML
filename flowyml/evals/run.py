"""FlowyML Evaluations — EvalRun (Evaluation Run Tracking).

Extends the tracking.Run concept to provide evaluation-specific
run tracking with scorer metadata, regression alerts, and comparison.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from flowyml.evals.core import EvalResult

logger = logging.getLogger(__name__)


class EvalRun:
    """Evaluation run — tracks a single evaluation execution.

    Extends the concept of a tracking Run with evaluation-specific features:
    - Stores EvalResult with per-scorer breakdown
    - Automatic baseline comparison for regression detection
    - Integration with experiment tracking

    Attributes:
        run_id: Unique run identifier
        experiment: Experiment name
        eval_result: The evaluation result
        baseline_run_id: Optional baseline run for comparison
        status: Run status (pending, running, completed, failed)
        tags: Run tags
        created_at: Timestamp
        metadata: Additional run metadata

    Example:
        >>> run = EvalRun(experiment="text_classification_v2")
        >>> run.execute(data=eval_ds, scorers=[Accuracy(), F1Score()])
        >>> print(run.eval_result.summary)
        >>> run.compare_with(baseline_run)
    """

    def __init__(
        self,
        experiment: str | None = None,
        run_id: str | None = None,
        baseline_run_id: str | None = None,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.run_id = run_id or str(uuid4())
        self.experiment = experiment
        self.baseline_run_id = baseline_run_id
        self.eval_result: EvalResult | None = None
        self.status = "pending"
        self.tags = tags or {}
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.completed_at: str | None = None
        self._regressions: dict | None = None

    def execute(
        self,
        data: Any,
        scorers: list,
        baseline: "EvalResult | None" = None,
        regression_threshold: float = 0.05,
        **kwargs: Any,
    ) -> EvalResult:
        """Execute the evaluation run.

        Args:
            data: Evaluation dataset (EvalDataset, list, or dict)
            scorers: List of Scorer instances
            baseline: Optional baseline EvalResult for regression detection
            regression_threshold: Threshold for regression detection
            **kwargs: Additional arguments passed to evaluate()

        Returns:
            EvalResult with all scores
        """
        from flowyml.evals.core import evaluate

        self.status = "running"

        try:
            self.eval_result = evaluate(
                data=data,
                scorers=scorers,
                experiment=self.experiment,
                baseline=baseline,
                regression_threshold=regression_threshold,
                **kwargs,
            )
            self.eval_result.eval_id = self.run_id
            self.status = "completed"
            self.completed_at = datetime.now().isoformat()

            # Check for regressions
            if baseline:
                self._regressions = self.eval_result.regressions_from(
                    baseline,
                    threshold=regression_threshold,
                )
                if self._regressions:
                    self.status = "completed_with_regressions"
                    self.tags["has_regressions"] = "true"

            logger.info("EvalRun %s completed: %s", self.run_id[:8], self.eval_result.summary)
            return self.eval_result

        except Exception as e:
            self.status = "failed"
            self.completed_at = datetime.now().isoformat()
            self.metadata["error"] = str(e)
            logger.error("EvalRun %s failed: %s", self.run_id[:8], e)
            raise

    def compare_with(
        self,
        other: "EvalRun",
        threshold: float = 0.05,
    ) -> dict[str, Any]:
        """Compare this run with another evaluation run.

        Args:
            other: Another EvalRun to compare against
            threshold: Threshold for detecting significant changes

        Returns:
            Comparison dictionary with deltas and regressions
        """
        if not self.eval_result or not other.eval_result:
            raise ValueError("Both runs must have completed evaluations")

        comparison = {
            "run_a": self.run_id,
            "run_b": other.run_id,
            "metrics": {},
            "regressions": {},
        }

        all_scorers = set(self.eval_result.summary.keys()) | set(other.eval_result.summary.keys())
        for scorer_name in all_scorers:
            val_a = self.eval_result.summary.get(scorer_name)
            val_b = other.eval_result.summary.get(scorer_name)

            if val_a is not None and val_b is not None:
                delta = val_a - val_b
                comparison["metrics"][scorer_name] = {
                    "run_a": val_a,
                    "run_b": val_b,
                    "delta": round(delta, 6),
                    "improved": delta > threshold,
                    "regressed": delta < -threshold,
                }
                if delta < -threshold:
                    comparison["regressions"][scorer_name] = {
                        "from": val_b,
                        "to": val_a,
                        "delta": round(delta, 6),
                    }

        return comparison

    @property
    def regressions(self) -> dict:
        """Get detected regressions (if any)."""
        return self._regressions or {}

    @property
    def has_regressions(self) -> bool:
        """Whether any regressions were detected."""
        return bool(self._regressions)

    def to_dict(self) -> dict[str, Any]:
        """Serialize run to dict."""
        return {
            "run_id": self.run_id,
            "experiment": self.experiment,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "tags": self.tags,
            "metadata": self.metadata,
            "eval_result": self.eval_result.to_dict() if self.eval_result else None,
            "regressions": self._regressions,
        }

    def __repr__(self) -> str:
        return f"EvalRun(id='{self.run_id[:8]}...', status='{self.status}', experiment='{self.experiment}')"

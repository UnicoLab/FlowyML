"""FlowyML Evaluations — Evaluation Assertions for CI/CD.

LLM-powered test assertions that can be integrated into CI/CD pipelines.
Define quality gates for your ML models and LLM applications.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from flowyml.evals.core import EvalResult

logger = logging.getLogger(__name__)


@dataclass
class AssertionResult:
    """Result of a single assertion check.

    Attributes:
        name: Assertion name
        passed: Whether the assertion passed
        message: Human-readable result message
        expected: Expected value
        actual: Actual value
        metadata: Additional context
    """

    name: str
    passed: bool
    message: str
    expected: Any = None
    actual: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class EvalAssert:
    """Evaluation assertions for CI/CD quality gates.

    Define assertions on evaluation results to automatically pass/fail
    CI pipelines based on model quality metrics.

    Supports:
    - Minimum score thresholds per metric
    - Regression detection against baselines
    - Pass rate assertions
    - Custom assertion functions

    Example:
        >>> from flowyml.evals import EvalAssert, evaluate, Accuracy, F1Score
        >>>
        >>> # In your CI/CD test file:
        >>> result = evaluate(data=test_ds, scorers=[Accuracy(), F1Score()])
        >>>
        >>> assertions = EvalAssert(result)
        >>> assertions.assert_min_score("accuracy", 0.90)
        >>> assertions.assert_min_score("f1_score", 0.85)
        >>> assertions.assert_pass_rate(0.95)
        >>> assertions.assert_no_regression(baseline_result, threshold=0.03)
        >>>
        >>> # Raises AssertionError if any assertion fails
        >>> assertions.validate()  # or assertions.validate(raise_on_failure=True)
    """

    def __init__(self, eval_result: EvalResult | None = None):
        self.eval_result = eval_result
        self._assertions: list[AssertionResult] = []

    def set_result(self, result: EvalResult) -> "EvalAssert":
        """Set the evaluation result to assert against.

        Args:
            result: EvalResult to validate

        Returns:
            self for chaining
        """
        self.eval_result = result
        return self

    def assert_min_score(
        self,
        metric: str,
        threshold: float,
        message: str | None = None,
    ) -> "EvalAssert":
        """Assert that a metric meets a minimum score.

        Args:
            metric: Metric name (e.g., 'accuracy', 'f1_score')
            threshold: Minimum acceptable score
            message: Optional custom failure message

        Returns:
            self for chaining
        """
        if self.eval_result is None:
            self._assertions.append(
                AssertionResult(
                    name=f"min_score_{metric}",
                    passed=False,
                    message="No evaluation result set",
                ),
            )
            return self

        actual = self.eval_result.summary.get(metric)
        if actual is None:
            self._assertions.append(
                AssertionResult(
                    name=f"min_score_{metric}",
                    passed=False,
                    message=f"Metric '{metric}' not found in evaluation results",
                    expected=threshold,
                ),
            )
        else:
            # Check if lower is better
            feedbacks = self.eval_result.scores.get(metric, [])
            lower_is_better = False
            if feedbacks:
                lower_is_better = feedbacks[0].metadata.get("lower_is_better", False)

            if lower_is_better:
                passed = actual <= threshold
                default_msg = f"Metric '{metric}' = {actual:.4f} (threshold: ≤ {threshold})"
            else:
                passed = actual >= threshold
                default_msg = f"Metric '{metric}' = {actual:.4f} (threshold: ≥ {threshold})"

            self._assertions.append(
                AssertionResult(
                    name=f"min_score_{metric}",
                    passed=passed,
                    message=message or default_msg,
                    expected=threshold,
                    actual=actual,
                    metadata={"lower_is_better": lower_is_better},
                ),
            )

        return self

    def assert_max_score(
        self,
        metric: str,
        threshold: float,
        message: str | None = None,
    ) -> "EvalAssert":
        """Assert that a metric does not exceed a maximum value.

        Useful for error metrics like MSE, RMSE, toxicity.

        Args:
            metric: Metric name
            threshold: Maximum acceptable score
            message: Optional custom failure message

        Returns:
            self for chaining
        """
        if self.eval_result is None:
            self._assertions.append(
                AssertionResult(
                    name=f"max_score_{metric}",
                    passed=False,
                    message="No evaluation result set",
                ),
            )
            return self

        actual = self.eval_result.summary.get(metric)
        if actual is None:
            self._assertions.append(
                AssertionResult(
                    name=f"max_score_{metric}",
                    passed=False,
                    message=f"Metric '{metric}' not found",
                    expected=threshold,
                ),
            )
        else:
            passed = actual <= threshold
            self._assertions.append(
                AssertionResult(
                    name=f"max_score_{metric}",
                    passed=passed,
                    message=message or f"Metric '{metric}' = {actual:.4f} (max: {threshold})",
                    expected=threshold,
                    actual=actual,
                ),
            )

        return self

    def assert_no_regression(
        self,
        baseline: EvalResult,
        threshold: float = 0.05,
        metrics: list[str] | None = None,
        message: str | None = None,
    ) -> "EvalAssert":
        """Assert that no regression occurred vs a baseline.

        Args:
            baseline: Baseline EvalResult to compare against
            threshold: Maximum acceptable regression (default: 5%)
            metrics: Optional list of specific metrics to check
            message: Optional custom failure message

        Returns:
            self for chaining
        """
        if self.eval_result is None:
            self._assertions.append(
                AssertionResult(
                    name="no_regression",
                    passed=False,
                    message="No evaluation result set",
                ),
            )
            return self

        regressions = self.eval_result.regressions_from(baseline, threshold=threshold)

        if metrics:
            regressions = {k: v for k, v in regressions.items() if k in metrics}

        passed = len(regressions) == 0
        if passed:
            msg = f"No regressions detected (threshold: {threshold})"
        else:
            reg_details = ", ".join(
                f"{k}: {v['baseline']:.4f} → {v['current']:.4f} (Δ{v['delta']:.4f})" for k, v in regressions.items()
            )
            msg = f"Regressions detected: {reg_details}"

        self._assertions.append(
            AssertionResult(
                name="no_regression",
                passed=passed,
                message=message or msg,
                metadata={"regressions": regressions, "threshold": threshold},
            ),
        )

        return self

    def assert_pass_rate(
        self,
        rate: float = 0.95,
        message: str | None = None,
    ) -> "EvalAssert":
        """Assert that the overall pass rate meets a threshold.

        Args:
            rate: Minimum pass rate (0.0 to 1.0, default: 0.95)
            message: Optional custom failure message

        Returns:
            self for chaining
        """
        if self.eval_result is None:
            self._assertions.append(
                AssertionResult(
                    name="pass_rate",
                    passed=False,
                    message="No evaluation result set",
                ),
            )
            return self

        actual_rate = self.eval_result.pass_rate
        passed = actual_rate >= rate

        self._assertions.append(
            AssertionResult(
                name="pass_rate",
                passed=passed,
                message=message or f"Pass rate: {actual_rate:.2%} (threshold: {rate:.2%})",
                expected=rate,
                actual=actual_rate,
            ),
        )

        return self

    def assert_custom(
        self,
        name: str,
        condition: bool,
        message: str = "",
    ) -> "EvalAssert":
        """Add a custom assertion.

        Args:
            name: Assertion name
            condition: Boolean condition (True = pass)
            message: Human-readable message

        Returns:
            self for chaining
        """
        self._assertions.append(
            AssertionResult(name=name, passed=condition, message=message),
        )
        return self

    @property
    def results(self) -> list[AssertionResult]:
        """Get all assertion results."""
        return list(self._assertions)

    @property
    def all_passed(self) -> bool:
        """Whether all assertions passed."""
        return all(a.passed for a in self._assertions)

    @property
    def failures(self) -> list[AssertionResult]:
        """Get only failed assertions."""
        return [a for a in self._assertions if not a.passed]

    def validate(self, raise_on_failure: bool = True) -> bool:
        """Validate all assertions.

        Args:
            raise_on_failure: If True, raises AssertionError on first failure

        Returns:
            True if all assertions pass

        Raises:
            AssertionError: If raise_on_failure is True and any assertion fails
        """
        if not self._assertions:
            logger.warning("No assertions defined")
            return True

        passed = 0
        failed = 0
        failure_messages = []

        for assertion in self._assertions:
            if assertion.passed:
                passed += 1
                logger.info("✅ %s: %s", assertion.name, assertion.message)
            else:
                failed += 1
                failure_messages.append(f"❌ {assertion.name}: {assertion.message}")
                logger.error("❌ %s: %s", assertion.name, assertion.message)

        logger.info(
            "Assertions: %d passed, %d failed, %d total",
            passed,
            failed,
            len(self._assertions),
        )

        if failed > 0 and raise_on_failure:
            raise AssertionError(
                f"Evaluation assertions failed ({failed}/{len(self._assertions)}):\n" + "\n".join(failure_messages),
            )

        return failed == 0

    def summary(self) -> dict[str, Any]:
        """Get assertion summary."""
        return {
            "total": len(self._assertions),
            "passed": sum(1 for a in self._assertions if a.passed),
            "failed": sum(1 for a in self._assertions if not a.passed),
            "all_passed": self.all_passed,
            "results": [{"name": a.name, "passed": a.passed, "message": a.message} for a in self._assertions],
        }

    def __repr__(self) -> str:
        p = sum(1 for a in self._assertions if a.passed)
        f = sum(1 for a in self._assertions if not a.passed)
        return f"EvalAssert(passed={p}, failed={f}, total={len(self._assertions)})"

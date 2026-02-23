"""FlowyML Evaluations — DeepEval Adapter.

Wraps `deepeval` metrics as FlowyML :class:`Scorer` instances so they
participate in ``evaluate()``, ``EvalSuite``, ``JudgeArena``, and the
CLI/API seamlessly.

Install the optional dependency::

    pip install deepeval

Adapted metrics:

* **AnswerRelevancy** — how relevant is the answer to the query
* **Hallucination** — does the answer contain unsupported claims
* **Bias** — does the answer contain biased content
* **Toxicity** — does the answer contain toxic content
"""

from __future__ import annotations

import logging
from typing import Any

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType
from flowyml.evals.utils import safe_import, format_rationale

logger = logging.getLogger(__name__)

_PACKAGE = "deepeval"
_INSTALL = "pip install deepeval"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_deepeval():
    """Lazy-import deepeval to keep FlowyML importable without it."""
    return safe_import("deepeval.metrics", package=_PACKAGE, install_hint=_INSTALL)


def _build_test_case(
    *,
    inputs: Any = None,
    outputs: Any = None,
    context: Any = None,
    expected: Any = None,
):
    """Convert FlowyML scorer kwargs → DeepEval ``LLMTestCase``."""
    tc_mod = safe_import("deepeval.test_case", package=_PACKAGE, install_hint=_INSTALL)
    ctx = context if isinstance(context, list) else ([context] if context else None)
    return tc_mod.LLMTestCase(
        input=str(inputs or ""),
        actual_output=str(outputs or ""),
        retrieval_context=ctx,
        expected_output=str(expected) if expected else None,
    )


# ---------------------------------------------------------------------------
# Scorers
# ---------------------------------------------------------------------------


class DeepEvalAnswerRelevancy(Scorer):
    """Wraps ``deepeval.metrics.AnswerRelevancyMetric``."""

    name = "deepeval.answer_relevancy"
    scorer_type = ScorerType.GENAI
    description = "DeepEval: measures how relevant the answer is to the input query"

    def __init__(self, *, model: str = "gpt-4o-mini", threshold: float | None = 0.7):
        self.model = model
        self.threshold = threshold

    def score(self, *, inputs: Any = None, outputs: Any = None, context: Any = None, **kw: Any) -> ScorerFeedback:
        metrics = _get_deepeval()
        metric = metrics.AnswerRelevancyMetric(model=self.model, threshold=self.threshold or 0.5)
        tc = _build_test_case(inputs=inputs, outputs=outputs, context=context)
        try:
            metric.measure(tc)
            value = float(metric.score)
        except Exception as exc:
            logger.warning("DeepEval AnswerRelevancy failed: %s", exc)
            value = 0.0

        passed = value >= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, details=getattr(metric, "reason", None), source="DeepEval"),
        )


class DeepEvalHallucination(Scorer):
    """Wraps ``deepeval.metrics.HallucinationMetric``."""

    name = "deepeval.hallucination"
    scorer_type = ScorerType.GENAI
    description = "DeepEval: detects hallucinated content not supported by context"
    lower_is_better = True

    def __init__(self, *, model: str = "gpt-4o-mini", threshold: float | None = 0.3):
        self.model = model
        self.threshold = threshold

    def score(self, *, inputs: Any = None, outputs: Any = None, context: Any = None, **kw: Any) -> ScorerFeedback:
        metrics = _get_deepeval()
        metric = metrics.HallucinationMetric(model=self.model, threshold=self.threshold or 0.5)
        tc = _build_test_case(inputs=inputs, outputs=outputs, context=context)
        try:
            metric.measure(tc)
            value = float(metric.score)
        except Exception as exc:
            logger.warning("DeepEval Hallucination failed: %s", exc)
            value = 1.0

        passed = value <= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, details=getattr(metric, "reason", None), source="DeepEval"),
        )


class DeepEvalBias(Scorer):
    """Wraps ``deepeval.metrics.BiasMetric``."""

    name = "deepeval.bias"
    scorer_type = ScorerType.GENAI
    description = "DeepEval: detects biased content in the output"
    lower_is_better = True

    def __init__(self, *, model: str = "gpt-4o-mini", threshold: float | None = 0.3):
        self.model = model
        self.threshold = threshold

    def score(self, *, inputs: Any = None, outputs: Any = None, context: Any = None, **kw: Any) -> ScorerFeedback:
        metrics = _get_deepeval()
        metric = metrics.BiasMetric(model=self.model, threshold=self.threshold or 0.5)
        tc = _build_test_case(inputs=inputs, outputs=outputs, context=context)
        try:
            metric.measure(tc)
            value = float(metric.score)
        except Exception as exc:
            logger.warning("DeepEval Bias failed: %s", exc)
            value = 1.0

        passed = value <= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, details=getattr(metric, "reason", None), source="DeepEval"),
        )


class DeepEvalToxicity(Scorer):
    """Wraps ``deepeval.metrics.ToxicityMetric``."""

    name = "deepeval.toxicity"
    scorer_type = ScorerType.GENAI
    description = "DeepEval: detects toxic content in the output"
    lower_is_better = True

    def __init__(self, *, model: str = "gpt-4o-mini", threshold: float | None = 0.3):
        self.model = model
        self.threshold = threshold

    def score(self, *, inputs: Any = None, outputs: Any = None, context: Any = None, **kw: Any) -> ScorerFeedback:
        metrics = _get_deepeval()
        metric = metrics.ToxicityMetric(model=self.model, threshold=self.threshold or 0.5)
        tc = _build_test_case(inputs=inputs, outputs=outputs, context=context)
        try:
            metric.measure(tc)
            value = float(metric.score)
        except Exception as exc:
            logger.warning("DeepEval Toxicity failed: %s", exc)
            value = 1.0

        passed = value <= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, details=getattr(metric, "reason", None), source="DeepEval"),
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DEEPEVAL_SCORERS: dict[str, type[Scorer]] = {
    "deepeval.answer_relevancy": DeepEvalAnswerRelevancy,
    "deepeval.hallucination": DeepEvalHallucination,
    "deepeval.bias": DeepEvalBias,
    "deepeval.toxicity": DeepEvalToxicity,
}

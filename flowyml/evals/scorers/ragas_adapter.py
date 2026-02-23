"""FlowyML Evaluations — RAGAS Adapter.

Wraps `ragas` metrics as FlowyML :class:`Scorer` instances so they
participate in ``evaluate()``, ``EvalSuite``, ``JudgeArena``, and the
CLI/API seamlessly.

Install the optional dependency::

    pip install ragas

Adapted metrics:

* **Faithfulness** — factual consistency with retrieved context
* **ContextPrecision** — relevance of retrieved context chunks
* **ContextRecall** — coverage of ground-truth by retrieved context
* **AnswerRelevancy** — relevance of the answer to the question
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType
from flowyml.evals.utils import safe_import, format_rationale

logger = logging.getLogger(__name__)

_PACKAGE = "ragas"
_INSTALL = "pip install ragas"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_ragas_metrics():
    """Lazy-import ragas metrics."""
    return safe_import("ragas.metrics", package=_PACKAGE, install_hint=_INSTALL)


def _build_sample(
    *,
    inputs: Any = None,
    outputs: Any = None,
    context: Any = None,
    expected: Any = None,
):
    """Convert FlowyML scorer kwargs → RAGAS ``SingleTurnSample``."""
    dataset_mod = safe_import("ragas.dataset_schema", package=_PACKAGE, install_hint=_INSTALL)
    ctx = context if isinstance(context, list) else ([str(context)] if context else [])
    return dataset_mod.SingleTurnSample(
        user_input=str(inputs or ""),
        response=str(outputs or ""),
        retrieved_contexts=ctx,
        reference=str(expected) if expected else "",
    )


def _run_async(coro):
    """Run a coroutine synchronously (RAGAS metrics are async)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Scorers
# ---------------------------------------------------------------------------


class RagasFaithfulness(Scorer):
    """Wraps ``ragas.metrics.Faithfulness``."""

    name = "ragas.faithfulness"
    scorer_type = ScorerType.GENAI
    description = "RAGAS: factual consistency of the answer with the context"

    def __init__(self, *, threshold: float | None = 0.7):
        self.threshold = threshold

    def score(
        self,
        *,
        inputs: Any = None,
        outputs: Any = None,
        context: Any = None,
        expected: Any = None,
        **kw: Any,
    ) -> ScorerFeedback:
        metrics = _get_ragas_metrics()
        metric = metrics.Faithfulness()
        sample = _build_sample(inputs=inputs, outputs=outputs, context=context, expected=expected)
        try:
            value = float(_run_async(metric.single_turn_ascore(sample)))
        except Exception as exc:
            logger.warning("RAGAS Faithfulness failed: %s", exc)
            value = 0.0

        passed = value >= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, source="RAGAS"),
        )


class RagasContextPrecision(Scorer):
    """Wraps ``ragas.metrics.LLMContextPrecisionWithReference``."""

    name = "ragas.context_precision"
    scorer_type = ScorerType.GENAI
    description = "RAGAS: relevance of retrieved context to the query"

    def __init__(self, *, threshold: float | None = 0.7):
        self.threshold = threshold

    def score(
        self,
        *,
        inputs: Any = None,
        outputs: Any = None,
        context: Any = None,
        expected: Any = None,
        **kw: Any,
    ) -> ScorerFeedback:
        metrics = _get_ragas_metrics()
        metric_cls = getattr(metrics, "LLMContextPrecisionWithReference", None) or getattr(
            metrics,
            "ContextPrecision",
            None,
        )
        if metric_cls is None:
            return ScorerFeedback(
                name=self.name,
                value=0.0,
                passed=False,
                rationale="RAGAS ContextPrecision metric not found",
            )
        metric = metric_cls()
        sample = _build_sample(inputs=inputs, outputs=outputs, context=context, expected=expected)
        try:
            value = float(_run_async(metric.single_turn_ascore(sample)))
        except Exception as exc:
            logger.warning("RAGAS ContextPrecision failed: %s", exc)
            value = 0.0

        passed = value >= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, source="RAGAS"),
        )


class RagasContextRecall(Scorer):
    """Wraps ``ragas.metrics.LLMContextRecall``."""

    name = "ragas.context_recall"
    scorer_type = ScorerType.GENAI
    description = "RAGAS: how much relevant information was retrieved"

    def __init__(self, *, threshold: float | None = 0.7):
        self.threshold = threshold

    def score(
        self,
        *,
        inputs: Any = None,
        outputs: Any = None,
        context: Any = None,
        expected: Any = None,
        **kw: Any,
    ) -> ScorerFeedback:
        metrics = _get_ragas_metrics()
        metric_cls = getattr(metrics, "LLMContextRecall", None) or getattr(metrics, "ContextRecall", None)
        if metric_cls is None:
            return ScorerFeedback(
                name=self.name,
                value=0.0,
                passed=False,
                rationale="RAGAS ContextRecall metric not found",
            )
        metric = metric_cls()
        sample = _build_sample(inputs=inputs, outputs=outputs, context=context, expected=expected)
        try:
            value = float(_run_async(metric.single_turn_ascore(sample)))
        except Exception as exc:
            logger.warning("RAGAS ContextRecall failed: %s", exc)
            value = 0.0

        passed = value >= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, source="RAGAS"),
        )


class RagasAnswerRelevancy(Scorer):
    """Wraps ``ragas.metrics.ResponseRelevancy``."""

    name = "ragas.answer_relevancy"
    scorer_type = ScorerType.GENAI
    description = "RAGAS: relevance of the answer to the original question"

    def __init__(self, *, threshold: float | None = 0.7):
        self.threshold = threshold

    def score(
        self,
        *,
        inputs: Any = None,
        outputs: Any = None,
        context: Any = None,
        expected: Any = None,
        **kw: Any,
    ) -> ScorerFeedback:
        metrics = _get_ragas_metrics()
        metric_cls = getattr(metrics, "ResponseRelevancy", None) or getattr(metrics, "AnswerRelevancy", None)
        if metric_cls is None:
            return ScorerFeedback(
                name=self.name,
                value=0.0,
                passed=False,
                rationale="RAGAS AnswerRelevancy metric not found",
            )
        metric = metric_cls()
        sample = _build_sample(inputs=inputs, outputs=outputs, context=context, expected=expected)
        try:
            value = float(_run_async(metric.single_turn_ascore(sample)))
        except Exception as exc:
            logger.warning("RAGAS AnswerRelevancy failed: %s", exc)
            value = 0.0

        passed = value >= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, source="RAGAS"),
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

RAGAS_SCORERS: dict[str, type[Scorer]] = {
    "ragas.faithfulness": RagasFaithfulness,
    "ragas.context_precision": RagasContextPrecision,
    "ragas.context_recall": RagasContextRecall,
    "ragas.answer_relevancy": RagasAnswerRelevancy,
}

"""FlowyML Evaluations — Phoenix Adapter.

Wraps `arize-phoenix-evals` templates as FlowyML :class:`Scorer` instances
so they participate in ``evaluate()``, ``EvalSuite``, ``JudgeArena``, and
the CLI/API seamlessly.

Install the optional dependency::

    pip install arize-phoenix-evals

Adapted metrics:

* **Hallucination** (Faithfulness) — detects unsupported claims
* **Toxicity** — detects harmful content
* **QACorrectness** — verifies answer accuracy against reference
* **Summarization** — evaluates summary quality
"""

from __future__ import annotations

import logging
from typing import Any

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType
from flowyml.evals.utils import safe_import, format_rationale

logger = logging.getLogger(__name__)

_PACKAGE = "arize-phoenix-evals"
_INSTALL = "pip install arize-phoenix-evals"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_phoenix_evals():
    """Lazy-import phoenix.evals."""
    return safe_import("phoenix.evals", package=_PACKAGE, install_hint=_INSTALL)


def _get_phoenix_templates():
    """Lazy-import phoenix.evals templates."""
    return safe_import("phoenix.evals.default_templates", package=_PACKAGE, install_hint=_INSTALL)


def _run_phoenix_eval(
    template_name: str,
    *,
    inputs: Any = None,
    outputs: Any = None,
    context: Any = None,
    expected: Any = None,
    model_name: str = "openai/gpt-4o-mini",
) -> tuple[float, str]:
    """Run a Phoenix template evaluation and return (score, label).

    Returns:
        Tuple of (normalised 0-1 score, raw label string)
    """
    phoenix = _get_phoenix_evals()

    # Phoenix evaluates via small DataFrames
    import pandas as pd

    ctx = context if isinstance(context, str) else " ".join(context) if isinstance(context, list) else ""
    df = pd.DataFrame(
        [
            {
                "input": str(inputs or ""),
                "output": str(outputs or ""),
                "reference": str(expected or ""),
                "context": ctx,
            },
        ],
    )

    try:
        model = phoenix.OpenAIModel(model=model_name.replace("openai/", ""))
    except Exception:
        # Fallback if model init fails
        return 0.0, "error"

    try:
        template = getattr(phoenix, template_name, None)
        if template is None:
            templates = _get_phoenix_templates()
            template = getattr(templates, template_name, None)

        if template is None:
            return 0.0, f"template_{template_name}_not_found"

        results = phoenix.llm_classify(
            dataframe=df,
            model=model,
            template=template,
            rails=["relevant", "irrelevant"] if "relevance" in template_name.lower() else ["correct", "incorrect"],
            provide_explanation=True,
        )

        label = results.iloc[0].get("label", "unknown")
        explanation = results.iloc[0].get("explanation", "")

        # Map categorical labels → 0-1
        positive_labels = {"relevant", "correct", "non-toxic", "faithful", "good"}
        score = 1.0 if label.lower() in positive_labels else 0.0

        return score, f"{label}: {explanation}" if explanation else label

    except Exception as exc:
        logger.warning("Phoenix %s eval failed: %s", template_name, exc)
        return 0.0, str(exc)


# ---------------------------------------------------------------------------
# Scorers
# ---------------------------------------------------------------------------


class PhoenixHallucination(Scorer):
    """Wraps Phoenix Hallucination / Faithfulness evaluation template."""

    name = "phoenix.hallucination"
    scorer_type = ScorerType.GENAI
    description = "Phoenix: detects hallucinated content not supported by context"
    lower_is_better = True

    def __init__(self, *, model: str = "openai/gpt-4o-mini", threshold: float | None = 0.3):
        self.model = model
        self.threshold = threshold

    def score(self, *, inputs: Any = None, outputs: Any = None, context: Any = None, **kw: Any) -> ScorerFeedback:
        value, detail = _run_phoenix_eval(
            "HALLUCINATION_PROMPT_TEMPLATE",
            inputs=inputs,
            outputs=outputs,
            context=context,
            model_name=self.model,
        )
        passed = value <= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, details=detail, source="Phoenix"),
        )


class PhoenixToxicity(Scorer):
    """Wraps Phoenix Toxicity evaluation template."""

    name = "phoenix.toxicity"
    scorer_type = ScorerType.GENAI
    description = "Phoenix: detects toxic, harmful, or inappropriate content"
    lower_is_better = True

    def __init__(self, *, model: str = "openai/gpt-4o-mini", threshold: float | None = 0.3):
        self.model = model
        self.threshold = threshold

    def score(self, *, inputs: Any = None, outputs: Any = None, context: Any = None, **kw: Any) -> ScorerFeedback:
        value, detail = _run_phoenix_eval(
            "TOXICITY_PROMPT_TEMPLATE",
            inputs=inputs,
            outputs=outputs,
            context=context,
            model_name=self.model,
        )
        passed = value <= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, details=detail, source="Phoenix"),
        )


class PhoenixQACorrectness(Scorer):
    """Wraps Phoenix QA Correctness evaluation template."""

    name = "phoenix.qa_correctness"
    scorer_type = ScorerType.GENAI
    description = "Phoenix: verifies answer accuracy against reference text"

    def __init__(self, *, model: str = "openai/gpt-4o-mini", threshold: float | None = 0.7):
        self.model = model
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
        value, detail = _run_phoenix_eval(
            "QA_PROMPT_TEMPLATE",
            inputs=inputs,
            outputs=outputs,
            context=context,
            expected=expected,
            model_name=self.model,
        )
        passed = value >= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, details=detail, source="Phoenix"),
        )


class PhoenixSummarization(Scorer):
    """Wraps Phoenix Summarization evaluation template."""

    name = "phoenix.summarization"
    scorer_type = ScorerType.GENAI
    description = "Phoenix: evaluates quality and faithfulness of text summaries"

    def __init__(self, *, model: str = "openai/gpt-4o-mini", threshold: float | None = 0.7):
        self.model = model
        self.threshold = threshold

    def score(self, *, inputs: Any = None, outputs: Any = None, context: Any = None, **kw: Any) -> ScorerFeedback:
        value, detail = _run_phoenix_eval(
            "SUMMARIZATION_PROMPT_TEMPLATE",
            inputs=inputs,
            outputs=outputs,
            context=context,
            model_name=self.model,
        )
        passed = value >= self.threshold if self.threshold else None
        return ScorerFeedback(
            name=self.name,
            value=value,
            passed=passed,
            rationale=format_rationale(self.name, value, details=detail, source="Phoenix"),
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

PHOENIX_SCORERS: dict[str, type[Scorer]] = {
    "phoenix.hallucination": PhoenixHallucination,
    "phoenix.toxicity": PhoenixToxicity,
    "phoenix.qa_correctness": PhoenixQACorrectness,
    "phoenix.summarization": PhoenixSummarization,
}

"""FlowyML Evaluations — Custom Scorers.

Factory functions for creating custom scorers:
- make_judge(): Create LLM-based judges with custom instructions/rubrics
- make_scorer(): Wrap any Python function as a Scorer
"""

import logging
from typing import Any
from collections.abc import Callable

from flowyml.evals.base import Scorer, ScorerFeedback, ScorerType

logger = logging.getLogger(__name__)


class FunctionScorer(Scorer):
    """Scorer that wraps an arbitrary Python function.

    The wrapped function should accept keyword arguments matching the Scorer.score()
    signature and return either a float, a dict with 'value' key, or a ScorerFeedback.

    Example:
        >>> def my_metric(predictions, targets, **kw):
        ...     return sum(p == t for p, t in zip(predictions, targets)) / len(targets)
        >>> scorer = FunctionScorer("custom_accuracy", my_metric, "classification")
    """

    def __init__(
        self,
        name: str,
        fn: Callable,
        scorer_type: str = "custom",
        threshold: float | None = None,
        description: str = "",
    ):
        super().__init__(name=name, threshold=threshold)
        self.fn = fn
        self.scorer_type = (
            ScorerType(scorer_type)
            if isinstance(scorer_type, str) and scorer_type in ScorerType._value2member_map_
            else ScorerType.CUSTOM
        )
        self.description = description or f"Custom scorer: {name}"

    def score(self, **kwargs: Any) -> ScorerFeedback:
        result = self.fn(**kwargs)

        if isinstance(result, ScorerFeedback):
            return result
        elif isinstance(result, dict):
            value = result.get("value", 0.0)
            rationale = result.get("rationale")
            metadata = result.get("metadata", {})
        else:
            value = float(result)
            rationale = None
            metadata = {}

        passed = None
        if self.threshold is not None and isinstance(value, (int, float)):
            lower_is_better = metadata.get("lower_is_better", False)
            passed = value <= self.threshold if lower_is_better else value >= self.threshold

        return ScorerFeedback(
            name=self.name,
            value=value,
            scorer_type=self.scorer_type.value if isinstance(self.scorer_type, ScorerType) else str(self.scorer_type),
            rationale=rationale,
            passed=passed,
            metadata=metadata,
        )


class CustomJudge(Scorer):
    """LLM-based judge created via make_judge().

    Uses custom instructions and optional rubric/examples to evaluate outputs.
    """

    name = "custom_judge"
    scorer_type = ScorerType.GENAI

    def __init__(
        self,
        name: str,
        instructions: str,
        model: str = "openai:/gpt-4o-mini",
        feedback_type: type = float,
        rubric: dict | None = None,
        examples: list[dict] | None = None,
        threshold: float | None = None,
    ):
        super().__init__(name=name, threshold=threshold)
        self.instructions = instructions
        self.model = model
        self.feedback_type = feedback_type
        self.rubric = rubric
        self.examples = examples or []
        self.description = f"Custom LLM judge: {name}"

    def _build_system_prompt(self) -> str:
        """Build the system prompt from instructions, rubric, and examples."""
        parts = [
            "You are an expert evaluator.",
            f"Task: {self.instructions}",
        ]

        if self.rubric:
            parts.append("\nRubric:")
            for score, description in sorted(self.rubric.items(), reverse=True):
                parts.append(f"  {score}: {description}")

        if self.feedback_type is float:
            parts.append(
                '\nRespond in JSON with exactly two fields: "score" (float 0.0 to 1.0) and "rationale" (string).',
            )
        elif self.feedback_type is bool:
            parts.append(
                '\nRespond in JSON with exactly two fields: "score" (boolean true/false) and "rationale" (string).',
            )
        elif hasattr(self.feedback_type, "__args__"):
            # Literal type — extract allowed values
            allowed = list(self.feedback_type.__args__)
            parts.append(
                f'\nRespond in JSON with exactly two fields: "score" (one of: {allowed}) and "rationale" (string).',
            )
        else:
            parts.append(
                '\nRespond in JSON with exactly two fields: "score" and "rationale" (string).',
            )

        if self.examples:
            parts.append("\nExamples:")
            for ex in self.examples:
                parts.append(f"  Input: {ex.get('input', '')}")
                parts.append(f"  Output: {ex.get('output', '')}")
                parts.append(f"  Score: {ex.get('score', '')}")
                if ex.get("reason"):
                    parts.append(f"  Reason: {ex['reason']}")
                parts.append("")

        return "\n".join(parts)

    def score(
        self,
        *,
        inputs: Any = None,
        outputs: Any = None,
        context: Any = None,
        **kwargs: Any,
    ) -> ScorerFeedback:
        if outputs is None:
            raise ValueError(f"Judge '{self.name}' requires 'outputs'")

        from flowyml.evals.scorers.genai import _call_llm, _parse_json_response

        system_prompt = self._build_system_prompt()

        prompt_parts = []
        if inputs:
            prompt_parts.append(f"Input: {inputs}")
        if context:
            ctx_text = "\n".join(context) if isinstance(context, list) else str(context)
            prompt_parts.append(f"Context:\n{ctx_text}")
        prompt_parts.append(f"Output: {outputs}")
        prompt_parts.append("Evaluate:")
        prompt = "\n\n".join(prompt_parts)

        try:
            response = _call_llm(self.model, prompt, system_prompt)
            parsed = _parse_json_response(response)
            raw_value = parsed.get("score", 0.0)
            rationale = parsed.get("rationale", "")

            # Convert value to expected type
            if self.feedback_type is float:
                value = float(raw_value)
            elif self.feedback_type is bool:
                value = bool(raw_value)
            else:
                value = raw_value

        except Exception as e:
            logger.warning("Custom judge '%s' LLM call failed: %s", self.name, e)
            return ScorerFeedback(
                name=self.name,
                value=0.0 if self.feedback_type in (float, int) else False,
                scorer_type=self.scorer_type.value,
                rationale=f"LLM call failed: {e}",
                passed=False,
                metadata={"model": self.model, "error": str(e)},
            )

        passed = None
        if self.threshold is not None and isinstance(value, (int, float)):
            passed = value >= self.threshold

        return ScorerFeedback(
            name=self.name,
            value=value,
            scorer_type=self.scorer_type.value,
            rationale=rationale,
            passed=passed,
            metadata={"model": self.model, "judge_type": "custom"},
        )


def make_judge(
    name: str,
    instructions: str,
    model: str = "openai:/gpt-4o-mini",
    feedback_type: type = float,
    rubric: dict | None = None,
    examples: list[dict] | None = None,
    threshold: float | None = None,
) -> CustomJudge:
    """Create a custom LLM-based judge scorer.

    Args:
        name: Name of the judge
        instructions: Evaluation instructions for the LLM
        model: LLM model URI (e.g., 'openai:/gpt-4o-mini', 'gemini:/gemini-3-flash')
        feedback_type: Type of feedback value (float, bool, or Literal type)
        rubric: Optional scoring rubric {score: description}
        examples: Optional few-shot examples [{input, output, score, reason}]
        threshold: Optional threshold for pass/fail

    Returns:
        CustomJudge scorer instance

    Example:
        >>> from typing import Literal
        >>> judge = make_judge(
        ...     name="quality",
        ...     instructions="Evaluate response quality",
        ...     model="openai:/gpt-4o-mini",
        ...     feedback_type=Literal["excellent", "good", "fair", "poor"],
        ... )
        >>> result = judge(inputs="What is X?", outputs="X is...")
    """
    return CustomJudge(
        name=name,
        instructions=instructions,
        model=model,
        feedback_type=feedback_type,
        rubric=rubric,
        examples=examples,
        threshold=threshold,
    )


def make_scorer(
    name: str,
    fn: Callable,
    scorer_type: str = "custom",
    threshold: float | None = None,
    description: str = "",
) -> FunctionScorer:
    """Wrap any Python function as a FlowyML Scorer.

    The function should accept keyword arguments matching the Scorer.score() signature.
    It should return a float, a dict with 'value' key, or a ScorerFeedback.

    Args:
        name: Scorer name
        fn: Function to wrap
        scorer_type: Category ('classification', 'regression', 'custom')
        threshold: Optional threshold for pass/fail
        description: Human-readable description

    Returns:
        FunctionScorer wrapping the function

    Example:
        >>> def weighted_accuracy(predictions, targets, weights=None, **kw):
        ...     if weights is None:
        ...         weights = [1.0] * len(targets)
        ...     correct = sum(w * (p == t) for w, p, t in zip(weights, predictions, targets))
        ...     return correct / sum(weights)
        >>> scorer = make_scorer("weighted_accuracy", weighted_accuracy, "classification")
    """
    return FunctionScorer(
        name=name,
        fn=fn,
        scorer_type=scorer_type,
        threshold=threshold,
        description=description,
    )

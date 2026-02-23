"""FlowyML Evaluations — Scorer Protocol and Data Models.

This module defines the core abstractions for the evaluation framework:
- ScorerFeedback: Result from a single evaluation
- Scorer: Abstract base class for all evaluators (classical ML + GenAI)
- ScorerType: Enum for categorizing scorers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any

import logging

logger = logging.getLogger(__name__)


class ScorerType(Enum):
    """Categories of scorers available in FlowyML."""

    # Classical ML
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"

    # GenAI / LLM
    GENAI = "genai"
    RAG = "rag"
    SAFETY = "safety"
    CONVERSATIONAL = "conversational"

    # Custom
    CUSTOM = "custom"


@dataclass
class ScorerFeedback:
    """Result from a single scorer evaluation.

    Represents the output of one scorer applied to one example. Works for both
    classical ML metrics (value is typically a float) and GenAI LLM-as-a-judge
    (value can be float, bool, or str, with rationale explaining the judgment).

    Attributes:
        name: Scorer name (e.g., "accuracy", "relevance")
        value: Score value — float for numeric metrics, bool for pass/fail,
               str for categorical judgments
        rationale: Human-readable explanation (populated by LLM judges)
        passed: Whether the score meets the threshold (None if no threshold)
        metadata: Extra info (cost, latency, model used, etc.)
        example_index: Index of the example in the dataset (for batch scoring)
        scorer_type: Type of scorer that produced this feedback
        timestamp: When the feedback was generated

    Examples:
        # Classical ML
        >>> ScorerFeedback(name="accuracy", value=0.95, scorer_type="classification")

        # GenAI LLM-as-a-judge
        >>> ScorerFeedback(
        ...     name="relevance",
        ...     value=0.87,
        ...     scorer_type="genai",
        ...     rationale="The response addresses the user's question directly...",
        ...     metadata={"model": "gpt-4o-mini", "cost": 0.002},
        ... )
    """

    name: str
    value: float | str | bool
    scorer_type: str = "custom"
    rationale: str | None = None
    passed: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    example_index: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScorerFeedback":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Scorer(ABC):
    """Abstract base class for all FlowyML scorers.

    The unified interface for both classical ML metrics and GenAI LLM-as-a-judge
    evaluators. Subclasses must implement the `score()` method.

    The `score()` method uses keyword-only arguments to serve both domains:
    - Classical ML: uses `predictions` and `targets`
    - GenAI: uses `inputs`, `outputs`, and optionally `context`/`expected`

    Attributes:
        name: Human-readable scorer name
        scorer_type: Category of scorer (classification, regression, genai, etc.)
        threshold: Optional threshold for pass/fail determination
        description: Human-readable description of the scorer

    Example:
        >>> class MyAccuracy(Scorer):
        ...     name = "accuracy"
        ...     scorer_type = ScorerType.CLASSIFICATION
        ...
        ...     def score(self, *, predictions, targets, **kwargs):
        ...         correct = sum(p == t for p, t in zip(predictions, targets))
        ...         return ScorerFeedback(name=self.name, value=correct / len(targets))
    """

    name: str = "unnamed_scorer"
    scorer_type: ScorerType = ScorerType.CUSTOM
    threshold: float | None = None
    description: str = ""

    def __init__(
        self,
        name: str | None = None,
        threshold: float | None = None,
        **kwargs: Any,
    ):
        if name:
            self.name = name
        if threshold is not None:
            self.threshold = threshold
        # Store extra config
        self._config = kwargs

    @abstractmethod
    def score(
        self,
        *,
        # Classical ML arguments
        predictions: Any | None = None,
        targets: Any | None = None,
        # GenAI arguments
        inputs: Any | None = None,
        outputs: Any | None = None,
        context: Any | None = None,
        expected: Any | None = None,
        # Shared
        **kwargs: Any,
    ) -> ScorerFeedback:
        """Score a single evaluation example or a batch.

        Classical ML usage:
            scorer.score(predictions=[1, 0, 1], targets=[1, 0, 0])

        GenAI usage:
            scorer.score(inputs="What is X?", outputs="X is...", context=["doc1"])

        Args:
            predictions: Model predictions (classical ML)
            targets: Ground truth labels (classical ML)
            inputs: Input query/prompt (GenAI)
            outputs: Model output/response (GenAI)
            context: Retrieved context documents (GenAI/RAG)
            expected: Expected output for comparison (GenAI)
            **kwargs: Additional scorer-specific arguments

        Returns:
            ScorerFeedback with the evaluation result
        """

    def score_batch(self, data: list[dict[str, Any]]) -> list[ScorerFeedback]:
        """Score multiple examples.

        Default implementation iterates over examples calling score().
        Override for batch-optimized implementations.

        Args:
            data: List of dictionaries, each containing arguments for score()

        Returns:
            List of ScorerFeedback objects
        """
        results = []
        for i, example in enumerate(data):
            try:
                feedback = self.score(**example)
                feedback.example_index = i
                if self.threshold is not None and isinstance(feedback.value, (int, float)):
                    feedback.passed = feedback.value >= self.threshold
                results.append(feedback)
            except Exception as e:
                logger.warning("Scorer %s failed on example %d: %s", self.name, i, e)
                results.append(
                    ScorerFeedback(
                        name=self.name,
                        value=0.0,
                        scorer_type=self.scorer_type.value
                        if isinstance(self.scorer_type, ScorerType)
                        else str(self.scorer_type),
                        rationale=f"Error: {e}",
                        passed=False,
                        example_index=i,
                    ),
                )
        return results

    def __call__(self, **kwargs: Any) -> ScorerFeedback:
        """Allow using scorer as a callable."""
        feedback = self.score(**kwargs)
        if self.threshold is not None and isinstance(feedback.value, (int, float)):
            feedback.passed = feedback.value >= self.threshold
        return feedback

    def __repr__(self) -> str:
        threshold_str = f", threshold={self.threshold}" if self.threshold is not None else ""
        return f"{self.__class__.__name__}(name='{self.name}'{threshold_str})"

    def to_dict(self) -> dict[str, Any]:
        """Serialize scorer configuration."""
        return {
            "name": self.name,
            "scorer_type": self.scorer_type.value
            if isinstance(self.scorer_type, ScorerType)
            else str(self.scorer_type),
            "threshold": self.threshold,
            "description": self.description,
            "config": self._config,
        }

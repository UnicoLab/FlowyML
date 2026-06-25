"""FlowyML Evaluations — EvalSuite (Reusable Scorer Collection).

A named, reusable collection of scorers that can be applied to evaluation
datasets. Provides a convenient API for grouping and running multiple scorers.
"""

import logging
from typing import Any

from flowyml.evals.base import Scorer
from flowyml.evals.core import EvalResult, evaluate
from flowyml.evals.dataset import EvalDataset

logger = logging.getLogger(__name__)


class EvalSuite:
    """Named collection of scorers for reusable evaluation workflows.

    Groups multiple scorers into a single, named suite that can be shared
    across pipelines, experiments, and teams. Supports fluent API via
    chaining and integrates with the full FlowyML evaluation pipeline.

    Attributes:
        name: Suite name for identification
        scorers: List of configured scorers
        description: Human-readable description
        tags: Tags for categorization

    Example:
        >>> from flowyml.evals import EvalSuite, Accuracy, F1Score, Precision

        >>> # Create a reusable suite
        >>> classification_suite = EvalSuite(
        ...     name="classification_quality",
        ...     scorers=[
        ...         Accuracy(threshold=0.9),
        ...         F1Score(threshold=0.85),
        ...         Precision(),
        ...     ],
        ...     description="Standard classification quality gates",
        ... )

        >>> # Run it
        >>> result = classification_suite.run(data=eval_dataset)

        >>> # Or use with evaluate()
        >>> result = classification_suite.run(
        ...     data=eval_dataset,
        ...     experiment="v2_model",
        ...     baseline=previous_result,
        ... )

        >>> # GenAI suite
        >>> rag_suite = EvalSuite(
        ...     name="rag_quality",
        ...     scorers=[Relevance(), Faithfulness(), Toxicity(threshold=0.1)],
        ... )
    """

    def __init__(
        self,
        name: str,
        scorers: list[Scorer] | None = None,
        description: str = "",
        tags: dict[str, str] | None = None,
    ):
        """Initialize the evaluation suite.

        Args:
            name: Suite name
            scorers: List of Scorer instances
            description: Human-readable description
            tags: Tags for categorization
        """
        self.name = name
        self.scorers = list(scorers) if scorers else []
        self.description = description
        self.tags = tags or {}

    def add(self, scorer: Scorer) -> "EvalSuite":
        """Add a scorer to the suite.

        Args:
            scorer: Scorer to add

        Returns:
            self for chaining
        """
        self.scorers.append(scorer)
        return self

    def remove(self, scorer_name: str) -> "EvalSuite":
        """Remove a scorer by name.

        Args:
            scorer_name: Name of scorer to remove

        Returns:
            self for chaining
        """
        self.scorers = [s for s in self.scorers if s.name != scorer_name]
        return self

    def run(
        self,
        data: EvalDataset | list[dict] | dict,
        experiment: str | None = None,
        baseline: EvalResult | None = None,
        regression_threshold: float = 0.05,
        store: bool = True,
        **kwargs: Any,
    ) -> EvalResult:
        """Run all scorers in the suite against data.

        Args:
            data: Evaluation data (EvalDataset, list of dicts, or dict)
            experiment: Experiment name for tracking
            baseline: Optional baseline for regression detection
            regression_threshold: Threshold for flagging regressions
            store: Whether to persist results
            **kwargs: Additional arguments for evaluate()

        Returns:
            EvalResult with all scores
        """
        if not self.scorers:
            raise ValueError(f"EvalSuite '{self.name}' has no scorers configured")

        result = evaluate(
            data=data,
            scorers=self.scorers,
            experiment=experiment or self.name,
            baseline=baseline,
            regression_threshold=regression_threshold,
            store=store,
            **kwargs,
        )

        result.metadata["suite_name"] = self.name
        result.metadata["suite_tags"] = self.tags

        return result

    @property
    def scorer_names(self) -> list[str]:
        """Get names of all scorers in the suite."""
        return [s.name for s in self.scorers]

    def to_dict(self) -> dict[str, Any]:
        """Serialize suite configuration."""
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "scorers": [s.to_dict() for s in self.scorers],
        }

    def __len__(self) -> int:
        return len(self.scorers)

    def __repr__(self) -> str:
        return f"EvalSuite(name='{self.name}', scorers={self.scorer_names})"

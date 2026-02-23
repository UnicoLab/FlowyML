"""FlowyML Evaluations — Judge Arena (A/B Testing for Evaluators).

Compares multiple judges (scorers) against each other and human labels
to find the best evaluator for a given domain. Computes inter-annotator
agreement, correlation with human judgments, and Elo-style rankings.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from flowyml.evals.base import Scorer, ScorerFeedback
from flowyml.evals.dataset import EvalDataset

logger = logging.getLogger(__name__)


@dataclass
class JudgeArenaResult:
    """Results from a Judge Arena evaluation.

    Attributes:
        judges: List of judge names
        human_agreement: Per-judge agreement with human labels {judge: float}
        inter_judge_agreement: Pairwise agreement between judges
        rankings: Elo-style ranking of judges
        detailed_scores: Per-judge per-example scores
        metadata: Additional metadata

    Example:
        >>> arena = JudgeArena(judges=[Relevance(), Coherence(), my_judge])
        >>> result = arena.evaluate(data=eval_ds, human_labels=[0.9, 0.5, ...])
        >>> result.rankings
        [{"judge": "relevance", "elo": 1523}, ...]
    """

    judges: list[str] = field(default_factory=list)
    human_agreement: dict[str, float] = field(default_factory=dict)
    inter_judge_agreement: dict[str, dict[str, float]] = field(default_factory=dict)
    rankings: list[dict[str, Any]] = field(default_factory=list)
    detailed_scores: dict[str, list[ScorerFeedback]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def best_judge(self) -> str:
        """Get the name of the best judge (highest human agreement)."""
        if not self.human_agreement:
            return self.judges[0] if self.judges else ""
        return max(self.human_agreement, key=self.human_agreement.get)

    def cost_analysis(self) -> dict[str, dict[str, float]]:
        """Analyse cost-per-evaluation for each judge.

        Extracts cost metadata from scorer feedbacks to show how much
        each judge costs to run. Useful for choosing judges with the
        best cost-to-accuracy tradeoff.

        Returns:
            Dict mapping judge name to cost breakdown:
            {"judge": {"total_cost": float, "avg_cost": float, "n_scored": int}}
        """
        analysis: dict[str, dict[str, float]] = {}
        for judge_name, feedbacks in self.detailed_scores.items():
            total_cost = 0.0
            total_latency = 0.0
            n_scored = len(feedbacks)
            for fb in feedbacks:
                total_cost += fb.metadata.get("cost", 0.0)
                total_latency += fb.metadata.get("latency", 0.0)
            analysis[judge_name] = {
                "total_cost": round(total_cost, 6),
                "avg_cost": round(total_cost / n_scored, 6) if n_scored else 0.0,
                "total_latency": round(total_latency, 4),
                "avg_latency": round(total_latency / n_scored, 4) if n_scored else 0.0,
                "n_scored": n_scored,
            }
        return analysis

    def correlation_matrix(self) -> dict[str, dict[str, float]]:
        """Get the inter-judge correlation matrix.

        Returns a symmetric matrix of pairwise Pearson correlations between
        all judges. Useful for identifying judges that agree/disagree.

        Returns:
            Dict of {judge_a: {judge_b: correlation}} for all pairs
        """
        return dict(self.inter_judge_agreement)

    def agreement_scores(self) -> dict[str, float]:
        """Get per-judge agreement with human labels.

        Returns:
            Dict mapping judge name to human agreement score (Pearson r)
        """
        return dict(self.human_agreement)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "judges": self.judges,
            "human_agreement": self.human_agreement,
            "inter_judge_agreement": self.inter_judge_agreement,
            "rankings": self.rankings,
            "cost_analysis": self.cost_analysis(),
            "metadata": self.metadata,
        }


class JudgeArena:
    """A/B Testing arena for evaluating evaluators.

    Compares multiple judges against each other and human labels to determine
    which judge best correlates with human judgment.

    This is a key differentiator for FlowyML — no other framework lets you
    A/B test your evaluators to find the best one.

    Args:
        judges: List of Scorer instances to compete
        human_labels: Optional human-provided scores for ground truth

    Example:
        >>> from flowyml.evals import JudgeArena, Relevance, Faithfulness, make_judge
        >>>
        >>> custom = make_judge("quality", "Evaluate response quality")
        >>> arena = JudgeArena(
        ...     judges=[Relevance(), Faithfulness(), custom],
        ... )
        >>> result = arena.evaluate(
        ...     data=eval_ds,
        ...     human_labels=[0.9, 0.5, 0.8, 0.3, 0.7],
        ... )
        >>> print(result.best_judge())
        >>> print(result.rankings)
    """

    def __init__(self, judges: list[Scorer]):
        if len(judges) < 2:
            raise ValueError("JudgeArena requires at least 2 judges")
        self.judges = judges

    def evaluate(
        self,
        data: EvalDataset | list[dict],
        human_labels: list[float] | None = None,
        **kwargs: Any,
    ) -> JudgeArenaResult:
        """Run the arena evaluation.

        Each judge scores all examples. Then we compute:
        1. Agreement with human labels (if provided)
        2. Inter-judge pairwise agreement
        3. Elo-style rankings

        Args:
            data: Evaluation data
            human_labels: Optional human scores (one per example)
            **kwargs: Additional arguments passed to scorers

        Returns:
            JudgeArenaResult with rankings and agreement scores
        """
        # Normalize input
        if isinstance(data, EvalDataset):
            scorer_args = data.to_scorer_args()
        elif isinstance(data, list):
            scorer_args = data
        else:
            raise ValueError("Data must be EvalDataset or list of dicts")

        result = JudgeArenaResult(
            judges=[j.name for j in self.judges],
            metadata={"n_examples": len(scorer_args), **kwargs},
        )

        # Score all examples with all judges
        judge_scores: dict[str, list[float]] = {}

        for judge in self.judges:
            logger.info("Arena: Running judge '%s'...", judge.name)
            feedbacks = judge.score_batch(scorer_args)
            result.detailed_scores[judge.name] = feedbacks

            # Extract numeric values
            values = []
            for fb in feedbacks:
                if isinstance(fb.value, (int, float)):
                    values.append(float(fb.value))
                elif isinstance(fb.value, bool):
                    values.append(1.0 if fb.value else 0.0)
                else:
                    values.append(0.0)
            judge_scores[judge.name] = values

        # Compute human agreement
        if human_labels:
            human = np.array(human_labels, dtype=float)
            for judge_name, scores in judge_scores.items():
                if len(scores) == len(human):
                    judge_arr = np.array(scores, dtype=float)
                    # Pearson correlation
                    std_h = np.std(human)
                    std_j = np.std(judge_arr)
                    if std_h > 0 and std_j > 0:
                        correlation = float(
                            np.corrcoef(human, judge_arr)[0, 1],
                        )
                    else:
                        correlation = 0.0
                    # Mean absolute difference
                    mae = float(np.mean(np.abs(human - judge_arr)))
                    result.human_agreement[judge_name] = round(correlation, 4)
                    result.metadata.setdefault("mae_from_human", {})[judge_name] = round(mae, 4)

        # Compute inter-judge agreement (pairwise correlation)
        judge_names = list(judge_scores.keys())
        for i, name_a in enumerate(judge_names):
            result.inter_judge_agreement[name_a] = {}
            for j, name_b in enumerate(judge_names):
                if i == j:
                    result.inter_judge_agreement[name_a][name_b] = 1.0
                else:
                    arr_a = np.array(judge_scores[name_a], dtype=float)
                    arr_b = np.array(judge_scores[name_b], dtype=float)
                    if len(arr_a) == len(arr_b) and len(arr_a) > 1:
                        std_a = np.std(arr_a)
                        std_b = np.std(arr_b)
                        if std_a > 0 and std_b > 0:
                            corr = float(np.corrcoef(arr_a, arr_b)[0, 1])
                        else:
                            corr = 0.0
                    else:
                        corr = 0.0
                    result.inter_judge_agreement[name_a][name_b] = round(corr, 4)

        # Compute Elo rankings via pairwise comparisons
        elo_ratings = self._compute_elo(judge_scores, human_labels)
        result.rankings = sorted(
            [{"judge": name, "elo": round(elo, 1)} for name, elo in elo_ratings.items()],
            key=lambda x: x["elo"],
            reverse=True,
        )

        return result

    def _compute_elo(
        self,
        judge_scores: dict[str, list[float]],
        human_labels: list[float] | None = None,
        k: float = 32.0,
        initial: float = 1500.0,
    ) -> dict[str, float]:
        """Compute Elo ratings for judges based on pairwise comparisons.

        For each example, judges are compared pairwise. The judge closer
        to the human label (or with a higher score if no human labels) wins.
        """
        ratings = dict.fromkeys(judge_scores, initial)
        names = list(judge_scores.keys())

        if not names or not judge_scores[names[0]]:
            return ratings

        n_examples = len(judge_scores[names[0]])

        for idx in range(n_examples):
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    name_a, name_b = names[i], names[j]

                    if idx >= len(judge_scores[name_a]) or idx >= len(judge_scores[name_b]):
                        continue

                    score_a = judge_scores[name_a][idx]
                    score_b = judge_scores[name_b][idx]

                    if human_labels and idx < len(human_labels):
                        human = human_labels[idx]
                        # Judge closer to human wins
                        diff_a = abs(score_a - human)
                        diff_b = abs(score_b - human)
                        if diff_a < diff_b:
                            actual_a = 1.0  # A wins
                        elif diff_b < diff_a:
                            actual_a = 0.0  # B wins
                        else:
                            actual_a = 0.5  # Draw
                    else:
                        # Without human labels, higher score wins
                        if score_a > score_b:
                            actual_a = 1.0
                        elif score_b > score_a:
                            actual_a = 0.0
                        else:
                            actual_a = 0.5

                    # Expected scores
                    expected_a = 1 / (1 + math.pow(10, (ratings[name_b] - ratings[name_a]) / 400))
                    expected_b = 1 - expected_a

                    # Update ratings
                    ratings[name_a] += k * (actual_a - expected_a)
                    ratings[name_b] += k * ((1 - actual_a) - expected_b)

        return ratings

    def __repr__(self) -> str:
        return f"JudgeArena(judges={[j.name for j in self.judges]})"

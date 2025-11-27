"""Model comparison and leaderboard functionality."""

from typing import Any
from dataclasses import dataclass
from uniflow.storage.metadata import SQLiteMetadataStore


@dataclass
class ModelScore:
    """A model's score on a leaderboard."""

    model_name: str
    run_id: str
    metric_value: float
    timestamp: str
    metadata: dict[str, Any]


class ModelLeaderboard:
    """Compare and rank models based on metrics.

    Examples:
        >>> leaderboard = ModelLeaderboard(metric="accuracy")
        >>> # Add model scores
        >>> leaderboard.add_score(model_name="bert-base", run_id="run_123", score=0.92)
        >>> # Get top models
        >>> top_models = leaderboard.get_top(n=5)
        >>> leaderboard.display()
    """

    def __init__(
        self,
        metric: str,
        higher_is_better: bool = True,
        metadata_store: SQLiteMetadataStore | None = None,
    ):
        """Args:
        metric: Metric to compare on
        higher_is_better: Whether higher values are better
        metadata_store: Optional metadata store.
        """
        self.metric = metric
        self.higher_is_better = higher_is_better
        self.metadata_store = metadata_store or SQLiteMetadataStore()

    def add_score(
        self,
        model_name: str,
        run_id: str,
        score: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a model score to the leaderboard."""
        # Save to metadata store
        self.metadata_store.save_metric(
            run_id=run_id,
            name=f"leaderboard_{self.metric}",
            value=score,
        )

        # Also save model info as artifact
        self.metadata_store.save_artifact(
            artifact_id=f"{run_id}_leaderboard",
            metadata={
                "name": model_name,
                "type": "leaderboard_entry",
                "run_id": run_id,
                "value": str(score),
                "metric": self.metric,
                "metadata": metadata or {},
            },
        )

    def get_top(self, n: int = 10) -> list[ModelScore]:
        """Get top N models."""
        # Query all leaderboard entries
        artifacts = self.metadata_store.list_assets(type="leaderboard_entry")

        # Filter by metric
        entries = [a for a in artifacts if a.get("metric") == self.metric]

        # Sort
        entries.sort(
            key=lambda x: float(x.get("value", 0)),
            reverse=self.higher_is_better,
        )

        # Convert to ModelScore
        scores = []
        for entry in entries[:n]:
            scores.append(
                ModelScore(
                    model_name=entry.get("name"),
                    run_id=entry.get("run_id"),
                    metric_value=float(entry.get("value", 0)),
                    timestamp=entry.get("created_at", ""),
                    metadata=entry.get("metadata", {}),
                ),
            )

        return scores

    def display(self, n: int = 10) -> None:
        """Display the leaderboard."""
        scores = self.get_top(n)

        if not scores:
            return

        for _i, _score in enumerate(scores, 1):
            pass

    def compare_models(self, run_ids: list[str]) -> dict[str, Any]:
        """Compare specific models side-by-side."""
        comparison = {
            "metric": self.metric,
            "models": [],
        }

        for run_id in run_ids:
            # Get metrics for this run
            metrics = self.metadata_store.get_metrics(run_id)
            metric_val = next(
                (m["value"] for m in metrics if m["name"] == self.metric),
                None,
            )

            # Get run details
            run = self.metadata_store.load_run(run_id)

            comparison["models"].append(
                {
                    "run_id": run_id,
                    "metric_value": metric_val,
                    "pipeline": run.get("pipeline_name") if run else None,
                    "status": run.get("status") if run else None,
                },
            )

        # Sort by metric value
        comparison["models"].sort(
            key=lambda x: x.get("metric_value", 0) or 0,
            reverse=self.higher_is_better,
        )

        return comparison


def compare_runs(
    run_ids: list[str],
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """Compare multiple runs across metrics.

    Args:
        run_ids: List of run IDs to compare
        metrics: Optional list of specific metrics to compare

    Returns:
        Comparison dictionary
    """
    store = SQLiteMetadataStore()

    comparison = {
        "runs": {},
        "metrics": {},
    }

    # Collect all metrics across runs
    all_metric_names = set()

    for run_id in run_ids:
        run_metrics = store.get_metrics(run_id)
        run_data = {
            "metrics": {m["name"]: m["value"] for m in run_metrics},
        }

        all_metric_names.update(run_data["metrics"].keys())
        comparison["runs"][run_id] = run_data

    # Filter metrics if specified
    if metrics:
        all_metric_names = set(metrics)

    # Organize by metric
    for metric_name in all_metric_names:
        comparison["metrics"][metric_name] = {
            run_id: comparison["runs"][run_id]["metrics"].get(metric_name) for run_id in run_ids
        }

    return comparison

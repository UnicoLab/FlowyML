from fastapi import APIRouter, HTTPException
from typing import Optional
from uniflow.tracking.leaderboard import ModelLeaderboard, compare_runs
from uniflow.storage.metadata import SQLiteMetadataStore

router = APIRouter()

@router.get("/{metric}")
async def get_leaderboard(
    metric: str,
    higher_is_better: bool = True,
    n: int = 10
):
    """Get leaderboard for a metric."""
    store = SQLiteMetadataStore()
    leaderboard = ModelLeaderboard(metric, higher_is_better, store)
    
    top_models = leaderboard.get_top(n=n)
    
    return {
        "metric": metric,
        "higher_is_better": higher_is_better,
        "models": [
            {
                "rank": i + 1,
                "model_name": model.model_name,
                "run_id": model.run_id,
                "score": model.metric_value,
                "timestamp": model.timestamp,
                "metadata": model.metadata
            }
            for i, model in enumerate(top_models)
        ]
    }

@router.post("/compare")
async def compare_model_runs(run_ids: list, metrics: Optional[list] = None):
    """Compare multiple runs."""
    comparison = compare_runs(run_ids, metrics)
    return comparison

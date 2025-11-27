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
    try:
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
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
async def compare_model_runs(run_ids: list, metrics: Optional[list] = None):
    """Compare multiple runs."""
    comparison = compare_runs(run_ids, metrics)
    return comparison

@router.post("/generate_sample_data")
async def generate_sample_data():
    """Generate sample data for the leaderboard."""
    import random
    from datetime import datetime, timedelta
    from uniflow.storage.metadata import SQLiteMetadataStore
    
    try:
        store = SQLiteMetadataStore()
        
        models = ["ResNet50", "BERT-Base", "YOLOv8", "EfficientNet", "GPT-2"]
        metrics = ["accuracy", "loss", "f1_score", "latency"]
        
        for i in range(10):
            run_id = f"run_{random.randint(1000, 9999)}"
            model_name = random.choice(models)
            
            # Save run metadata
            store.save_run(run_id, {
                "run_id": run_id,
                "pipeline_name": "training_pipeline",
                "status": "completed",
                "start_time": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration": random.uniform(10, 100),
                "success": True
            })
            
            # Save metrics
            store.save_metric(run_id, "accuracy", random.uniform(0.7, 0.99))
            store.save_metric(run_id, "loss", random.uniform(0.01, 0.5))
            store.save_metric(run_id, "f1_score", random.uniform(0.6, 0.95))
            store.save_metric(run_id, "latency", random.uniform(10, 200))
            
            # Save model artifact with timestamp
            store.save_artifact(f"{run_id}_model", {
                "artifact_id": f"{run_id}_model",
                "name": model_name,
                "type": "Model",
                "run_id": run_id,
                "step": "train",
                "value": f"Model: {model_name}",
                "created_at": datetime.now().isoformat()
            })
            
            # Save leaderboard entry for this model
            store.save_artifact(f"{run_id}_leaderboard", {
                "artifact_id": f"{run_id}_leaderboard",
                "name": model_name,
                "type": "leaderboard_entry",
                "run_id": run_id,
                "value": str(store.get_metrics(run_id, "accuracy")[0]["value"] if store.get_metrics(run_id, "accuracy") else 0),
                "metric": "accuracy",
                "created_at": datetime.now().isoformat(),
                "metadata": {"model_type": model_name}
            })
            
        return {"success": True, "message": "Sample data generated"}
    except Exception as e:
        print(f"Error generating sample data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from flowy.storage.metadata import SQLiteMetadataStore
from flowy.utils.config import get_config

router = APIRouter()

def get_store():
    config = get_config()
    # Assuming default path or from config
    # The SQLiteMetadataStore defaults to .flowy/metadata.db which is what we want for now
    return SQLiteMetadataStore()

@router.get("/")
async def list_pipelines():
    """List all unique pipelines."""
    store = get_store()
    # We need to add a method to get unique pipelines or query manually
    # Since we can't easily modify the store right now without potentially breaking things or reloading modules,
    # we will use a direct query here or add a method to the store if possible.
    # But wait, I can modify SQLiteMetadataStore.
    # For now, let's just use what we have.
    # We can fetch all runs and extract unique pipeline names, but that's inefficient.
    # Let's add a method to SQLiteMetadataStore to list pipelines.
    
    # Actually, I'll just implement it here using raw SQL for now to avoid modifying core too much unless needed.
    import sqlite3
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT pipeline_name FROM runs ORDER BY pipeline_name")
    rows = cursor.fetchall()
    conn.close()
    
    pipelines = [row[0] for row in rows if row[0]]
    return {"pipelines": pipelines}

@router.get("/{pipeline_name}/runs")
async def list_pipeline_runs(pipeline_name: str, limit: int = 10):
    """List runs for a specific pipeline."""
    store = get_store()
    runs = store.query(pipeline_name=pipeline_name)
    return {"runs": runs[:limit]}

@router.get("/stats")
async def get_all_pipelines_stats():
    """Get statistics for all pipelines."""
    try:
        store = get_store()
        import sqlite3
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT pipeline_name FROM runs")
        pipelines = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not pipelines:
            return {"total_pipelines": 0, "total_runs": 0, "pipelines": []}
        
        stats = []
        for pipeline_name in pipelines:
            runs = store.query(pipeline_name=pipeline_name)
            total = len(runs)
            successful = len([r for r in runs if r.get('status') == 'completed'])
            stats.append({
                "name": pipeline_name,
                "total_runs": total,
                "success_rate": successful / total if total > 0 else 0
            })
        
        return {
            "total_pipelines": len(pipelines),
            "total_runs": sum(s["total_runs"] for s in stats),
            "pipelines": stats
        }
    except Exception as e:
        # Database might not exist yet
        return {"total_pipelines": 0, "total_runs": 0, "pipelines": [], "error": str(e)}

@router.get("/{pipeline_name}/stats")
async def get_pipeline_stats(pipeline_name: str):
    """Get statistics for a specific pipeline."""
    try:
        store = get_store()
        runs = store.query(pipeline_name=pipeline_name)
        
        total_runs = len(runs)
        if total_runs == 0:
            return {"total_runs": 0, "success_rate": 0, "avg_duration": 0}
            
        successful_runs = [r for r in runs if r.get('status') == 'completed']
        success_rate = len(successful_runs) / total_runs if total_runs > 0 else 0
        
        durations = [r.get('duration', 0) for r in runs if r.get('duration') is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_runs": total_runs,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "last_run": runs[0] if runs else None
        }
    except Exception as e:
        return {"total_runs": 0, "success_rate": 0, "avg_duration": 0, "error": str(e)}

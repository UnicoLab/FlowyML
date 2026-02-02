"""
Test artifacts and metrics saving.
"""

import pytest
from flowyml.storage.metadata import SQLiteMetadataStore
from datetime import datetime


def test_artifacts_and_metrics_saving(tmp_path):
    """Test saving artifacts and metrics to a temporary database."""
    db_path = tmp_path / "test_metadata.db"
    store = SQLiteMetadataStore(db_path=str(db_path))
    run_id = f"test_artifacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 1. Save Run
    metadata = {
        "run_id": run_id,
        "pipeline_name": "artifact_test_pipeline",
        "status": "completed",
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "duration": 5.0,
        "success": True,
        "steps": {},
    }
    store.save_run(run_id, metadata)

    # Verify run saved
    saved_run = store.load_run(run_id)
    assert saved_run is not None
    assert saved_run["run_id"] == run_id

    # 2. Save Artifacts
    artifacts = [
        {"name": "dataset", "type": "DataFrame", "value": "rows: 1000, cols: 20"},
        {"name": "model", "type": "RandomForest", "value": "n_estimators=100"},
        {"name": "confusion_matrix", "type": "dict", "value": '{"TP": 90, "FP": 10}'},
    ]

    for i, art in enumerate(artifacts):
        art_id = f"{run_id}_step_{i}_{art['name']}"
        art_meta = {
            "name": art["name"],
            "type": art["type"],
            "run_id": run_id,
            "step": f"step_{i}",
            "value": art["value"],
            "created_at": datetime.now().isoformat(),
        }
        store.save_artifact(art_id, art_meta)

    # 3. Save Metrics
    metrics = {
        "accuracy": 0.95,
        "loss": 0.05,
        "f1_score": 0.94,
    }

    for name, value in metrics.items():
        store.save_metric(run_id, name, value)

    # Verify metrics saved
    saved_metrics = store.get_metrics(run_id)
    assert len(saved_metrics) == 3
    names = [m["name"] for m in saved_metrics]
    assert "accuracy" in names
    assert "loss" in names
    assert "f1_score" in names

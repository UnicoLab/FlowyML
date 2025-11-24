"""
Test script to verify artifacts and metrics saving.
"""
from flowy.storage.metadata import SQLiteMetadataStore
from datetime import datetime
import json

print("🧪 Testing Artifacts and Metrics Saving...")

store = SQLiteMetadataStore()
run_id = f"test_artifacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# 1. Save Run
metadata = {
    'run_id': run_id,
    'pipeline_name': 'artifact_test_pipeline',
    'status': 'completed',
    'start_time': datetime.now().isoformat(),
    'end_time': datetime.now().isoformat(),
    'duration': 5.0,
    'success': True,
    'steps': {}
}
store.save_run(run_id, metadata)
print(f"✅ Saved run: {run_id}")

# 2. Save Artifacts
artifacts = [
    {'name': 'dataset', 'type': 'DataFrame', 'value': 'rows: 1000, cols: 20'},
    {'name': 'model', 'type': 'RandomForest', 'value': 'n_estimators=100'},
    {'name': 'confusion_matrix', 'type': 'dict', 'value': '{"TP": 90, "FP": 10}'}
]

for i, art in enumerate(artifacts):
    art_id = f"{run_id}_step_{i}_{art['name']}"
    art_meta = {
        'name': art['name'],
        'type': art['type'],
        'run_id': run_id,
        'step': f"step_{i}",
        'value': art['value'],
        'created_at': datetime.now().isoformat()
    }
    store.save_artifact(art_id, art_meta)
    print(f"✅ Saved artifact: {art['name']}")

# 3. Save Metrics
metrics = {
    'accuracy': 0.95,
    'loss': 0.05,
    'f1_score': 0.94
}

for name, value in metrics.items():
    store.save_metric(run_id, name, value)
    print(f"✅ Saved metric: {name}")

print("\n🌐 Check the UI:")
print(f"   Run Details: http://localhost:8080/runs/{run_id}")
print(f"   Artifacts: http://localhost:8080/assets")

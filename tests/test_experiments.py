"""
Test script to verify experiments tracking.
"""
from flowyml.tracking.experiment import Experiment
from flowyml.storage.metadata import SQLiteMetadataStore
from datetime import datetime
import json

print("🧪 Testing Experiments Tracking...")

# 1. Create Experiment
exp_name = f"test_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
print(f"📝 Creating experiment: {exp_name}")

exp = Experiment(
    name=exp_name,
    description="Testing experiment tracking integration",
    tags={"framework": "flowyml", "test": "true"},
)

# 2. Log Runs
run_ids = [
    f"run_alpha_{datetime.now().strftime('%H%M%S')}",
    f"run_beta_{datetime.now().strftime('%H%M%S')}",
]

# Create dummy runs in DB first (foreign key constraint)
store = SQLiteMetadataStore()
for run_id in run_ids:
    store.save_run(
        run_id,
        {
            "run_id": run_id,
            "pipeline_name": "test_pipeline",
            "status": "completed",
            "start_time": datetime.now().isoformat(),
            "duration": 1.0,
            "success": True,
        },
    )

# Log to experiment
print(f"📊 Logging runs to experiment...")
exp.log_run(run_ids[0], metrics={"accuracy": 0.85, "loss": 0.15}, parameters={"lr": 0.01})
exp.log_run(run_ids[1], metrics={"accuracy": 0.92, "loss": 0.08}, parameters={"lr": 0.001})

print("✅ Runs logged successfully!")

print("\n🌐 Check the API:")
print(f"   List Experiments: http://localhost:8080/api/experiments")
print(f"   Experiment Details: http://localhost:8080/api/experiments/{exp_name}")

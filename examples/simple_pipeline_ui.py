"""
Simple UniFlow Pipeline Example with UI Integration.

This demonstrates the simplest possible UniFlow pipeline with UI visibility.

Usage:
    $ python examples/simple_pipeline_ui.py
"""

from uniflow import Pipeline, step, context
from uniflow.storage.metadata import SQLiteMetadataStore
import time

# Define context with parameters
ctx = context(
    learning_rate=0.001,
    epochs=10,
)


# Define steps
@step(outputs=["data/processed"])
def load_and_preprocess():
    """Load and preprocess data."""
    print("📥 Loading and preprocessing data...")
    time.sleep(0.5)
    return {"samples": 1000, "features": 20}


@step(inputs=["data/processed"], outputs=["model/trained"])
def train_model(data, learning_rate: float, epochs: int):
    """Train a model with auto-injected parameters."""
    print(f"🚀 Training model with lr={learning_rate}, epochs={epochs}")
    print(f"   Data: {data}")
    time.sleep(0.5)
    return {"accuracy": 0.95, "loss": 0.05}


# Create and run pipeline
print("\n" + "=" * 70)
print("🌊 Running UniFlow Pipeline with UI Integration")
print("=" * 70 + "\n")

pipeline = Pipeline("simple_example_ui", context=ctx)
pipeline.add_step(load_and_preprocess)
pipeline.add_step(train_model)

result = pipeline.run(debug=True)

# Manually save to metadata store for UI (until auto-save is working)
if result.success:
    print(f"\n✅ Pipeline completed in {result.duration_seconds:.2f}s")
    print(f"📊 Model accuracy: {result.outputs['model/trained']['accuracy']}")

    # Save to metadata database
    print("\n💾 Saving run metadata to database...")
    metadata_store = SQLiteMetadataStore()
    metadata = {
        "run_id": result.run_id,
        "pipeline_name": result.pipeline_name,
        "status": "completed",
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat() if result.end_time else None,
        "duration": result.duration_seconds,
        "success": True,
        "context": ctx._params,
        "steps": result.to_dict()["steps"],
    }
    metadata_store.save_run(result.run_id, metadata)

    print("✅ Run saved to database!")
    print("\n🌐 View in UI:")
    print("   Dashboard: http://localhost:8080")
    print(f"   This run: http://localhost:8080/runs/{result.run_id}")
    print("\n💡 Refresh your browser to see the run!")

print("\n" + "=" * 70)

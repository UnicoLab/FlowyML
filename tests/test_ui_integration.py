"""
Test pipeline to verify UI integration works.
This should populate the database and show in the UI.
"""

# Note: Module reloading removed as it causes test pollution and isinstance failures

import sys

from uniflow import Pipeline, step, context
import time

# Define context with parameters
ctx = context(
    learning_rate=0.001,
    epochs=5,
    batch_size=32,
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
print("🧪 Testing UniFlow UI Integration")
print("=" * 70)

pipeline = Pipeline("ui_test_pipeline", context=ctx)
pipeline.add_step(load_and_preprocess)
pipeline.add_step(train_model)

result = pipeline.run(debug=True)

if result.success:
    print(f"\n✅ Pipeline completed in {result.duration_seconds:.2f}s")
    print(f"📊 Model accuracy: {result.outputs['model/trained']['accuracy']}")
    print(f"\n🌐 View in UI:")
    print(f"   Dashboard: http://localhost:8080")
    print(f"   This run: http://localhost:8080/runs/{result.run_id}")
    print("\n💡 Refresh your browser to see the run!")
else:
    print(f"\n❌ Pipeline failed")

print("=" * 70)

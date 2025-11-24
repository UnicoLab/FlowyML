"""
Simple Flowy Pipeline Example.

This is the simplest possible Flowy pipeline to get you started.

Usage:
    $ python examples/simple_pipeline.py
"""

from flowy import Pipeline, step, context
import time

# Define context with parameters
ctx = context(
    learning_rate=0.001,
    epochs=10
)

# Define steps
@step(outputs=["data/processed"])
def load_and_preprocess():
    """Load and preprocess data."""
    print("Loading and preprocessing data...")
    time.sleep(30)
    return {"samples": 1000, "features": 20}

@step(inputs=["data/processed"], outputs=["model/trained"])
def train_model(data, learning_rate: float, epochs: int):
    """Train a model with auto-injected parameters."""
    print(f"Training model with lr={learning_rate}, epochs={epochs}")
    print(f"Data: {data}")
    return {"accuracy": 0.95, "loss": 0.05}

# Create and run pipeline
pipeline = Pipeline("simple_example", context=ctx, enable_cache=False)
pipeline.add_step(load_and_preprocess)
pipeline.add_step(train_model)

result = pipeline.run(debug=True)

if result.success:
    print(f"\n✅ Pipeline completed in {result.duration_seconds:.2f}s")
    print(f"Model accuracy: {result.outputs['model/trained']['accuracy']}")

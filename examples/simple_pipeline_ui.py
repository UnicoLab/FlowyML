"""
Simple flowyml Pipeline Example with UI Integration.

This demonstrates the simplest possible flowyml pipeline with UI visibility.
FlowyML automatically starts the UI server and saves run metadata.

Usage:
    $ python examples/simple_pipeline_ui.py
"""

import time
import numpy as np
from flowyml import Pipeline, step, context, Metrics, Dataset

# Define context with parameters
# These will be automatically injected into steps that accept them as arguments
ctx = context(
    learning_rate=0.001,
    epochs=10,
    batch_size=32,
)


# Define steps
@step(outputs=["data/processed"])
def load_and_preprocess():
    """Load and preprocess data, returning a Dataset asset."""
    print("📥 Loading and preprocessing data...")
    time.sleep(1)

    # Create some synthetic data
    data = {
        "features": np.random.randn(100, 5).tolist(),
        "labels": np.random.randint(0, 2, 100).tolist(),
    }

    # Returning a Dataset asset provides better UI visualization (stats, histograms)
    return Dataset.create(
        data=data,
        name="processed_data",
        properties={"format": "json", "source": "synthetic"},
    )


@step(inputs=["data/processed"], outputs=["model/trained"])
def train_model(data: Dataset, learning_rate: float, epochs: int):
    """Train a model with auto-injected parameters."""
    print(f"🚀 Training model with lr={learning_rate}, epochs={epochs}")
    print(f"   Input data: {data.name} ({len(data.data['features'])} samples)")

    # Simulate training
    for i in range(epochs):
        time.sleep(0.1)
        print(f"   Iteration {i+1}/{epochs}...")

    return {"accuracy": 0.92, "loss": 0.08}


@step(inputs=["model/trained"], outputs=["metrics/eval"])
def evaluate_model(trained_model: dict):
    """Evaluate and return a Metrics asset for UI visualization."""
    print("📈 Evaluating model...")
    accuracy = trained_model["accuracy"]

    # Returning a Metrics asset enables interactive charts in the UI
    return Metrics.create(
        accuracy=accuracy,
        f1_score=0.89,
        name="evaluation_metrics",
    )


def run_pipeline():
    # Create pipeline
    pipeline = Pipeline("simple_ui_showcase", context=ctx)

    # Add steps
    pipeline.add_step(load_and_preprocess)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_model)

    # Run the pipeline
    # Run the pipeline
    # auto_start_ui=True is the default, which starts the uvicorn server if not running
    result = pipeline.run()

    if result.success:
        print("\n✅ Pipeline completed successfully!")
        print(f"📊 Final Accuracy: {result.outputs['metrics/eval'].data['accuracy']}")
    else:
        print("\n❌ Pipeline failed!")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🌊 flowyml Pipeline with Automatic UI Integration")
    print("=" * 70 + "\n")

    run_pipeline()

    print("\n" + "=" * 70)

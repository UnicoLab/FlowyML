"""
Simple Flowy Pipeline Example.

This is the simplest possible Flowy pipeline to get you started.

Usage:
    $ python examples/simple_pipeline.py
"""

from flowy import Pipeline, step, context, Dataset, Model, Metrics
import time

# Define context with parameters
ctx = context(
    learning_rate=0.001,
    epochs=10,
    batch_size=32
)

# Define steps
@step(outputs=["dataset"])
def load_and_preprocess():
    """Load and preprocess data."""
    print("Loading and preprocessing data...")
    time.sleep(1) # Simulate work
    
    # Return a Dataset asset
    return Dataset.create(
        data={"X": [1, 2, 3], "y": [0, 1, 0]},
        name="training_data",
        description="Preprocessed training dataset"
    )

@step(inputs=["dataset"], outputs=["model", "metrics"])
def train_model(dataset: Dataset, learning_rate: float, epochs: int):
    """Train a model with auto-injected parameters."""
    print(f"Training model with lr={learning_rate}, epochs={epochs}")
    print(f"Training on dataset: {dataset.name}")
    time.sleep(2) # Simulate training
    
    # Return Model and Metrics assets
    return (
        Model.create(
            data={"weights": [0.1, 0.2, 0.3]},
            name="simple_model",
            trained_on=dataset,
            description="Simple linear model"
        ),
        Metrics.create(
            accuracy=0.95,
            loss=0.05,
            f1_score=0.94
        )
    )

# Create and run pipeline
pipeline = Pipeline("simple_example", context=ctx)
pipeline.add_step(load_and_preprocess)
pipeline.add_step(train_model)

if __name__ == "__main__":
    print("🚀 Running pipeline...")
    result = pipeline.run(debug=True)

    if result.success:
        print(f"\n✅ Pipeline completed in {result.duration_seconds:.2f}s")
        print(f"Run ID: {result.run_id}")
        print(f"Check the UI at http://localhost:8080/runs/{result.run_id}")
    else:
        print("\n❌ Pipeline failed")

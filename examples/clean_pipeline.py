"""
Clean Pipeline Example - Infrastructure Agnostic.

This pipeline has NO infrastructure configuration hardcoded.
It can run on any stack configured in flowyml.yaml.

Run with:
    # Local development
    flowyml run clean_pipeline.py

    # Production on GCP
    flowyml run clean_pipeline.py --stack production

    # With GPU resources
    flowyml run clean_pipeline.py --stack production --resources gpu_training
"""

from flowyml import Pipeline, step, Dataset, Model, Metrics
import pandas as pd


# Pure pipeline logic - no infrastructure code!


@step
def load_data(data_path: str):
    """Load training data."""
    print(f"Loading data from {data_path}")

    # Simulated data loading
    df = pd.DataFrame(
        {
            "feature1": range(1000),
            "feature2": range(1000, 2000),
            "label": [i % 2 for i in range(1000)],
        },
    )

    return Dataset.create(
        data=df,
        name="training_data",
        rows=len(df),
        cols=len(df.columns),
    )


@step
def preprocess(dataset: Dataset):
    """Preprocess data."""
    df = dataset.data

    # Preprocessing logic
    train_df = df.iloc[:800]
    val_df = df.iloc[800:]

    return {
        "train": Dataset.create(data=train_df, name="train_data", parent=dataset),
        "val": Dataset.create(data=val_df, name="val_data", parent=dataset),
    }


@step
def train_model(datasets: dict):
    """Train ML model."""
    train_data = datasets["train"].data
    print(f"Training on {len(train_data)} samples")

    # Simulated training
    model_weights = {"accuracy": 0.95}

    return Model.create(
        data=model_weights,
        name="trained_model",
        framework="sklearn",
        parent=datasets["train"],
    )


@step
def evaluate(model: Model, datasets: dict):
    """Evaluate model."""
    val_data = datasets["val"].data
    print("Evaluating model...")

    return Metrics.create(
        accuracy=0.94,
        precision=0.93,
        recall=0.95,
        name="val_metrics",
        parent=model,
    )


# Create pipeline - notice NO stack configuration!
pipeline = Pipeline("clean_ml_pipeline")
pipeline.add_step(load_data)
pipeline.add_step(preprocess)
pipeline.add_step(train_model)
pipeline.add_step(evaluate)


if __name__ == "__main__":
    # For programmatic execution (optional)
    # Stack is still configured externally via flowyml.yaml or CLI
    result = pipeline.run(context={"data_path": "data/train.csv"})
    print(f"✅ Pipeline completed: {result}")

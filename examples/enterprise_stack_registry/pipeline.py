"""Example: Enterprise Stack Registry with FlowyML.

This pipeline demonstrates how the same pipeline code runs on different
stacks based on environment configuration.
"""
from flowyml import Pipeline, step


@step
def load_data():
    """Load the churn dataset."""
    # In a real project, this would load from a database or file
    import random

    random.seed(42)
    data = {
        "features": [[random.random() for _ in range(10)] for _ in range(100)],
        "labels": [random.choice([0, 1]) for _ in range(100)],
    }
    return data


@step
def preprocess(data):
    """Preprocess the dataset."""
    # Simple normalization
    features = data["features"]
    labels = data["labels"]
    return {"features": features, "labels": labels, "preprocessed": True}


@step
def train_model(data):
    """Train a model."""
    # Simulate training
    model = {"type": "logistic_regression", "accuracy": 0.85, "trained": True}
    return model


@step
def evaluate(model):
    """Evaluate the model."""
    metrics = {
        "accuracy": model.get("accuracy", 0),
        "precision": 0.82,
        "recall": 0.79,
        "f1": 0.80,
    }
    return metrics


def build_pipeline():
    """Build the training pipeline."""
    pipe = Pipeline("churn-training", project_name="churn-modeling")
    pipe.add_step(load_data)
    pipe.add_step(preprocess)
    pipe.add_step(train_model)
    pipe.add_step(evaluate)
    return pipe


if __name__ == "__main__":
    import sys

    pipe = build_pipeline()

    # Determine environment from CLI args or default
    env = sys.argv[1] if len(sys.argv) > 1 else None

    if env:
        print(f"Running on environment: {env}")
        result = pipe.run(env=env)
    else:
        print("Running on default (local) stack")
        result = pipe.run()

    print(f"Pipeline completed: {result.status}")

"""
Example: Complete ML Training Pipeline on GCP.

This example demonstrates running a full machine learning training
pipeline on Google Cloud Platform using Vertex AI.
"""

from flowyml import Pipeline, step, Dataset, Model, Metrics
from flowyml.stacks.gcp import GCPStack
from flowyml.stacks.components import ResourceConfig, DockerConfig
from flowyml.stacks.registry import StackRegistry
import pandas as pd

# Setup GCP stack
gcp_stack = GCPStack(
    name="ml-training",
    project_id="your-gcp-project",
    region="us-central1",
    bucket_name="your-artifacts-bucket",
    registry_uri="gcr.io/your-gcp-project",
)

# Register stack
registry = StackRegistry()
registry.register_stack(gcp_stack, set_active=True)

# Define compute resources for training
train_resources = ResourceConfig(
    cpu="8",
    memory="32Gi",
    gpu="nvidia-tesla-v100",
    gpu_count=2,
    machine_type="n1-highmem-8",
)

# Define Docker configuration
train_docker = DockerConfig(
    image="gcr.io/your-project/ml-training:v1",
    requirements=[
        "tensorflow>=2.12.0",
        "scikit-learn>=1.0.0",
        "pandas>=2.0.0",
    ],
    env_vars={
        "TF_FORCE_GPU_ALLOW_GROWTH": "true",
        "PYTHONUNBUFFERED": "1",
    },
)


# Pipeline steps
@step
def load_data(data_path: str):
    """Load training data from GCS."""
    print(f"Loading data from {data_path}")

    # In real scenario, load from GCS
    # df = pd.read_csv(data_path)

    # Simulated data
    df = pd.DataFrame(
        {
            "feature1": range(1000),
            "feature2": range(1000),
            "label": [i % 2 for i in range(1000)],
        },
    )

    return Dataset.create(
        data=df,
        name="training_data",
        rows=len(df),
        cols=len(df.columns),
        source=data_path,
    )


@step
def preprocess_data(dataset: Dataset):
    """Preprocess and split data."""
    df = dataset.data

    # Preprocessing logic
    # ... feature engineering, scaling, etc.

    train_df = df.iloc[:800]
    val_df = df.iloc[800:]

    train_dataset = Dataset.create(
        data=train_df,
        name="train_dataset",
        parent=dataset,
        split="train",
    )

    val_dataset = Dataset.create(
        data=val_df,
        name="val_dataset",
        parent=dataset,
        split="validation",
    )

    return {"train": train_dataset, "val": val_dataset}


@step
def train_model(datasets: dict):
    """Train machine learning model."""
    train_data = datasets["train"].data
    val_data = datasets["val"].data

    print(f"Training on {len(train_data)} samples")

    # Simulated training
    # In real scenario, train TensorFlow/PyTorch model
    model_weights = {"layer1": [1, 2, 3], "layer2": [4, 5, 6]}

    return Model.create(
        data=model_weights,
        name="trained_model",
        framework="tensorflow",
        accuracy=0.95,
        parent=datasets["train"],
    )


@step
def evaluate_model(model: Model, datasets: dict):
    """Evaluate model on validation set."""
    val_data = datasets["val"].data

    print("Evaluating model...")

    # Simulated evaluation
    accuracy = 0.94
    precision = 0.93
    recall = 0.95

    return Metrics.create(
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=2 * (precision * recall) / (precision + recall),
        name="validation_metrics",
        parent=model,
    )


@step
def save_model(model: Model):
    """Save model to model registry."""
    print(f"Saving model {model.name} to registry")
    # Model saving logic
    return {"model_uri": f"gs://models/{model.name}/v1"}


# Create pipeline
pipeline = Pipeline(
    "ml_training_pipeline",
    stack=gcp_stack,
)

# Add steps
pipeline.add_step(load_data)
pipeline.add_step(preprocess_data)
pipeline.add_step(train_model)
pipeline.add_step(evaluate_model)
pipeline.add_step(save_model)

if __name__ == "__main__":
    # Run pipeline on GCP
    print("Running ML training pipeline on GCP...")
    print(f"Stack: {gcp_stack.name}")
    print(f"Region: {gcp_stack.region}")

    result = pipeline.run(
        context={"data_path": "gs://your-bucket/train_data.csv"},
        resources=train_resources,
        docker_config=train_docker,
    )

    print("\nPipeline completed successfully!")
    print(f"Results: {result}")

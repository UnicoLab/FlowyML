"""
Comprehensive flowyml Pipeline Showcase.

This example demonstrates the core features of FlowyML for production pipelines:
- Execution Grouping: Bundling steps for resource efficiency.
- Conditional Execution: Skipping steps based on context parameters.
- Logical Branching (If): Decision making based on step outputs.
- Asset-Centric Design: Using Dataset and Metrics for UI observability.
- Context Injection: Seamless parameter passing.
- Error Resilience: Automatic retries for flaky steps.

Scenario: A Fraud Detection Pipeline that only deploys if performance is high.
"""

import time
import random
import numpy as np
from flowyml import Pipeline, step, context, If, Dataset, Metrics

# 1. Define Context (Parameters)
ctx = context(
    data_source="s3://fraud-data/raw",
    model_type="random_forest",
    threshold=0.85,
    enable_deep_validation=True,
    retry_count=2,
)

# 2. Define Steps


@step(outputs=["data/raw"], execution_group="preprocessing")
def ingest_data(data_source: str):
    """Ingest raw data from source."""
    print(f"📥 Ingesting data from {data_source}...")
    time.sleep(1)
    return Dataset.create(
        data={"raw_records": 1000},
        name="raw_fraud_data",
    )


@step(inputs=["data/raw"], outputs=["data/processed"], execution_group="preprocessing")
def process_features(raw_data: Dataset):
    """Clean and transform features."""
    print("🧹 Cleaning and transforming features...")
    time.sleep(1.5)
    return Dataset.create(
        data={
            "features": np.random.randn(1000, 10).tolist(),
            "labels": np.random.randint(0, 2, 1000).tolist(),
        },
        name="processed_features",
    )


@step(
    inputs=["data/processed"],
    outputs=["data/validated"],
    condition=lambda enable_deep_validation: enable_deep_validation,
)
def validate_data(data: Dataset):
    """Perform deep validation (only runs if enabled in context)."""
    print("🔍 Performing deep data validation...")
    time.sleep(2)
    return data


@step(
    inputs=["data/validated"],
    outputs=["model/trained"],
    retry=2,
)
def train_model(data: Dataset, model_type: str):
    """Train the fraud detection model."""
    print(f"🧠 Training {model_type} model...")
    # Simulate a flaky step that might need retry
    if random.random() < 0.2:
        print("⚠️ Training failed unexpectedly, retrying...")
        raise RuntimeError("GPU OOM (Simulated)")

    time.sleep(3)
    # Return model metadata and performance
    accuracy = 0.7 + (random.random() * 0.25)  # Random accuracy between 0.7 and 0.95
    return {"model_id": f"fraud_{int(time.time())}", "accuracy": accuracy}


@step(inputs=["model/trained"], outputs=["metrics/eval"])
def evaluate_model(trained_model: dict):
    """Generate final evaluation metrics."""
    print("📈 Evaluating model performance...")
    time.sleep(1)
    acc = trained_model["accuracy"]
    return Metrics.create(
        accuracy=acc,
        precision=acc * 0.9,
        recall=acc * 0.85,
        name="fraud_model_metrics",
        properties={"model_id": trained_model["model_id"]},
    )


@step(inputs=["model/trained"], outputs=["deploy/status"])
def deploy_to_production(trained_model: dict):
    """Deploy the model (only if performance threshold is met)."""
    print(f"🚀 Deploying model {trained_model['model_id']} to production!")
    time.sleep(1)
    return {"status": "deployed", "timestamp": time.time()}


# 3. Build & Run Pipeline


def main():
    # Initialize Pipeline
    pipeline = Pipeline("fraud_detection_demo", context=ctx)

    # Add linear steps
    pipeline.add_step(ingest_data)
    pipeline.add_step(process_features)
    pipeline.add_step(validate_data)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_model)

    # Add Branching Logic
    # We only deploy if accuracy > threshold defined in context
    def check_deployment_condition(ctx):
        # Access previous step output via ctx.steps
        eval_result = ctx.steps["evaluate_model"].outputs["metrics/eval"]
        accuracy = eval_result.data["accuracy"]
        threshold = ctx.params["threshold"]

        print(f"Checking deployment: Accuracy {accuracy:.4f} vs Threshold {threshold}")
        return accuracy >= threshold

    pipeline.add_control_flow(
        If(
            condition=check_deployment_condition,
            then_step=deploy_to_production,
        ),
    )

    print("\n" + "=" * 80)
    print("🌊 STARTING COMPREHENSIVE FLOWYML SHOWCASE")
    print("=" * 80 + "\n")

    # Run!
    # auto_start_ui=False for this environment (run 'flowyml go' separately if needed)
    result = pipeline.run(auto_start_ui=False)

    print("\n" + "=" * 80)
    if result.success:
        print("✅ Pipeline Completed Successfully")
        metrics = result.outputs["metrics/eval"].data
        print(f"Final Metrics: {metrics}")

        if "deploy_to_production" in result.step_results:
            print("🚀 STATUS: Model DEPLOYED to production")
        else:
            print("🛑 STATUS: Model NOT DEPLOYED (Did not meet threshold)")
    else:
        print("❌ Pipeline Failed")
    print("=" * 80)


if __name__ == "__main__":
    main()

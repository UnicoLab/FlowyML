"""
Flowy Comprehensive Demo Pipeline.

This example demonstrates the core features of Flowy:
- Pipeline creation and execution
- Step definition with @step decorator
- Automatic context injection
- Asset management (Datasets, Models, Metrics)
- Caching (Code hash and Input hash)
- Conditional execution
- Monitoring and Alerts

Usage:
    1. Ensure the UI server is running (optional but recommended):
       $ flowy ui start

    2. Run this script:
       $ python examples/demo_pipeline.py

    3. View the results in the UI at http://localhost:8080
"""

import time
import random
import logging
from typing import Tuple, Dict, Any

from flowy import Pipeline, step, context
from flowy.assets.dataset import Dataset
from flowy.assets.model import Model
from flowy.assets.metrics import Metrics
from flowy.assets.featureset import FeatureSet
from flowy.monitoring.alerts import alert_manager, AlertLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flowy.demo")

# 1. Define Context
# These parameters will be automatically injected into steps that request them
ctx = context(
    # Data parameters
    data_source="s3://demo-bucket/churn-data",
    test_size=0.2,
    
    # Training parameters
    learning_rate=0.01,
    n_estimators=100,
    max_depth=5,
    
    # Deployment thresholds
    min_accuracy=0.85,
    should_deploy=True,  # Flag for conditional execution
    
    # Metadata
    experiment_name="churn_prediction_v1",
    owner="data-team"
)

# 2. Define Steps

@step(outputs=["data/raw"], cache="code_hash")
def load_data(data_source: str) -> Dataset:
    """Simulate loading data from a source."""
    logger.info(f"Loading data from {data_source}...")
    time.sleep(1.5)  # Simulate I/O
    
    # Create a Dataset asset
    return Dataset(
        name="churn_raw",
        uri=data_source,
        metadata={"rows": 10000, "columns": 20}
    )

@step(inputs=["data/raw"], outputs=["data/features"], cache="input_hash")
def preprocess(raw_data: Dataset, test_size: float) -> FeatureSet:
    """Simulate data preprocessing and feature engineering."""
    logger.info(f"Preprocessing {raw_data.name} with test_size={test_size}...")
    time.sleep(2.0)  # Simulate processing
    
    # Simulate some data quality check
    if random.random() < 0.1:
        alert_manager.alert(
            "Data quality warning: Null values detected in 'age' column", 
            level=AlertLevel.WARNING
        )
    
    return FeatureSet(
        name="churn_features",
        uri="s3://demo-bucket/features/v1",
        metadata={
            "features": ["age", "tenure", "balance", "products"],
            "test_size": test_size
        }
    )

@step(inputs=["data/features"], outputs=["model/candidate", "metrics/training"])
def train_model(
    features: FeatureSet, 
    learning_rate: float, 
    n_estimators: int,
    max_depth: int
) -> Tuple[Model, Metrics]:
    """Simulate model training."""
    logger.info(f"Training model with lr={learning_rate}, n_estimators={n_estimators}...")
    time.sleep(3.0)  # Simulate training
    
    # Simulate training metrics
    accuracy = 0.82 + (random.random() * 0.1)  # Random accuracy between 0.82 and 0.92
    loss = 0.5 - (accuracy * 0.4)
    
    model = Model(
        name="churn_classifier",
        uri="s3://demo-bucket/models/v1",
        metadata={
            "algorithm": "RandomForest",
            "hyperparameters": {
                "learning_rate": learning_rate,
                "n_estimators": n_estimators,
                "max_depth": max_depth
            }
        }
    )
    
    metrics = Metrics(
        name="training_metrics",
        values={
            "accuracy": accuracy,
            "loss": loss,
            "f1_score": accuracy - 0.02
        }
    )
    
    return model, metrics

@step(inputs=["model/candidate", "metrics/training"], outputs=["metrics/evaluation"])
def evaluate_model(model: Model, training_metrics: Metrics, min_accuracy: float) -> Metrics:
    """Evaluate model and check against thresholds."""
    logger.info(f"Evaluating model {model.name}...")
    time.sleep(1.0)
    
    accuracy = training_metrics.values["accuracy"]
    logger.info(f"Model accuracy: {accuracy:.4f} (Threshold: {min_accuracy})")
    
    if accuracy < min_accuracy:
        alert_manager.alert(
            f"Model accuracy {accuracy:.4f} is below threshold {min_accuracy}",
            level=AlertLevel.WARNING
        )
    
    return Metrics(
        name="eval_metrics",
        values={
            "accuracy": accuracy,
            "passed_threshold": accuracy >= min_accuracy
        }
    )

# Conditional deployment: only runs if 'should_deploy' context param is True
@step(
    inputs=["model/candidate"], 
    condition=lambda should_deploy: should_deploy
)
def deploy_model(model: Model, min_accuracy: float):
    """Simulate model deployment."""
    logger.info(f"Deploying model {model.name} to production...")
    time.sleep(2.0)
    
    # Simulate deployment success/failure
    if random.random() < 0.9:
        logger.info("Deployment successful! 🚀")
        alert_manager.alert(f"Model {model.name} deployed successfully", level=AlertLevel.INFO)
    else:
        logger.error("Deployment failed!")
        alert_manager.alert("Deployment failed due to timeout", level=AlertLevel.ERROR)
        raise RuntimeError("Deployment timeout")

# 3. Build and Run Pipeline

def main():
    print("🌊 Initializing Flowy Demo Pipeline...")
    
    # Create pipeline with context
    pipeline = Pipeline("churn_prediction_demo", context=ctx)
    
    # Add steps (order doesn't matter, Flowy builds the DAG based on inputs/outputs)
    pipeline.add_step(load_data)
    pipeline.add_step(preprocess)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_model)
    pipeline.add_step(deploy_model)
    
    # Run the pipeline
    # Note: The UI URL will be printed automatically when the pipeline starts
    try:
        result = pipeline.run()
        
        if result.success:
            print("\n✅ Pipeline finished successfully!")
            print(f"Duration: {result.duration_seconds:.2f}s")
            
            # Access outputs
            metrics = result.outputs.get("metrics/evaluation")
            if metrics:
                print(f"Final Accuracy: {metrics.values['accuracy']:.4f}")
        else:
            print("\n❌ Pipeline failed!")
            
    except Exception as e:
        print(f"\n❌ Pipeline execution error: {e}")

if __name__ == "__main__":
    main()

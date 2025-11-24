"""
Example: Using Flowy with Real-Time UI Monitoring

This example demonstrates how to run a pipeline that integrates
with the Flowy UI for real-time monitoring of execution.

To use this example:
1. Install Flowy with UI support: pip install "flowy[ui]"
2. Build the frontend: cd flowy/ui/frontend && npm install && npm run build
3. Start the UI server: flowy ui start --open-browser
4. Run this script: python examples/ui_integration_example.py
5. Watch the pipeline execution in the UI at http://localhost:8080
"""

from flowy import Pipeline, step, context
from flowy.ui import is_ui_running, get_ui_url, get_run_url
import time
import random


# Define context with experiment parameters
ctx = context(
    learning_rate=0.001,
    epochs=10,
    batch_size=32,
    model_type="neural_network",
    dataset_name="cifar10",
)


@step(outputs=["data/raw"])
def load_data(dataset_name: str):
    """Load and prepare dataset."""
    print(f"📥 Loading dataset: {dataset_name}")
    time.sleep(1)  # Simulate data loading
    
    data = {
        "name": dataset_name,
        "samples": 50000,
        "features": 3072,  # 32x32x3
        "classes": 10,
    }
    
    print(f"✅ Loaded {data['samples']} samples")
    return data


@step(inputs=["data/raw"], outputs=["data/processed"])
def preprocess_data(raw_data):
    """Preprocess and augment data."""
    print(f"🔧 Preprocessing {raw_data['name']}...")
    time.sleep(1.5)  # Simulate preprocessing
    
    processed = {
        **raw_data,
        "normalized": True,
        "augmented": True,
        "split": {"train": 40000, "val": 10000},
    }
    
    print(f"✅ Data preprocessed and split")
    return processed


@step(inputs=["data/processed"], outputs=["model/trained", "metrics/training"])
def train_model(
    processed_data,
    learning_rate: float,
    epochs: int,
    batch_size: int,
    model_type: str,
):
    """Train the model and track metrics."""
    print(f"🚀 Training {model_type} model...")
    print(f"   Learning rate: {learning_rate}")
    print(f"   Batch size: {batch_size}")
    print(f"   Epochs: {epochs}")
    
    # Simulate training with improving metrics
    metrics_history = []
    for epoch in range(1, epochs + 1):
        # Simulate training progress
        time.sleep(0.5)
        
        # Generate realistic-looking metrics
        loss = 2.5 * (0.8 ** epoch) + random.uniform(-0.1, 0.1)
        accuracy = min(0.95, 0.3 + (epoch / epochs) * 0.65 + random.uniform(-0.02, 0.02))
        
        metrics = {
            "epoch": epoch,
            "train_loss": round(loss, 4),
            "train_accuracy": round(accuracy, 4),
            "learning_rate": learning_rate,
        }
        
        metrics_history.append(metrics)
        print(f"   Epoch {epoch}/{epochs}: loss={metrics['train_loss']:.4f}, acc={metrics['train_accuracy']:.4f}")
    
    # Final model
    model = {
        "type": model_type,
        "architecture": "ResNet18",
        "parameters": 11_173_962,
        "trained_epochs": epochs,
        "final_loss": metrics_history[-1]["train_loss"],
        "final_accuracy": metrics_history[-1]["train_accuracy"],
    }
    
    print(f"✅ Model trained successfully!")
    print(f"   Final accuracy: {model['final_accuracy']:.2%}")
    
    return model, {"history": metrics_history}


@step(inputs=["model/trained", "data/processed"], outputs=["metrics/evaluation"])
def evaluate_model(trained_model, processed_data):
    """Evaluate model on validation set."""
    print(f"📊 Evaluating model on validation set...")
    time.sleep(1)  # Simulate evaluation
    
    # Simulate evaluation metrics
    val_metrics = {
        "val_loss": trained_model["final_loss"] + 0.05,
        "val_accuracy": trained_model["final_accuracy"] - 0.02,
        "precision": 0.93,
        "recall": 0.92,
        "f1_score": 0.925,
        "validation_samples": processed_data["split"]["val"],
    }
    
    print(f"✅ Evaluation complete!")
    print(f"   Validation accuracy: {val_metrics['val_accuracy']:.2%}")
    print(f"   F1 Score: {val_metrics['f1_score']:.3f}")
    
    return val_metrics


@step(inputs=["model/trained", "metrics/evaluation"], outputs=["model/exported"])
def export_model(trained_model, eval_metrics):
    """Export model for deployment."""
    print(f"📦 Exporting model...")
    time.sleep(0.5)
    
    exported = {
        **trained_model,
        "validation_metrics": eval_metrics,
        "format": "onnx",
        "quantized": False,
        "deployment_ready": True,
        "export_timestamp": time.time(),
    }
    
    print(f"✅ Model exported successfully!")
    print(f"   Format: {exported['format']}")
    print(f"   Deployment ready: {exported['deployment_ready']}")
    
    return exported


def main():
    """Main function to run the pipeline with UI integration."""
    
    print("=" * 70)
    print("🌊 Flowy Pipeline with UI Integration Example")
    print("=" * 70)
    
    # Check if UI is running
    print("\n🔍 Checking UI server status...")
    if is_ui_running():
        ui_url = get_ui_url()
        print(f"✅ UI server is running at: {ui_url}")
        print(f"   You can monitor this pipeline in real-time!")
    else:
        print("⚠️  UI server is not running.")
        print("   Start it with: flowy ui start --open-browser")
        print("   The pipeline will still run, but without UI monitoring.")
    
    print("\n" + "=" * 70)
    
    # Create pipeline
    pipeline = Pipeline("training_pipeline", context=ctx)
    
    # Add steps in order
    pipeline.add_step(load_data)
    pipeline.add_step(preprocess_data)
    pipeline.add_step(train_model)
    pipeline.add_step(evaluate_model)
    pipeline.add_step(export_model)
    
    print("\n📋 Pipeline Configuration:")
    print(f"   Name: {pipeline.name}")
    print(f"   Steps: {len(pipeline._steps)}")
    print(f"   Context parameters: {len(ctx._params)}")
    
    # Run the pipeline
    print("\n🚀 Starting pipeline execution...")
    print("=" * 70 + "\n")
    
    try:
        result = pipeline.run(debug=True)
        
        print("\n" + "=" * 70)
        print("✅ Pipeline completed successfully!")
        print("=" * 70)
        
        # Display results
        print("\n📊 Results Summary:")
        if hasattr(result, 'artifacts'):
            for artifact_name, artifact_value in result.artifacts.items():
                print(f"   {artifact_name}: {type(artifact_value).__name__}")
        
        # Show UI link if available
        if is_ui_running():
            ui_url = get_ui_url()
            if hasattr(result, 'run_id'):
                run_url = get_run_url(result.run_id)
                print(f"\n🔗 View this run in the UI:")
                print(f"   {run_url}")
            else:
                print(f"\n🔗 View in the UI:")
                print(f"   {ui_url}")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ Pipeline failed: {e}")
        print("=" * 70)
        raise


if __name__ == "__main__":
    main()

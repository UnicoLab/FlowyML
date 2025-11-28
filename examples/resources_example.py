"""Example: Using Resource Specifications

This example demonstrates how to specify CPU, GPU, memory, and other resources
for pipeline steps in UniFlow, with automatic translation to orchestrator-specific formats.
"""

from uniflow.core import step
from uniflow.core.resources import ResourceRequirements, GPUConfig, NodeAffinity


# Example 1: Simple CPU and Memory Specification
@step(resources=ResourceRequirements(cpu="2", memory="4Gi"))
def preprocess_data(raw_data):
    """Preprocess data with 2 CPU cores and 4GB memory."""
    # Data preprocessing logic
    processed = raw_data.lower().strip()
    return processed


# Example 2: GPU Training Step
@step(
    resources=ResourceRequirements(
        cpu="4",
        memory="16Gi",
        gpu=GPUConfig(gpu_type="nvidia-tesla-v100", count=2, memory="16Gi"),
    ),
)
def train_model_on_gpu(processed_data):
    """Train model using 2 V100 GPUs."""
    # Training logic would use GPU here
    # In real implementation: import torch, use torch.cuda, etc.
    model = "trained_model"
    return model


# Example 3: Large Memory Processing
@step(resources=ResourceRequirements(cpu="8", memory="64Gi", storage="500Gi"))
def process_large_dataset(data):
    """Process very large dataset requiring high memory."""
    # Large data processing
    result = f"processed_{len(data)}_records"
    return result


# Example 4: Node Affinity for Specific Hardware
@step(
    resources=ResourceRequirements(
        cpu="16",
        memory="128Gi",
        gpu=GPUConfig(gpu_type="nvidia-a100", count=8, memory="80Gi"),
        node_affinity=NodeAffinity(
            required={
                "cloud.google.com/gke-nodepool": "gpu-pool",
                "gpu": "true",
            },
            preferred={"zone": "us-central1-a"},
            tolerations=[
                {"key": "nvidia.com/gpu", "operator": "Exists"},
                {"key": "dedicated", "value": "gpu-training", "effect": "NoSchedule"},
            ],
        ),
    ),
)
def distributed_training(dataset):
    """Distributed training on specific GPU nodes."""
    # Distributed training logic
    return "distributed_model"


# Example 5: Backward Compatible Dict Format
@step(resources={"cpu": "1", "memory": "2Gi"})
def lightweight_task():
    """Lightweight task using dict format (backward compatible)."""
    return "result"


def ml_training_pipeline():
    """Complete ML pipeline with resource specifications."""
    # Preprocessing with moderate resources
    raw = "RAW DATA"
    processed = preprocess_data(raw)

    # Training with GPU resources
    model = train_model_on_gpu(processed)

    return model


def resource_intensive_pipeline():
    """Pipeline demonstrating various resource configurations."""
    data = "large_dataset"

    # Step 1: Process with high memory
    processed = process_large_dataset(data)

    # Step 2: Distributed training on specific nodes
    model = distributed_training(processed)

    # Step 3: Lightweight post-processing
    finalized = lightweight_task()

    return model, finalized


if __name__ == "__main__":
    print("=" * 60)
    print("UniFlow Resource Specification Example")
    print("=" * 60)

    print("\n1. Running simple training pipeline...")
    result = ml_training_pipeline()
    print(f"   Result: {result}")

    print("\n2. Running resource-intensive pipeline...")
    model, final = resource_intensive_pipeline()
    print(f"   Model: {model}, Final: {final}")

    print("\n3. Demonstrating resource inspection...")
    # Demonstrate resource specification on steps
    steps = [
        preprocess_data,
        train_model_on_gpu,
        process_large_dataset,
        distributed_training,
        lightweight_task,
    ]

    for step_obj in steps:
        print(f"\n   Step: {step_obj.name}")
        if step_obj.resources:
            if isinstance(step_obj.resources, ResourceRequirements):
                print(f"     CPU: {step_obj.resources.cpu}")
                print(f"     Memory: {step_obj.resources.memory}")
                if step_obj.resources.has_gpu():
                    print(f"     GPUs: {step_obj.resources.get_gpu_count()}")
            else:
                print(f"     Resources (dict): {step_obj.resources}")
        else:
            print("     No resource requirements")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

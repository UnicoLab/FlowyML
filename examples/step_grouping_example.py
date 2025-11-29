"""Example: Using Step Grouping in flowyml

This example demonstrates how to use execution groups to run multiple steps
in the same Docker container or remote executor, optimizing resource usage
and reducing container overhead.
"""

from flowyml.core import step, Pipeline
from flowyml.core.resources import ResourceRequirements, GPUConfig


print("=" * 70)
print("flowyml Step Grouping Example")
print("=" * 70)


# Example 1: Basic Step Grouping
# -------------------------------
print("\n1. Basic Step Grouping - Data Preprocessing Pipeline")
print("-" * 70)


@step(outputs=["raw_data"], execution_group="preprocessing")
def load_raw_data():
    """Load raw data - runs in preprocessing group."""
    print("   [Group: preprocessing] Loading raw data...")
    return {"records": 1000, "format": "csv"}


@step(inputs=["raw_data"], outputs=["clean_data"], execution_group="preprocessing")
def clean_data(raw_data: dict):
    """Clean data - runs in same container as load_raw_data."""
    print(f"   [Group: preprocessing] Cleaning {raw_data['records']} records...")
    return {**raw_data, "status": "cleaned"}


@step(inputs=["clean_data"], outputs=["transformed_data"], execution_group="preprocessing")
def transform_data(clean_data: dict):
    """Transform data - runs in same container as previous steps."""
    print("   [Group: preprocessing] Transforming data...")
    return {**clean_data, "status": "transformed"}


@step(inputs=["transformed_data"], outputs=["report"])
def generate_report(transformed_data: dict):
    """Generate report - runs separately (no group)."""
    print("   [Standalone] Generating report...")
    return f"Report: {transformed_data['records']} records processed"


# Build and run pipeline
pipeline1 = Pipeline("preprocessing_pipeline")
pipeline1.add_step(load_raw_data)
pipeline1.add_step(clean_data)
pipeline1.add_step(transform_data)
pipeline1.add_step(generate_report)

result1 = pipeline1.run()

print("\n✓ Pipeline completed successfully!")
print(f"  Result: {result1.outputs['report']}")
print(f"  Groups created: {len(pipeline1.step_groups)}")
if pipeline1.step_groups:
    group = pipeline1.step_groups[0]
    print(f"  Group '{group.group_name}' contains {len(group.steps)} steps:")
    for s in group.steps:
        print(f"    - {s.name}")


# Example 2: Resource Aggregation
# --------------------------------
print("\n\n2. Resource Aggregation - ML Training Pipeline")
print("-" * 70)


@step(
    outputs=["dataset"],
    execution_group="training",
    resources=ResourceRequirements(cpu="2", memory="4Gi"),
)
def prepare_dataset():
    """Prepare dataset with 2 CPU cores and 4GB memory."""
    print("   [Group: training, 2 CPU, 4Gi Mem] Preparing dataset...")
    return "prepared_dataset"


@step(
    inputs=["dataset"],
    outputs=["model"],
    execution_group="training",
    resources=ResourceRequirements(
        cpu="4",
        memory="8Gi",
        gpu=GPUConfig(gpu_type="nvidia-v100", count=2),
    ),
)
def train_model(dataset: str):
    """Train model with 4 CPU cores, 8GB memory, and 2 V100 GPUs."""
    print(f"   [Group: training, 4 CPU, 8Gi Mem, 2x V100] Training model on {dataset}...")
    return "trained_model_v1"


@step(
    inputs=["model"],
    outputs=["evaluation"],
    execution_group="training",
    resources=ResourceRequirements(
        cpu="2",
        memory="2Gi",
        gpu=GPUConfig(gpu_type="nvidia-a100", count=1),
    ),
)
def evaluate_model(model: str):
    """Evaluate model with A100 GPU (will be upgraded in group)."""
    print(f"   [Group: training, 2 CPU, 2Gi Mem, 1x A100] Evaluating {model}...")
    return {"accuracy": 0.95, "model": model}


# Build and run pipeline
pipeline2 = Pipeline("training_pipeline")
pipeline2.add_step(prepare_dataset)
pipeline2.add_step(train_model)
pipeline2.add_step(evaluate_model)
pipeline2.build()

print("\n📊 Resource Aggregation Results:")
if pipeline2.step_groups:
    group = pipeline2.step_groups[0]
    res = group.aggregated_resources
    print(f"  Group '{group.group_name}' aggregated resources:")
    print(f"    CPU: {res.cpu} (max of 2, 4, 2)")
    print(f"    Memory: {res.memory} (max of 4Gi, 8Gi, 2Gi)")
    if res.gpu:
        print(f"    GPU: {res.gpu.count}x {res.gpu.gpu_type}")
        print("         (max count=2, best type=A100)")

result2 = pipeline2.run()
print(f"\n✓ Training completed: {result2.outputs['evaluation']}")


# Example 3: Mixed Grouped and Ungrouped Steps
# ---------------------------------------------
print("\n\n3. Mixed Grouped and Ungrouped Steps - Complex Workflow")
print("-" * 70)


@step(outputs=["config"])
def load_config():
    """Load configuration - standalone step."""
    print("   [Standalone] Loading configuration...")
    return {"batch_size": 32, "epochs": 10}


@step(inputs=["config"], outputs=["data"], execution_group="data_prep")
def fetch_data(config: dict):
    """Fetch data - starts data_prep group."""
    print(f"   [Group: data_prep] Fetching data with batch_size={config['batch_size']}...")
    return "raw_data"


@step(inputs=["data"], outputs=["processed"], execution_group="data_prep")
def process_data(data: str):
    """Process data - continues in data_prep group."""
    print(f"   [Group: data_prep] Processing {data}...")
    return "processed_data"


@step(inputs=["config", "processed"], outputs=["model"], execution_group="training")
def train(config: dict, processed: str):
    """Train model - separate training group."""
    print(f"   [Group: training] Training for {config['epochs']} epochs on {processed}...")
    return "final_model"


@step(inputs=["model"], outputs=["deployed"])
def deploy(model: str):
    """Deploy model - standalone step."""
    print(f"   [Standalone] Deploying {model}...")
    return f"{model}_deployed"


# Build and run pipeline
pipeline3 = Pipeline("complex_pipeline")
pipeline3.add_step(load_config)
pipeline3.add_step(fetch_data)
pipeline3.add_step(process_data)
pipeline3.add_step(train)
pipeline3.add_step(deploy)
pipeline3.build()

print("\n📦 Execution Plan:")
print(f"  Total steps: {len(pipeline3.steps)}")
print(f"  Groups created: {len(pipeline3.step_groups)}")
for i, group in enumerate(pipeline3.step_groups, 1):
    print(f"  Group {i}: '{group.group_name}' with {len(group.steps)} steps")
    for s in group.steps:
        print(f"    - {s.name}")

result3 = pipeline3.run()
print(f"\n✓ Pipeline completed: {result3.outputs['deployed']}")


# Example 4: Demonstrating Non-Consecutive Grouping
# --------------------------------------------------
print("\n\n4. Non-Consecutive Steps (Auto-Split into Subgroups)")
print("-" * 70)


@step(outputs=["a"], execution_group="same_name")
def step_a():
    """First step in group."""
    print("   [Group: same_name] Step A executing...")
    return "a"


@step(outputs=["x"])
def step_x():
    """Intermediate ungrouped step."""
    print("   [Standalone] Step X executing...")
    return "x"


@step(inputs=["x"], outputs=["b"], execution_group="same_name")
def step_b(x: str):
    """Another step with same group name, but non-consecutive."""
    print("   [Group: same_name] Step B executing...")
    return f"{x}_b"


# Build pipeline
pipeline4 = Pipeline("non_consecutive")
pipeline4.add_step(step_a)
pipeline4.add_step(step_x)
pipeline4.add_step(step_b)
pipeline4.build()

print("\n🔍 Intelligent Grouping Analysis:")
print("  Steps with 'same_name' group: 2 (step_a, step_b)")
print("  Are they consecutive? No (step_x is in between)")
print(f"  Groups created: {len(pipeline4.step_groups)}")
for i, group in enumerate(pipeline4.step_groups, 1):
    print(f"  Group {i}: '{group.group_name}' with steps: {[s.name for s in group.steps]}")

result4 = pipeline4.run()
print("\n✓ Pipeline completed successfully!")


# Summary
# -------
print("\n\n" + "=" * 70)
print("Summary: Step Grouping Benefits")
print("=" * 70)
print(
    """
✓ EFFICIENCY: Multiple steps run in the same Docker container/environment
✓ RESOURCE OPTIMIZATION: Resources are automatically aggregated (max CPU, memory)
✓ CLEAN SEPARATION: Maintain clear step boundaries without monolithic functions
✓ SMART ANALYSIS: Non-consecutive steps are automatically split into subgroups
✓ FLEXIBLE: Mix grouped and ungrouped steps in the same pipeline

Next Steps:
- Use execution_group parameter in your @step decorators
- Let flowyml handle the rest - no complex configuration needed!
- Check pipeline.step_groups after build() to see grouping results
""",
)
print("=" * 70)

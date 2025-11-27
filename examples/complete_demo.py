"""Comprehensive example demonstrating all UniFlow features."""

import numpy as np
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from uniflow import (  # noqa: E402
    Pipeline,
    step,
    context,
    PipelineScheduler,
    configure_notifications,
    get_notifier,
    ModelLeaderboard,
    # Templates
    create_from_template,
    list_templates,
    # Caching
    ContentBasedCache,
    memoize,
    # Keras
    detect_drift,
    # Versioning & Projects
    VersionedPipeline,
    Project,
)

# ============================================================================
# PART 1: Basic Pipeline with Context
# ============================================================================

print("=" * 80)
print("PART 1: Basic Pipeline with Context")
print("=" * 80)

ctx = context(
    learning_rate=0.001,
    epochs=5,
    batch_size=32,
)

pipeline = Pipeline("basic_ml_pipeline", context=ctx)


@step(outputs=["training_data", "test_data"])
def load_data():
    """Load sample data."""
    print("  📊 Loading data...")
    X_train = np.random.rand(1000, 10)
    y_train = np.random.randint(0, 2, 1000)
    X_test = np.random.rand(200, 10)
    y_test = np.random.randint(0, 2, 200)
    return (X_train, y_train), (X_test, y_test)


@step(inputs=["training_data"], outputs=["model", "history"])
def train_model(training_data, learning_rate: float, epochs: int):
    """Train a simple model."""
    print(f"  🎯 Training model (lr={learning_rate}, epochs={epochs})...")
    X_train, y_train = training_data
    # Simulate training
    time.sleep(0.5)
    model = {"weights": np.random.rand(10), "bias": 0.1}
    history = {"loss": [0.5, 0.4, 0.3, 0.2, 0.1]}
    return model, history


@step(inputs=["model", "test_data"], outputs=["metrics"])
def evaluate_model(model, test_data):
    """Evaluate the model."""
    print("  📈 Evaluating model...")
    X_test, y_test = test_data
    accuracy = np.random.rand()  # Simulate accuracy
    return {"accuracy": accuracy, "loss": 0.15}


pipeline.add_step(load_data)
pipeline.add_step(train_model)
pipeline.add_step(evaluate_model)

result = pipeline.run(debug=True)
print(f"\n✅ Pipeline completed: {result.success}")
print(f"   Metrics: {result.outputs.get('metrics')}")

# ============================================================================
# PART 2: Pipeline Versioning
# ============================================================================

print("\n" + "=" * 80)
print("PART 2: Pipeline Versioning")
print("=" * 80)

versioned_pipeline = VersionedPipeline("ml_training")
versioned_pipeline.version = "v1.0.0"

versioned_pipeline.add_step(load_data)
versioned_pipeline.add_step(train_model)

versioned_pipeline.save_version(metadata={"description": "Initial version with basic training"})

# Add evaluation step
versioned_pipeline.add_step(evaluate_model)
versioned_pipeline.version = "v1.1.0"
versioned_pipeline.save_version(metadata={"description": "Added evaluation step"})

# Compare versions
print("\n📊 Comparing versions:")
versioned_pipeline.display_comparison("v1.0.0")

# ============================================================================
# PART 3: Projects & Multi-Tenancy
# ============================================================================

print("\n" + "=" * 80)
print("PART 3: Projects & Multi-Tenancy")
print("=" * 80)

project = Project(
    name="recommendation_system",
    description="Movie recommendation ML system",
)

# Create pipeline within project
project_pipeline = project.create_pipeline("training_v1")
project_pipeline.add_step(load_data)
project_pipeline.add_step(train_model)
project_pipeline.add_step(evaluate_model)

# Run pipeline
result = project_pipeline.run()

# Get project stats
stats = project.get_stats()
print("\n📊 Project Stats:")
print(f"   Total runs: {stats['total_runs']}")
print(f"   Total artifacts: {stats['total_artifacts']}")

# ============================================================================
# PART 4: Notifications
# ============================================================================

print("\n" + "=" * 80)
print("PART 4: Notifications")
print("=" * 80)

configure_notifications(console=True)
notifier = get_notifier()

notifier.notify(
    title="Training Complete",
    message=f"Model trained successfully with accuracy: {result.outputs.get('metrics', {}).get('accuracy', 0):.2%}",
    level="success",
)

# ============================================================================
# PART 5: Model Leaderboard
# ============================================================================

print("\n" + "=" * 80)
print("PART 5: Model Leaderboard")
print("=" * 80)

leaderboard = ModelLeaderboard(metric="accuracy", higher_is_better=True)

# Add some model scores
for i in range(5):
    model_name = f"model_v{i+1}"
    run_id = f"run_{i+1}"
    score = 0.7 + np.random.rand() * 0.25  # Random accuracy between 0.7-0.95

    leaderboard.add_score(
        model_name=model_name,
        run_id=run_id,
        score=score,
        metadata={"version": f"v{i+1}"},
    )

# Display leaderboard
leaderboard.display(n=5)

# ============================================================================
# PART 6: Templates
# ============================================================================

print("\n" + "=" * 80)
print("PART 6: Pipeline Templates")
print("=" * 80)

# from uniflow import list_templates  # Moved to top

print(f"Available templates: {list_templates()}")

template_pipeline = create_from_template(
    "ml_training",
    name="template_based_training",
    data_loader=load_data,
    trainer=lambda data: train_model(data, 0.001, 5),
    evaluator=lambda model, data: evaluate_model(model, data),
)

print(f"✨ Created pipeline from template: {template_pipeline.name}")
print(f"   Steps: {[s.name for s in template_pipeline.steps]}")

# ============================================================================
# PART 7: Advanced Caching
# ============================================================================

print("\n" + "=" * 80)
print("PART 7: Advanced Caching")
print("=" * 80)

cache = ContentBasedCache()


# Use memoization decorator
@memoize(ttl_seconds=3600)
def expensive_computation(n):
    print(f"  🔄 Computing expensive operation for n={n}...")
    time.sleep(0.1)
    return n**2


# First call - computes
result1 = expensive_computation(5)
print(f"Result: {result1}")

# Second call - cached
result2 = expensive_computation(5)
print(f"Result (cached): {result2}")

# ============================================================================
# PART 8: Data Drift Detection
# ============================================================================

print("\n" + "=" * 80)
print("PART 8: Data Drift Detection")
print("=" * 80)

# Training data distribution
train_feature = np.random.normal(0, 1, 1000)

# Production data (similar distribution - no drift)
prod_feature_no_drift = np.random.normal(0, 1, 1000)

# Production data (different distribution - drift!)
prod_feature_with_drift = np.random.normal(2, 1, 1000)

# Check for drift
drift_result = detect_drift(train_feature, prod_feature_with_drift)

if drift_result["drift_detected"]:
    print("⚠️  Data drift detected!")
    print(f"   PSI: {drift_result['psi']:.4f}")
    notifier.on_drift_detected("feature_x", drift_result["psi"])
else:
    print(f"✅ No drift detected (PSI: {drift_result['psi']:.4f})")

# ============================================================================
# PART 9: Pipeline Scheduling (Demo - not started)
# ============================================================================

print("\n" + "=" * 80)
print("PART 9: Pipeline Scheduling")
print("=" * 80)

scheduler = PipelineScheduler()

# Schedule daily training at 2 AM
scheduler.schedule_daily(
    name="daily_retrain",
    pipeline_func=lambda: pipeline.run(),
    hour=2,
    minute=0,
)

# Schedule hourly data refresh
scheduler.schedule_interval(
    name="data_refresh",
    pipeline_func=lambda: print("Refreshing data..."),
    hours=1,
)

# List schedules (don't start for demo)
scheduler.list_schedules()
print("\n💡 Note: Scheduler configured but not started (use scheduler.start() to activate)")

# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 80)
print("🎉 COMPLETE DEMO FINISHED")
print("=" * 80)
print("\n✨ Features demonstrated:")
print("   ✓ Basic pipelines with context")
print("   ✓ Pipeline versioning & comparison")
print("   ✓ Projects & multi-tenancy")
print("   ✓ Notifications")
print("   ✓ Model leaderboard")
print("   ✓ Pipeline templates")
print("   ✓ Advanced caching")
print("   ✓ Data drift detection")
print("   ✓ Pipeline scheduling")
print("\n🌊 UniFlow - Next-Generation ML Pipeline Framework")

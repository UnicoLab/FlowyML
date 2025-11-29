"""
Conditional Execution Example.

Demonstrates how to use conditional steps in flowyml pipelines.

Usage:
    $ python examples/conditional_pipeline.py
"""

from flowyml import Pipeline, step, context

# Define context with a flag for conditional execution
ctx = context(
    data_quality_threshold=0.9,
    enable_advanced_features=True,
    run_expensive_validation=False,
)


@step(outputs=["data/raw"])
def load_data():
    """Load raw data."""
    print("Loading data...")
    return {"quality_score": 0.85, "rows": 10000}


@step(inputs=["data/raw"], outputs=["data/cleaned"])
def clean_data(data):
    """Clean data."""
    print(f"Cleaning data with quality score: {data['quality_score']}")
    return {"quality_score": 0.92, "rows": 9500}


# Conditional step: only runs if quality is below threshold
@step(
    inputs=["data/cleaned"],
    outputs=["data/enhanced"],
    condition=lambda quality_score: quality_score < 0.9,
)
def enhance_data_quality(data, data_quality_threshold: float):
    """Enhance data quality if needed."""
    print(f"Enhancing data quality (threshold: {data_quality_threshold})...")
    return {"quality_score": 0.95, "rows": data["rows"]}


# Conditional step: only runs if flag is enabled
@step(
    inputs=["data/cleaned"],
    outputs=["features/advanced"],
    condition=lambda enable_advanced_features: enable_advanced_features,
)
def extract_advanced_features(data, enable_advanced_features: bool):
    """Extract advanced features if enabled."""
    print("Extracting advanced features...")
    return {"feature_count": 100, "quality": "high"}


@step(inputs=["data/cleaned"], outputs=["model/trained"])
def train_model(data):
    """Train model."""
    print("Training model...")
    return {"accuracy": 0.93}


# Create and run pipeline
pipeline = Pipeline("conditional_example", context=ctx)
pipeline.add_step(load_data)
pipeline.add_step(clean_data)
pipeline.add_step(enhance_data_quality)  # May be skipped
pipeline.add_step(extract_advanced_features)  # May be skipped
pipeline.add_step(train_model)

result = pipeline.run(debug=True)

if result.success:
    print("\n✅ Pipeline completed!")

    # Check which steps were skipped
    for step_name, step_result in result.step_results.items():
        if step_result.skipped:
            print(f"⏭️  Step '{step_name}' was skipped")

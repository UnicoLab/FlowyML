"""
Caching Example.

Demonstrates different caching strategies in UniFlow.

Usage:
    $ python examples/caching_pipeline.py
"""

from uniflow import Pipeline, step, context
import time

ctx = context(
    data_version="v1.0",
    model_type="random_forest",
)


# Code hash caching (default): cached until function code changes
@step(outputs=["data/raw"], cache="code_hash")
def load_data():
    """Load data - cached by code hash."""
    print("Loading data (expensive operation)...")
    time.sleep(2)  # Simulate expensive I/O
    return {"rows": 10000, "version": "v1.0"}


# Input hash caching: cached based on input values
@step(inputs=["data/raw"], outputs=["data/processed"], cache="input_hash")
def preprocess(data, data_version: str):
    """Preprocess data - cached by inputs."""
    print(f"Preprocessing data version {data_version}...")
    time.sleep(1.5)
    return {"rows": data["rows"], "processed": True}


# No caching: always runs
@step(inputs=["data/processed"], outputs=["model/trained"], cache=False)
def train_model(data, model_type: str):
    """Train model - no caching."""
    print(f"Training {model_type} model (always runs)...")
    time.sleep(1)
    return {"accuracy": 0.92, "type": model_type}


# Create pipeline
pipeline = Pipeline("caching_example", context=ctx)
pipeline.add_step(load_data)
pipeline.add_step(preprocess)
pipeline.add_step(train_model)

print("=" * 60)
print("First run - all steps execute")
print("=" * 60)
result1 = pipeline.run(debug=True)

print("\n" + "=" * 60)
print("Second run - cached steps are skipped")
print("=" * 60)
result2 = pipeline.run(debug=True)

# Show cache statistics
print("\n" + "=" * 60)
print("Cache Statistics")
print("=" * 60)
stats = pipeline.cache_stats()
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Total cache size: {stats['total_size_mb']:.2f} MB")

"""
Simple example: Switching between local and GCP stacks.

This example shows how to easily switch between local development
and cloud production environments.
"""

from flowyml import Pipeline, step
from flowyml.stacks import LocalStack
from flowyml.stacks.gcp import GCPStack
from flowyml.stacks.registry import StackRegistry
import os

# Create registry
registry = StackRegistry()

# Register local stack for development
local_stack = LocalStack(name="local")
registry.register_stack(local_stack)

# Register GCP stack for production
gcp_stack = GCPStack(
    name="production",
    project_id=os.getenv("GCP_PROJECT_ID", "my-project"),
    region="us-central1",
    bucket_name=os.getenv("GCP_BUCKET", "my-artifacts"),
)
registry.register_stack(gcp_stack)


# Define a simple pipeline
@step
def process_data(value: int):
    """Process some data."""
    return {"result": value * 2}


@step
def aggregate(data: dict):
    """Aggregate results."""
    return {"total": data["result"] + 10}


pipeline = Pipeline("example_pipeline")
pipeline.add_step(process_data)
pipeline.add_step(aggregate)

if __name__ == "__main__":
    import sys

    # Check environment
    env = sys.argv[1] if len(sys.argv) > 1 else "local"

    # Switch stack based on environment
    if env == "prod":
        print("Running on GCP Production...")
        registry.set_active_stack("production")
    else:
        print("Running Locally...")
        registry.set_active_stack("local")

    # Get active stack
    active_stack = registry.get_active_stack()
    print(f"Active stack: {active_stack.name}")

    # Run pipeline - same code, different infrastructure!
    result = pipeline.run(context={"value": 5})

    print(f"\nResults: {result}")
    print("\nDone!")

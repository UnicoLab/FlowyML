"""End-to-end integration tests for FlowyML."""

import pytest
import time
import shutil
from pathlib import Path
from flowyml import Pipeline, step, context
from flowyml.core.retry_policy import OrchestratorRetryPolicy
from flowyml.core.observability import ConsoleMetricsCollector, set_metrics_collector
from flowyml.core.scheduler import PipelineScheduler

# Setup temporary directory for tests
TEST_DIR = Path(".flowyml_test_e2e")


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown for E2E tests."""
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir()

    yield

    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)


@step(outputs=["data"])
def ingest_step():
    return {"values": [1, 2, 3]}


@step(outputs=["processed"])
def process_step(data: dict):
    return [x * 2 for x in data["values"]]


class TestEndToEnd:
    """End-to-end tests for full pipeline lifecycle."""

    def test_full_local_execution_with_features(self):
        """Test full local execution with retries, caching, and observability."""

        # 1. Setup Observability
        set_metrics_collector(ConsoleMetricsCollector())

        # 2. Create Pipeline
        pipeline = Pipeline(
            "e2e_test_pipeline",
            cache_dir=str(TEST_DIR / "cache"),
        )
        pipeline.add_step(ingest_step)
        pipeline.add_step(process_step)

        # 3. Configure Retry Policy
        retry_policy = OrchestratorRetryPolicy(max_attempts=2)

        # 4. Run Pipeline
        result = pipeline.run(retry_policy=retry_policy)

        assert result.success
        assert result.state == "completed"
        assert "processed" in result.outputs
        assert result.outputs["processed"] == [2, 4, 6]

        # 5. Check Caching (Run again)
        # Note: LocalOrchestrator handles step caching automatically if inputs match
        result2 = pipeline.run()
        assert result2.success
        # Verify steps were cached (LocalOrchestrator marks result.cached)
        # We need to check step results
        assert result2.step_results["ingest_step"].cached

    def test_scheduler_integration(self):
        """Test pipeline scheduling integration."""
        pipeline = Pipeline("scheduled_test")
        pipeline.add_step(ingest_step)

        # Schedule it
        schedule = pipeline.schedule(
            schedule_type="interval",
            value=1,  # 1 second
        )

        assert schedule.pipeline_name == "scheduled_test"
        assert schedule.schedule_type == "interval"
        assert schedule.enabled

        # Clean up scheduler
        PipelineScheduler().clear()

    def test_pre_execution_cache_check(self):
        """Test pre-execution cache checking."""
        pipeline = Pipeline(
            "cache_check_test",
            cache_dir=str(TEST_DIR / "cache"),
        )
        pipeline.add_step(ingest_step)

        # First run
        result = pipeline.run()
        assert result.success

        # Check cache
        cached_run = pipeline.check_cache()
        assert cached_run is not None
        assert cached_run["pipeline_name"] == "cache_check_test"
        assert cached_run["status"] == "completed"

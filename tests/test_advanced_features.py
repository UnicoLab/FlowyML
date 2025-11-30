"""Tests for Phase 3 advanced features."""

import pytest
from flowyml.core.retry_policy import OrchestratorRetryPolicy
from flowyml.core.observability import (
    ConsoleMetricsCollector,
    set_metrics_collector,
    get_metrics_collector,
    PipelineMetricEvent,
    StepMetricEvent,
)
from flowyml.core.pipeline import Pipeline
from flowyml.core.step import step


class TestRetryPolicy:
    """Test retry policies."""

    def test_retry_policy_creation(self):
        """Test creating retry policy."""
        policy = OrchestratorRetryPolicy(
            max_attempts=5,
            initial_delay=30.0,
            max_delay=300.0,
        )
        assert policy.max_attempts == 5
        assert policy.initial_delay == 30.0

    def test_retry_policy_to_config(self):
        """Test converting to RetryConfig."""
        policy = OrchestratorRetryPolicy()
        config = policy.to_retry_config()
        assert config.max_attempts == 3
        assert config.backoff is not None


class TestObservability:
    """Test observability features."""

    def test_console_metrics_collector(self):
        """Test console metrics collector."""
        collector = ConsoleMetricsCollector()

        @step(outputs=["result"])
        def test_step() -> int:
            return 42

        pipeline = Pipeline("test_metrics")
        pipeline.add_step(test_step)

        # Should not raise
        collector.record_pipeline_start(pipeline, "test-run")

    def test_global_metrics_collector(self):
        """Test global metrics collector."""
        collector = ConsoleMetricsCollector()
        set_metrics_collector(collector)

        assert get_metrics_collector() is collector

    def test_metric_events(self):
        """Test metric event creation."""
        pipeline_event = PipelineMetricEvent(
            pipeline_name="test",
            run_id="123",
            duration_seconds=10.5,
            success=True,
        )

        data = pipeline_event.to_dict()
        assert data["pipeline_name"] == "test"
        assert data["run_id"] == "123"
        assert data["duration_seconds"] == 10.5
        assert data["success"] is True

        step_event = StepMetricEvent(
            step_name="test_step",
            pipeline_name="test",
            run_id="123",
            cached=True,
        )

        data = step_event.to_dict()
        assert data["cached"] is True

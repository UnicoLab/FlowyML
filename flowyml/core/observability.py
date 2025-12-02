"""Observability hooks for monitoring and metrics collection."""

from typing import Protocol, Any, TYPE_CHECKING
from datetime import datetime
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from flowyml.core.pipeline import Pipeline, PipelineResult
    from flowyml.core.step import Step
    from flowyml.core.executor import ExecutionResult


@dataclass
class MetricEvent:
    """Base metric event."""

    timestamp: datetime = field(default_factory=datetime.now)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class PipelineMetricEvent(MetricEvent):
    """Pipeline-level metric event."""

    pipeline_name: str = ""
    run_id: str = ""
    duration_seconds: float | None = None
    success: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "pipeline_name": self.pipeline_name,
                "run_id": self.run_id,
                "duration_seconds": self.duration_seconds,
                "success": self.success,
            },
        )
        return base


@dataclass
class StepMetricEvent(MetricEvent):
    """Step-level metric event."""

    step_name: str = ""
    pipeline_name: str = ""
    run_id: str = ""
    duration_seconds: float | None = None
    success: bool | None = None
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "step_name": self.step_name,
                "pipeline_name": self.pipeline_name,
                "run_id": self.run_id,
                "duration_seconds": self.duration_seconds,
                "success": self.success,
                "cached": self.cached,
            },
        )
        return base


class MetricsCollector(Protocol):
    """Protocol for metrics collectors."""

    def record_pipeline_start(self, pipeline: "Pipeline", run_id: str) -> None:
        """Record pipeline start."""
        ...

    def record_pipeline_end(self, pipeline: "Pipeline", result: "PipelineResult") -> None:
        """Record pipeline completion."""
        ...

    def record_step_start(self, step: "Step", pipeline_name: str, run_id: str) -> None:
        """Record step start."""
        ...

    def record_step_end(self, step: "Step", result: "ExecutionResult", pipeline_name: str, run_id: str) -> None:
        """Record step completion."""
        ...


class ConsoleMetricsCollector:
    """Simple console metrics collector for debugging."""

    def record_pipeline_start(self, pipeline: "Pipeline", run_id: str) -> None:
        event = PipelineMetricEvent(
            pipeline_name=pipeline.name,
            run_id=run_id,
        )
        print(f"📊 Pipeline Started: {event.to_dict()}")

    def record_pipeline_end(self, pipeline: "Pipeline", result: "PipelineResult") -> None:
        event = PipelineMetricEvent(
            pipeline_name=pipeline.name,
            run_id=result.run_id,
            duration_seconds=result.duration_seconds,
            success=result.success,
        )
        print(f"📊 Pipeline Ended: {event.to_dict()}")

    def record_step_start(self, step: "Step", pipeline_name: str, run_id: str) -> None:
        event = StepMetricEvent(
            step_name=step.name,
            pipeline_name=pipeline_name,
            run_id=run_id,
        )
        print(f"📊 Step Started: {event.to_dict()}")

    def record_step_end(self, step: "Step", result: "ExecutionResult", pipeline_name: str, run_id: str) -> None:
        event = StepMetricEvent(
            step_name=step.name,
            pipeline_name=pipeline_name,
            run_id=run_id,
            duration_seconds=getattr(result, "duration_seconds", None),
            success=result.success,
            cached=getattr(result, "cached", False),
        )
        print(f"📊 Step Ended: {event.to_dict()}")


class PrometheusMetricsCollector:
    """Prometheus metrics collector (requires prometheus_client)."""

    def __init__(self):
        try:
            from prometheus_client import Counter, Histogram

            self.pipeline_starts = Counter(
                "flowyml_pipeline_starts_total",
                "Total pipeline starts",
                ["pipeline_name"],
            )
            self.pipeline_completions = Counter(
                "flowyml_pipeline_completions_total",
                "Total pipeline completions",
                ["pipeline_name", "status"],
            )
            self.pipeline_duration = Histogram(
                "flowyml_pipeline_duration_seconds",
                "Pipeline duration in seconds",
                ["pipeline_name"],
            )
            self.step_duration = Histogram(
                "flowyml_step_duration_seconds",
                "Step duration in seconds",
                ["pipeline_name", "step_name"],
            )
            self.step_cache_hits = Counter(
                "flowyml_step_cache_hits_total",
                "Total step cache hits",
                ["pipeline_name", "step_name"],
            )
        except ImportError:
            raise ImportError("prometheus_client required for PrometheusMetricsCollector")

    def record_pipeline_start(self, pipeline: "Pipeline", run_id: str) -> None:
        self.pipeline_starts.labels(pipeline_name=pipeline.name).inc()

    def record_pipeline_end(self, pipeline: "Pipeline", result: "PipelineResult") -> None:
        status = "success" if result.success else "failure"
        self.pipeline_completions.labels(pipeline_name=pipeline.name, status=status).inc()

        if result.duration_seconds:
            self.pipeline_duration.labels(pipeline_name=pipeline.name).observe(result.duration_seconds)

    def record_step_start(self, step: "Step", pipeline_name: str, run_id: str) -> None:
        pass  # No-op for Prometheus (only track completion)

    def record_step_end(self, step: "Step", result: "ExecutionResult", pipeline_name: str, run_id: str) -> None:
        duration = getattr(result, "duration_seconds", None)
        if duration:
            self.step_duration.labels(
                pipeline_name=pipeline_name,
                step_name=step.name,
            ).observe(duration)

        if getattr(result, "cached", False):
            self.step_cache_hits.labels(
                pipeline_name=pipeline_name,
                step_name=step.name,
            ).inc()


# Global metrics collector
_metrics_collector: MetricsCollector | None = None


def set_metrics_collector(collector: MetricsCollector) -> None:
    """Set global metrics collector."""
    global _metrics_collector
    _metrics_collector = collector


def get_metrics_collector() -> MetricsCollector | None:
    """Get global metrics collector."""
    return _metrics_collector

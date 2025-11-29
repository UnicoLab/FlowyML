"""Run Management - Track individual pipeline runs."""

import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class RunMetadata:
    """Metadata for a pipeline run."""

    run_id: str
    pipeline_name: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "running"  # running, success, failed
    parameters: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "tags": self.tags,
        }


class Run:
    """Represents a single pipeline execution run.

    Example:
        >>> run = Run(run_id="training_20240115_120000", pipeline_name="training_pipeline")
        >>> run.log_metric("accuracy", 0.95)
        >>> run.complete(status="success")
    """

    def __init__(
        self,
        run_id: str,
        pipeline_name: str,
        parameters: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
        runs_dir: str = ".flowyml/runs",
    ):
        self.run_id = run_id
        self.pipeline_name = pipeline_name

        self.metadata = RunMetadata(
            run_id=run_id,
            pipeline_name=pipeline_name,
            started_at=datetime.now(),
            parameters=parameters or {},
            tags=tags or {},
        )

        # Storage
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        self._save()

    def log_metric(self, name: str, value: Any) -> None:
        """Log a metric for this run."""
        self.metadata.metrics[name] = value
        self._save()

    def log_metrics(self, metrics: dict[str, Any]) -> None:
        """Log multiple metrics."""
        self.metadata.metrics.update(metrics)
        self._save()

    def log_parameter(self, name: str, value: Any) -> None:
        """Log a parameter."""
        self.metadata.parameters[name] = value
        self._save()

    def add_tag(self, key: str, value: str) -> None:
        """Add a tag to the run."""
        self.metadata.tags[key] = value
        self._save()

    def complete(self, status: str = "success") -> None:
        """Mark run as complete.

        Args:
            status: Final status ("success" or "failed")
        """
        self.metadata.status = status
        self.metadata.ended_at = datetime.now()
        self._save()

    def get_duration(self) -> float | None:
        """Get run duration in seconds."""
        if self.metadata.ended_at:
            return (self.metadata.ended_at - self.metadata.started_at).total_seconds()
        return None

    def _save(self) -> None:
        """Save run metadata to disk."""
        run_file = self.runs_dir / f"{self.run_id}.json"

        with open(run_file, "w") as f:
            json.dump(self.metadata.to_dict(), f, indent=2)

    @classmethod
    def load(cls, run_id: str, runs_dir: str = ".flowyml/runs") -> Optional["Run"]:
        """Load a run from disk."""
        run_file = Path(runs_dir) / f"{run_id}.json"

        if not run_file.exists():
            return None

        try:
            with open(run_file) as f:
                data = json.load(f)

            run = cls(
                run_id=data["run_id"],
                pipeline_name=data["pipeline_name"],
                parameters=data.get("parameters", {}),
                tags=data.get("tags", {}),
                runs_dir=runs_dir,
            )

            run.metadata.status = data["status"]
            run.metadata.metrics = data.get("metrics", {})
            if data.get("ended_at"):
                run.metadata.ended_at = datetime.fromisoformat(data["ended_at"])

            return run

        except Exception:
            return None

    def __repr__(self) -> str:
        return f"Run(id='{self.run_id}', status='{self.metadata.status}')"

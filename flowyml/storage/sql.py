"""SQLAlchemy-based metadata storage backend."""

import json
import logging
from pathlib import Path
from datetime import datetime

# Python 3.11+ has UTC, but Python 3.10 doesn't
try:
    from datetime import UTC
except ImportError:
    UTC = UTC

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Float,
    Text,
    ForeignKey,
    select,
    insert,
    update,
    delete,
    func,
    text,
    inspect,
)
from sqlalchemy.pool import StaticPool

from flowyml.storage.metadata import MetadataStore

logger = logging.getLogger(__name__)


class SQLMetadataStore(MetadataStore):
    """SQLAlchemy-based metadata storage supporting SQLite and PostgreSQL."""

    def __init__(self, db_path: str = ".flowyml/metadata.db", db_url: str | None = None):
        """Initialize SQL metadata store.

        Args:
            db_path: Path to SQLite database file OR database URL (backward compatible)
            db_url: Explicit database URL (takes precedence if provided)
                   (e.g., sqlite:///path/to/db, postgresql://user:pass@host/db)
        """
        # Handle backward compatibility: if db_path looks like a URL, use it as db_url
        if db_url:
            self.db_url = db_url
            # Store db_path for backward compatibility
            if db_url.startswith("sqlite:///"):
                self.db_path = Path(db_url[10:])  # Remove 'sqlite:///'
            else:
                self.db_path = None
        elif db_path and ("://" in db_path or db_path.startswith("sqlite:")):
            # db_path is actually a URL
            self.db_url = db_path
            if db_path.startswith("sqlite:///"):
                self.db_path = Path(db_path[10:])
            else:
                self.db_path = None
        else:
            # db_path is a file path
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            # Ensure absolute path for SQLite URL
            abs_path = self.db_path.resolve()
            self.db_url = f"sqlite:///{abs_path}"

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        # Configure engine
        connect_args = {}
        if self.db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(
            self.db_url,
            connect_args=connect_args,
            poolclass=StaticPool if self.db_url.startswith("sqlite") else None,
        )

        self.metadata = MetaData()

        # Define tables
        self.runs = Table(
            "runs",
            self.metadata,
            Column("run_id", String, primary_key=True),
            Column("pipeline_name", String),
            Column("status", String),
            Column("start_time", String),
            Column("end_time", String),
            Column("duration", Float),
            Column("metadata", Text),
            Column("project", String),
            Column("created_at", String, server_default=func.current_timestamp()),
        )

        self.artifacts = Table(
            "artifacts",
            self.metadata,
            Column("artifact_id", String, primary_key=True),
            Column("name", String),
            Column("type", String),
            Column("run_id", String, ForeignKey("runs.run_id")),
            Column("path", String),
            Column("metadata", Text),
            Column("project", String),
            Column("created_at", String, server_default=func.current_timestamp()),
        )

        self.metrics = Table(
            "metrics",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("run_id", String, ForeignKey("runs.run_id")),
            Column("name", String),
            Column("value", Float),
            Column("step", Integer),
            Column("timestamp", String, server_default=func.current_timestamp()),
        )

        self.model_metrics = Table(
            "model_metrics",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("project", String),
            Column("model_name", String),
            Column("run_id", String),
            Column("metric_name", String),
            Column("metric_value", Float),
            Column("environment", String),
            Column("tags", Text),
            Column("created_at", String, server_default=func.current_timestamp()),
        )

        self.parameters = Table(
            "parameters",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("run_id", String, ForeignKey("runs.run_id")),
            Column("name", String),
            Column("value", Text),
        )

        self.experiments = Table(
            "experiments",
            self.metadata,
            Column("experiment_id", String, primary_key=True),
            Column("name", String),
            Column("description", Text),
            Column("tags", Text),
            Column("project", String),
            Column("created_at", String, server_default=func.current_timestamp()),
        )

        self.experiment_runs = Table(
            "experiment_runs",
            self.metadata,
            Column("experiment_id", String, ForeignKey("experiments.experiment_id"), primary_key=True),
            Column("run_id", String, ForeignKey("runs.run_id"), primary_key=True),
            Column("metrics", Text),
            Column("parameters", Text),
            Column("timestamp", String, server_default=func.current_timestamp()),
        )

        self.traces = Table(
            "traces",
            self.metadata,
            Column("event_id", String, primary_key=True),
            Column("trace_id", String),
            Column("parent_id", String),
            Column("event_type", String),
            Column("name", String),
            Column("inputs", Text),
            Column("outputs", Text),
            Column("start_time", Float),
            Column("end_time", Float),
            Column("duration", Float),
            Column("status", String),
            Column("error", Text),
            Column("metadata", Text),
            Column("prompt_tokens", Integer),
            Column("completion_tokens", Integer),
            Column("total_tokens", Integer),
            Column("cost", Float),
            Column("model", String),
            Column("project", String),
            Column("created_at", String, server_default=func.current_timestamp()),
        )

        self.pipeline_definitions = Table(
            "pipeline_definitions",
            self.metadata,
            Column("pipeline_name", String, primary_key=True),
            Column("definition", Text, nullable=False),
            Column("created_at", String, nullable=False),
            Column("updated_at", String, nullable=False),
        )

        # Create tables
        self.metadata.create_all(self.engine)

        # Handle migrations (add missing columns if tables existed)
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Add missing columns if needed."""
        inspector = inspect(self.engine)

        # Check runs.project
        columns = [c["name"] for c in inspector.get_columns("runs")]
        if "project" not in columns:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE runs ADD COLUMN project VARCHAR"))
                conn.commit()

        # Check artifacts.project
        columns = [c["name"] for c in inspector.get_columns("artifacts")]
        if "project" not in columns:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE artifacts ADD COLUMN project VARCHAR"))
                conn.commit()

        # Check experiments.project
        columns = [c["name"] for c in inspector.get_columns("experiments")]
        if "project" not in columns:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE experiments ADD COLUMN project VARCHAR"))
                conn.commit()

        # Check traces.project
        columns = [c["name"] for c in inspector.get_columns("traces")]
        if "project" not in columns:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE traces ADD COLUMN project VARCHAR"))
                conn.commit()

    def save_run(self, run_id: str, metadata: dict) -> None:
        """Save run metadata."""
        with self.engine.connect() as conn:
            # Upsert run
            stmt = select(self.runs).where(self.runs.c.run_id == run_id)
            existing = conn.execute(stmt).fetchone()

            values = {
                "run_id": run_id,
                "pipeline_name": metadata.get("pipeline_name"),
                "status": metadata.get("status"),
                "start_time": metadata.get("start_time"),
                "end_time": metadata.get("end_time"),
                "duration": metadata.get("duration"),
                "metadata": json.dumps(metadata),
                "project": metadata.get("project"),
            }

            if existing:
                conn.execute(
                    update(self.runs).where(self.runs.c.run_id == run_id).values(**values),
                )
            else:
                conn.execute(insert(self.runs).values(**values))

            # Save parameters
            if "parameters" in metadata:
                conn.execute(delete(self.parameters).where(self.parameters.c.run_id == run_id))
                if metadata["parameters"]:
                    conn.execute(
                        insert(self.parameters),
                        [
                            {"run_id": run_id, "name": k, "value": json.dumps(v)}
                            for k, v in metadata["parameters"].items()
                        ],
                    )

            # Save metrics
            if "metrics" in metadata:
                conn.execute(delete(self.metrics).where(self.metrics.c.run_id == run_id))
                if metadata["metrics"]:
                    conn.execute(
                        insert(self.metrics),
                        [
                            {"run_id": run_id, "name": k, "value": float(v), "step": 0}
                            for k, v in metadata["metrics"].items()
                        ],
                    )

            conn.commit()

    def load_run(self, run_id: str) -> dict | None:
        """Load run metadata."""
        with self.engine.connect() as conn:
            stmt = select(self.runs.c.metadata).where(self.runs.c.run_id == run_id)
            row = conn.execute(stmt).fetchone()
            if row:
                return json.loads(row[0])
            return None

    def update_run_project(self, run_id: str, project_name: str) -> None:
        """Update the project for a run."""
        with self.engine.connect() as conn:
            # Update column
            conn.execute(
                update(self.runs).where(self.runs.c.run_id == run_id).values(project=project_name),
            )

            # Update JSON blob
            stmt = select(self.runs.c.metadata).where(self.runs.c.run_id == run_id)
            row = conn.execute(stmt).fetchone()
            if row:
                metadata = json.loads(row[0])
                metadata["project"] = project_name
                conn.execute(
                    update(self.runs).where(self.runs.c.run_id == run_id).values(metadata=json.dumps(metadata)),
                )

            conn.commit()

    def list_runs(self, limit: int | None = None) -> list[dict]:
        """List all runs."""
        with self.engine.connect() as conn:
            stmt = select(self.runs.c.metadata).order_by(self.runs.c.created_at.desc())
            if limit:
                stmt = stmt.limit(limit)

            rows = conn.execute(stmt).fetchall()
            return [json.loads(row[0]) for row in rows]

    def list_pipelines(self, project: str = None) -> list[str]:
        """List all unique pipeline names."""
        with self.engine.connect() as conn:
            stmt = select(self.runs.c.pipeline_name).distinct().order_by(self.runs.c.pipeline_name)
            if project:
                stmt = stmt.where(self.runs.c.project == project)

            rows = conn.execute(stmt).fetchall()
            return [row[0] for row in rows if row[0]]

    def save_artifact(self, artifact_id: str, metadata: dict) -> None:
        """Save artifact metadata."""
        with self.engine.connect() as conn:
            stmt = select(self.artifacts).where(self.artifacts.c.artifact_id == artifact_id)
            existing = conn.execute(stmt).fetchone()

            values = {
                "artifact_id": artifact_id,
                "name": metadata.get("name"),
                "type": metadata.get("type"),
                "run_id": metadata.get("run_id"),
                "path": metadata.get("path"),
                "metadata": json.dumps(metadata),
                "project": metadata.get("project"),
            }

            if existing:
                conn.execute(
                    update(self.artifacts).where(self.artifacts.c.artifact_id == artifact_id).values(**values),
                )
            else:
                conn.execute(insert(self.artifacts).values(**values))

            conn.commit()

    def load_artifact(self, artifact_id: str) -> dict | None:
        """Load artifact metadata."""
        with self.engine.connect() as conn:
            stmt = select(self.artifacts.c.metadata).where(self.artifacts.c.artifact_id == artifact_id)
            row = conn.execute(stmt).fetchone()
            if row:
                return json.loads(row[0])
            return None

    def delete_artifact(self, artifact_id: str) -> None:
        """Delete artifact metadata."""
        with self.engine.connect() as conn:
            conn.execute(delete(self.artifacts).where(self.artifacts.c.artifact_id == artifact_id))
            conn.commit()

    def list_assets(self, limit: int | None = None, **filters) -> list[dict]:
        """List assets with optional filters."""
        with self.engine.connect() as conn:
            stmt = select(self.artifacts.c.metadata)

            for key, value in filters.items():
                if value is not None and hasattr(self.artifacts.c, key):
                    stmt = stmt.where(getattr(self.artifacts.c, key) == value)

            stmt = stmt.order_by(self.artifacts.c.created_at.desc())

            if limit:
                stmt = stmt.limit(limit)

            rows = conn.execute(stmt).fetchall()
            return [json.loads(row[0]) for row in rows]

    def query(self, **filters) -> list[dict]:
        """Query runs with filters."""
        with self.engine.connect() as conn:
            stmt = select(self.runs.c.metadata)

            for key, value in filters.items():
                if hasattr(self.runs.c, key):
                    stmt = stmt.where(getattr(self.runs.c, key) == value)

            stmt = stmt.order_by(self.runs.c.created_at.desc())
            rows = conn.execute(stmt).fetchall()
            return [json.loads(row[0]) for row in rows]

    def save_metric(self, run_id: str, name: str, value: float, step: int = 0) -> None:
        """Save a single metric value."""
        with self.engine.connect() as conn:
            conn.execute(
                insert(self.metrics).values(
                    run_id=run_id,
                    name=name,
                    value=value,
                    step=step,
                ),
            )
            conn.commit()

    def get_metrics(self, run_id: str, name: str | None = None) -> list[dict]:
        """Get metrics for a run."""
        with self.engine.connect() as conn:
            stmt = select(
                self.metrics.c.name,
                self.metrics.c.value,
                self.metrics.c.step,
                self.metrics.c.timestamp,
            ).where(self.metrics.c.run_id == run_id)

            if name:
                stmt = stmt.where(self.metrics.c.name == name)

            stmt = stmt.order_by(self.metrics.c.step)
            rows = conn.execute(stmt).fetchall()

            return [{"name": row[0], "value": row[1], "step": row[2], "timestamp": str(row[3])} for row in rows]

    def log_model_metrics(
        self,
        project: str,
        model_name: str,
        metrics: dict[str, float],
        run_id: str | None = None,
        environment: str | None = None,
        tags: dict | None = None,
    ) -> None:
        """Log production model metrics."""
        if not metrics:
            return

        with self.engine.connect() as conn:
            tags_json = json.dumps(tags or {})

            values_list = []
            for metric_name, value in metrics.items():
                try:
                    metric_value = float(value)
                    values_list.append(
                        {
                            "project": project,
                            "model_name": model_name,
                            "run_id": run_id,
                            "metric_name": metric_name,
                            "metric_value": metric_value,
                            "environment": environment,
                            "tags": tags_json,
                        },
                    )
                except (TypeError, ValueError):
                    continue

            if values_list:
                conn.execute(insert(self.model_metrics), values_list)
                conn.commit()

    def list_model_metrics(
        self,
        project: str | None = None,
        model_name: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List logged model metrics."""
        with self.engine.connect() as conn:
            stmt = select(
                self.model_metrics.c.project,
                self.model_metrics.c.model_name,
                self.model_metrics.c.run_id,
                self.model_metrics.c.metric_name,
                self.model_metrics.c.metric_value,
                self.model_metrics.c.environment,
                self.model_metrics.c.tags,
                self.model_metrics.c.created_at,
            )

            if project:
                stmt = stmt.where(self.model_metrics.c.project == project)
            if model_name:
                stmt = stmt.where(self.model_metrics.c.model_name == model_name)

            stmt = stmt.order_by(self.model_metrics.c.created_at.desc()).limit(limit)
            rows = conn.execute(stmt).fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "project": row[0],
                        "model_name": row[1],
                        "run_id": row[2],
                        "metric_name": row[3],
                        "metric_value": row[4],
                        "environment": row[5],
                        "tags": json.loads(row[6]) if row[6] else {},
                        "created_at": str(row[7]),
                    },
                )
            return results

    def save_experiment(self, experiment_id: str, name: str, description: str = "", tags: dict = None) -> None:
        """Save experiment metadata."""
        with self.engine.connect() as conn:
            stmt = select(self.experiments).where(self.experiments.c.experiment_id == experiment_id)
            existing = conn.execute(stmt).fetchone()

            values = {
                "experiment_id": experiment_id,
                "name": name,
                "description": description,
                "tags": json.dumps(tags or {}),
            }

            if existing:
                conn.execute(
                    update(self.experiments).where(self.experiments.c.experiment_id == experiment_id).values(**values),
                )
            else:
                conn.execute(insert(self.experiments).values(**values))

            conn.commit()

    def log_experiment_run(
        self,
        experiment_id: str,
        run_id: str,
        metrics: dict = None,
        parameters: dict = None,
    ) -> None:
        """Log a run to an experiment."""
        with self.engine.connect() as conn:
            # Check if exists (composite primary key)
            stmt = select(self.experiment_runs).where(
                (self.experiment_runs.c.experiment_id == experiment_id) & (self.experiment_runs.c.run_id == run_id),
            )
            existing = conn.execute(stmt).fetchone()

            values = {
                "experiment_id": experiment_id,
                "run_id": run_id,
                "metrics": json.dumps(metrics or {}),
                "parameters": json.dumps(parameters or {}),
            }

            if existing:
                conn.execute(
                    update(self.experiment_runs)
                    .where(
                        (self.experiment_runs.c.experiment_id == experiment_id)
                        & (self.experiment_runs.c.run_id == run_id),
                    )
                    .values(**values),
                )
            else:
                conn.execute(insert(self.experiment_runs).values(**values))

            conn.commit()

    def list_experiments(self) -> list[dict]:
        """List all experiments."""
        with self.engine.connect() as conn:
            stmt = select(
                self.experiments.c.experiment_id,
                self.experiments.c.name,
                self.experiments.c.description,
                self.experiments.c.tags,
                self.experiments.c.created_at,
                self.experiments.c.project,
            ).order_by(self.experiments.c.created_at.desc())

            rows = conn.execute(stmt).fetchall()

            experiments = []
            for row in rows:
                # Count runs
                count_stmt = (
                    select(func.count())
                    .select_from(self.experiment_runs)
                    .where(
                        self.experiment_runs.c.experiment_id == row[0],
                    )
                )
                run_count = conn.execute(count_stmt).scalar()

                experiments.append(
                    {
                        "experiment_id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "tags": json.loads(row[3]),
                        "created_at": str(row[4]),
                        "project": row[5],
                        "run_count": run_count,
                    },
                )
            return experiments

    def update_experiment_project(self, experiment_name: str, project_name: str) -> None:
        """Update the project for an experiment."""
        with self.engine.connect() as conn:
            conn.execute(
                update(self.experiments).where(self.experiments.c.name == experiment_name).values(project=project_name),
            )
            conn.commit()

    def get_experiment(self, experiment_id: str) -> dict | None:
        """Get experiment details."""
        with self.engine.connect() as conn:
            stmt = select(
                self.experiments.c.experiment_id,
                self.experiments.c.name,
                self.experiments.c.description,
                self.experiments.c.tags,
                self.experiments.c.created_at,
            ).where(self.experiments.c.experiment_id == experiment_id)

            row = conn.execute(stmt).fetchone()
            if not row:
                return None

            return {
                "experiment_id": row[0],
                "name": row[1],
                "description": row[2],
                "tags": json.loads(row[3]),
                "created_at": str(row[4]),
            }

    def save_trace_event(self, event: dict) -> None:
        """Save a trace event."""
        with self.engine.connect() as conn:
            stmt = select(self.traces).where(self.traces.c.event_id == event["event_id"])
            existing = conn.execute(stmt).fetchone()

            values = {
                "event_id": event["event_id"],
                "trace_id": event.get("trace_id"),
                "parent_id": event.get("parent_id"),
                "event_type": event.get("event_type"),
                "name": event.get("name"),
                "inputs": json.dumps(event.get("inputs")),
                "outputs": json.dumps(event.get("outputs")),
                "start_time": event.get("start_time"),
                "end_time": event.get("end_time"),
                "duration": event.get("duration"),
                "status": event.get("status"),
                "error": json.dumps(event.get("error")),
                "metadata": json.dumps(event.get("metadata")),
                "prompt_tokens": event.get("prompt_tokens"),
                "completion_tokens": event.get("completion_tokens"),
                "total_tokens": event.get("total_tokens"),
                "cost": event.get("cost"),
                "model": event.get("model"),
                "project": event.get("project"),
            }

            if existing:
                conn.execute(
                    update(self.traces).where(self.traces.c.event_id == event["event_id"]).values(**values),
                )
            else:
                conn.execute(insert(self.traces).values(**values))

            conn.commit()

    def save_pipeline_definition(self, pipeline_name: str, definition: dict) -> None:
        """Save pipeline definition."""
        now = datetime.now(UTC).isoformat()
        with self.engine.connect() as conn:
            stmt = select(self.pipeline_definitions).where(
                self.pipeline_definitions.c.pipeline_name == pipeline_name,
            )
            existing = conn.execute(stmt).fetchone()

            values = {
                "pipeline_name": pipeline_name,
                "definition": json.dumps(definition),
                "updated_at": now,
            }

            if existing:
                conn.execute(
                    update(self.pipeline_definitions)
                    .where(self.pipeline_definitions.c.pipeline_name == pipeline_name)
                    .values(**values),
                )
            else:
                values["created_at"] = now
                conn.execute(insert(self.pipeline_definitions).values(**values))

            conn.commit()

    def get_trace(self, trace_id: str) -> list[dict]:
        """Get all events for a trace."""
        with self.engine.connect() as conn:
            stmt = select(self.traces).where(self.traces.c.trace_id == trace_id).order_by(self.traces.c.start_time)
            rows = conn.execute(stmt).fetchall()

            events = []
            for row in rows:
                event = {
                    "event_id": row.event_id,
                    "trace_id": row.trace_id,
                    "parent_id": row.parent_id,
                    "event_type": row.event_type,
                    "name": row.name,
                    "inputs": json.loads(row.inputs) if row.inputs else {},
                    "outputs": json.loads(row.outputs) if row.outputs else {},
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "duration": row.duration,
                    "status": row.status,
                    "error": json.loads(row.error) if row.error else None,
                    "metadata": json.loads(row.metadata) if row.metadata else {},
                    "prompt_tokens": row.prompt_tokens,
                    "completion_tokens": row.completion_tokens,
                    "total_tokens": row.total_tokens,
                    "cost": row.cost,
                    "model": row.model,
                    "project": row.project,
                }
                events.append(event)
            return events

    def list_traces(
        self,
        limit: int = 50,
        trace_id: str | None = None,
        event_type: str | None = None,
        project: str | None = None,
    ) -> list[dict]:
        """List traces with optional filters."""
        with self.engine.connect() as conn:
            stmt = select(self.traces)

            if trace_id:
                stmt = stmt.where(self.traces.c.trace_id == trace_id)
            if event_type:
                stmt = stmt.where(self.traces.c.event_type == event_type)
            if project:
                stmt = stmt.where(self.traces.c.project == project)

            stmt = stmt.order_by(self.traces.c.start_time.desc()).limit(limit)
            rows = conn.execute(stmt).fetchall()

            traces = []
            for row in rows:
                trace = {
                    "event_id": row.event_id,
                    "trace_id": row.trace_id,
                    "parent_id": row.parent_id,
                    "event_type": row.event_type,
                    "name": row.name,
                    "inputs": json.loads(row.inputs) if row.inputs else {},
                    "outputs": json.loads(row.outputs) if row.outputs else {},
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "duration": row.duration,
                    "status": row.status,
                    "error": json.loads(row.error) if row.error else None,
                    "metadata": json.loads(row.metadata) if row.metadata else {},
                    "prompt_tokens": row.prompt_tokens,
                    "completion_tokens": row.completion_tokens,
                    "total_tokens": row.total_tokens,
                    "cost": row.cost,
                    "model": row.model,
                    "project": row.project,
                    "created_at": row.created_at,
                }
                traces.append(trace)
            return traces

    def get_pipeline_definition(self, pipeline_name: str) -> dict | None:
        """Get pipeline definition."""
        with self.engine.connect() as conn:
            stmt = select(self.pipeline_definitions.c.definition).where(
                self.pipeline_definitions.c.pipeline_name == pipeline_name,
            )
            row = conn.execute(stmt).fetchone()
            if row:
                return json.loads(row[0])
            return None

    def get_orchestrator_metrics(self, days: int = 30) -> dict:
        """Get orchestrator-level performance metrics for the last N days."""
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with self.engine.connect() as conn:
            # Total runs
            total_runs = conn.execute(
                select(func.count()).select_from(self.runs).where(self.runs.c.created_at >= cutoff),
            ).scalar()

            # Status distribution
            status_stmt = (
                select(
                    self.runs.c.status,
                    func.count(),
                )
                .where(self.runs.c.created_at >= cutoff)
                .group_by(self.runs.c.status)
            )
            status_rows = conn.execute(status_stmt).fetchall()
            status_counts = {row[0]: row[1] for row in status_rows if row[0]}

            # Average duration
            avg_duration = (
                conn.execute(
                    select(func.avg(self.runs.c.duration)).where(
                        (self.runs.c.created_at >= cutoff) & (self.runs.c.duration.isnot(None)),
                    ),
                ).scalar()
                or 0
            )

            completed = status_counts.get("completed", 0)
            success_rate = completed / total_runs if total_runs > 0 else 0

            return {
                "total_runs": total_runs,
                "success_rate": success_rate,
                "avg_duration_seconds": avg_duration,
                "status_distribution": status_counts,
                "period_days": days,
            }

    def get_cache_metrics(self, days: int = 30) -> dict:
        """Get cache performance metrics for the last N days."""
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with self.engine.connect() as conn:
            stmt = select(self.runs.c.metadata).where(self.runs.c.created_at >= cutoff)
            rows = conn.execute(stmt).fetchall()

            total_steps, cached_steps = 0, 0
            for row in rows:
                if not row[0]:
                    continue
                try:
                    metadata = json.loads(row[0])
                    for step_data in metadata.get("steps", {}).values():
                        total_steps += 1
                        if step_data.get("cached"):
                            cached_steps += 1
                except Exception:
                    continue

            cache_hit_rate = cached_steps / total_steps if total_steps > 0 else 0

            return {
                "total_steps": total_steps,
                "cached_steps": cached_steps,
                "cache_hit_rate": cache_hit_rate,
                "period_days": days,
            }

    def get_statistics(self) -> dict:
        """Get global statistics."""
        with self.engine.connect() as conn:
            # Total runs
            total_runs = conn.execute(select(func.count()).select_from(self.runs)).scalar()

            # Total pipelines
            total_pipelines = conn.execute(
                select(func.count(func.distinct(self.runs.c.pipeline_name))),
            ).scalar()

            # Total experiments
            total_experiments = conn.execute(select(func.count()).select_from(self.experiments)).scalar()

            # Total models (unique model names in metrics)
            total_models = conn.execute(
                select(func.count(func.distinct(self.model_metrics.c.model_name))),
            ).scalar()

            return {
                "total_runs": total_runs,
                "total_pipelines": total_pipelines,
                "total_experiments": total_experiments,
                "total_models": total_models,
            }

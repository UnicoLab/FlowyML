"""Pipeline scheduling and automation."""

import contextlib
import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    select,
    insert,
    update,
    delete,
    func,
)
from sqlalchemy.pool import StaticPool

from flowyml.core.scheduler_config import SchedulerConfig

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    from croniter import croniter
except ImportError:
    croniter = None

try:
    import pytz
except ImportError:
    pytz = None


@dataclass
class Schedule:
    """Represents a pipeline schedule."""

    pipeline_name: str
    schedule_type: str  # 'cron', 'interval', 'daily', 'hourly'
    schedule_value: str  # cron expression or interval in seconds
    pipeline_func: Callable
    context: dict[str, Any] | None = None
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
    timezone: str = "UTC"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "schedule_type": self.schedule_type,
            "schedule_value": self.schedule_value,
            "context": self.context,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], pipeline_func: Callable) -> "Schedule":
        """Create from dictionary."""
        return cls(
            pipeline_name=data["pipeline_name"],
            schedule_type=data["schedule_type"],
            schedule_value=data["schedule_value"],
            pipeline_func=pipeline_func,
            context=data.get("context"),
            enabled=data.get("enabled", True),
            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None,
            timezone=data.get("timezone", "UTC"),
        )


@dataclass
class ScheduleExecution:
    """Record of schedule execution."""

    schedule_name: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = False
    error: str | None = None
    duration_seconds: float | None = None
    run_id: str | None = None  # Pipeline run_id if available


class SchedulerMetrics:
    """Track scheduler metrics."""

    def __init__(self):
        self.total_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0
        self.avg_duration_seconds = 0.0
        self.last_heartbeat = datetime.now()

    def update(self, execution: ScheduleExecution):
        """Update metrics with new execution."""
        self.total_runs += 1
        if execution.success:
            self.successful_runs += 1
        else:
            self.failed_runs += 1

        if execution.duration_seconds is not None:
            # Moving average
            alpha = 0.1
            self.avg_duration_seconds = alpha * execution.duration_seconds + (1 - alpha) * self.avg_duration_seconds

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": self.successful_runs / max(self.total_runs, 1),
            "avg_duration_seconds": self.avg_duration_seconds,
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }


class SchedulerPersistence:
    """Persist schedules to SQLite database using SQLAlchemy."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(Path.cwd() / ".flowyml_scheduler.db")
        # Convert to absolute path for SQLite URL
        abs_path = Path(self.db_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_url = f"sqlite:///{abs_path}"
        self._init_db()

    def _init_db(self):
        """Initialize database schema using SQLAlchemy."""
        # Create engine
        self.engine = create_engine(
            self.db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        self.metadata = MetaData()

        # Define schedules table
        self.schedules = Table(
            "schedules",
            self.metadata,
            Column("name", String, primary_key=True),
            Column("data", Text, nullable=False),
            Column("updated_at", DateTime, server_default=func.current_timestamp()),
        )

        # Define executions table
        self.executions = Table(
            "executions",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("schedule_name", String, ForeignKey("schedules.name"), nullable=False),
            Column("started_at", DateTime, nullable=False),
            Column("completed_at", DateTime, nullable=True),
            Column("success", Boolean, nullable=True),
            Column("error", Text, nullable=True),
            Column("duration_seconds", Float, nullable=True),
            Column("run_id", String, nullable=True),
        )

        # Create all tables
        self.metadata.create_all(self.engine)

    def save_schedule(self, schedule: Schedule) -> None:
        """Save schedule to database using SQLAlchemy."""
        data = schedule.to_dict()
        with self.engine.connect() as conn:
            # Use INSERT OR REPLACE equivalent in SQLAlchemy
            stmt = (
                update(self.schedules)
                .where(self.schedules.c.name == schedule.pipeline_name)
                .values(data=json.dumps(data), updated_at=func.current_timestamp())
            )
            result = conn.execute(stmt)
            conn.commit()

            # If no rows were updated, insert new record
            if result.rowcount == 0:
                stmt = insert(self.schedules).values(
                    name=schedule.pipeline_name,
                    data=json.dumps(data),
                )
                conn.execute(stmt)
                conn.commit()

    def load_schedules(self, pipeline_funcs: dict[str, Callable]) -> dict[str, Schedule]:
        """Load all schedules from database using SQLAlchemy."""
        schedules = {}
        with self.engine.connect() as conn:
            stmt = select(self.schedules.c.name, self.schedules.c.data)
            result = conn.execute(stmt)
            for row in result:
                name, data_json = row
                try:
                    data = json.loads(data_json)
                    if name in pipeline_funcs:
                        schedules[name] = Schedule.from_dict(data, pipeline_funcs[name])
                except Exception as e:
                    logger.error(f"Failed to load schedule {name}: {e}")
        return schedules

    def delete_schedule(self, name: str) -> None:
        """Delete schedule from database using SQLAlchemy."""
        with self.engine.connect() as conn:
            # Delete executions first (foreign key constraint)
            stmt = delete(self.executions).where(self.executions.c.schedule_name == name)
            conn.execute(stmt)

            # Delete schedule
            stmt = delete(self.schedules).where(self.schedules.c.name == name)
            conn.execute(stmt)
            conn.commit()

    def save_execution(self, execution: ScheduleExecution) -> None:
        """Save execution record using SQLAlchemy."""
        with self.engine.connect() as conn:
            stmt = insert(self.executions).values(
                schedule_name=execution.schedule_name,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                success=execution.success,
                error=execution.error,
                duration_seconds=execution.duration_seconds,
                run_id=execution.run_id,
            )
            conn.execute(stmt)
            conn.commit()

    def list_all_schedules(self) -> list[dict[str, Any]]:
        """List all schedules from database without requiring pipeline functions.

        This is useful for displaying schedules in the UI regardless of whether
        the pipeline code is loaded.
        """
        schedules = []
        with self.engine.connect() as conn:
            stmt = select(self.schedules.c.name, self.schedules.c.data, self.schedules.c.updated_at)
            result = conn.execute(stmt)
            for row in result:
                try:
                    data = json.loads(row.data)
                    data["name"] = row.name
                    if row.updated_at:
                        data["updated_at"] = (
                            row.updated_at.isoformat() if isinstance(row.updated_at, datetime) else str(row.updated_at)
                        )
                    schedules.append(data)
                except Exception as e:
                    logger.error(f"Failed to parse schedule {row.name}: {e}")
        return schedules

    def get_history(self, schedule_name: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get execution history for a schedule using SQLAlchemy."""
        history = []
        with self.engine.connect() as conn:
            stmt = (
                select(
                    self.executions.c.started_at,
                    self.executions.c.completed_at,
                    self.executions.c.success,
                    self.executions.c.error,
                    self.executions.c.duration_seconds,
                    self.executions.c.run_id,
                )
                .where(self.executions.c.schedule_name == schedule_name)
                .order_by(self.executions.c.started_at.desc())
                .limit(limit)
            )
            result = conn.execute(stmt)
            for row in result:
                # Handle datetime conversion
                started_at = row.started_at
                if isinstance(started_at, datetime):
                    started_at = started_at.isoformat()
                elif started_at is not None:
                    started_at = str(started_at)

                completed_at = row.completed_at
                if isinstance(completed_at, datetime):
                    completed_at = completed_at.isoformat()
                elif completed_at is not None:
                    completed_at = str(completed_at)

                history.append(
                    {
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "success": bool(row.success) if row.success is not None else False,
                        "error": row.error,
                        "duration_seconds": row.duration_seconds,
                        "run_id": row.run_id,
                    },
                )
        return history


class DistributedLock:
    """Distributed lock for coordinating multiple scheduler instances."""

    def __init__(self, backend: str = "file", redis_url: str | None = None):
        self.backend = backend
        self.redis_url = redis_url
        self._redis = None
        if backend == "redis" and redis_url:
            try:
                import redis

                self._redis = redis.from_url(redis_url)
            except ImportError:
                logger.warning("Redis not installed, falling back to file lock")
                self.backend = "file"

    def acquire(self, schedule_name: str, timeout: int = 60) -> bool:
        """Acquire lock for schedule execution."""
        if self.backend == "redis" and self._redis:
            lock_key = f"flowyml:scheduler:lock:{schedule_name}"
            return bool(self._redis.set(lock_key, "locked", ex=timeout, nx=True))
        else:
            # Simple file-based lock (not truly distributed across machines, but works for processes)
            lock_file = f".lock_{schedule_name}"
            lock_path = Path(lock_file)
            if lock_path.exists():
                # Check if stale
                if time.time() - lock_path.stat().st_mtime > timeout:
                    lock_path.unlink()
                else:
                    return False
            try:
                with open(lock_file, "w") as f:
                    f.write(str(time.time()))
                return True
            except OSError:
                return False

    def release(self, schedule_name: str) -> None:
        """Release lock after execution."""
        if self.backend == "redis" and self._redis:
            lock_key = f"flowyml:scheduler:lock:{schedule_name}"
            self._redis.delete(lock_key)
        else:
            lock_file = f".lock_{schedule_name}"
            lock_path = Path(lock_file)
            if lock_path.exists():
                with contextlib.suppress(OSError):
                    lock_path.unlink()


class PipelineScheduler:
    """Schedule pipelines to run automatically.

    Enhanced scheduler with persistence, distributed locking, and cron support.
    """

    def __init__(
        self,
        config: SchedulerConfig | None = None,
        on_success: Callable | None = None,
        on_failure: Callable | None = None,
    ):
        self.config = config or SchedulerConfig.from_env()
        self.schedules: dict[str, Schedule] = {}
        self.running = False
        self._thread = None
        self.on_success = on_success
        self.on_failure = on_failure
        self.metrics = SchedulerMetrics()

        # Persistence
        self._persistence = None
        if self.config.persist_schedules:
            self._persistence = SchedulerPersistence(self.config.db_path)

        # Locking
        self._lock = DistributedLock(self.config.lock_backend, self.config.redis_url)

        # Registry of pipeline functions for reloading
        self._pipeline_funcs: dict[str, Callable] = {}

    def _register_func(self, name: str, func: Callable):
        """Register pipeline function for persistence reloading."""
        self._pipeline_funcs[name] = func

    def schedule_daily(
        self,
        name: str,
        pipeline_func: Callable,
        hour: int = 0,
        minute: int = 0,
        timezone: str = "UTC",
        context: dict[str, Any] | None = None,
    ) -> Schedule:
        """Schedule pipeline to run daily at a specific time."""
        self._register_func(name, pipeline_func)

        if pytz:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        else:
            # Fallback to local time if pytz missing
            now = datetime.now()
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)

        schedule = Schedule(
            pipeline_name=name,
            schedule_type="daily",
            schedule_value=f"{hour:02d}:{minute:02d}",
            pipeline_func=pipeline_func,
            context=context,
            next_run=next_run,
            timezone=timezone,
        )
        self.schedules[name] = schedule
        if self._persistence:
            self._persistence.save_schedule(schedule)
        return schedule

    def schedule_interval(
        self,
        name: str,
        pipeline_func: Callable,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        timezone: str = "UTC",
        context: dict[str, Any] | None = None,
    ) -> Schedule:
        """Schedule pipeline to run at regular intervals."""
        self._register_func(name, pipeline_func)

        interval_seconds = hours * 3600 + minutes * 60 + seconds

        if pytz:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
        else:
            now = datetime.now()

        next_run = now + timedelta(seconds=interval_seconds)

        schedule = Schedule(
            pipeline_name=name,
            schedule_type="interval",
            schedule_value=str(interval_seconds),
            pipeline_func=pipeline_func,
            context=context,
            next_run=next_run,
            timezone=timezone,
        )
        self.schedules[name] = schedule
        if self._persistence:
            self._persistence.save_schedule(schedule)
        return schedule

    def schedule_hourly(
        self,
        name: str,
        pipeline_func: Callable,
        minute: int = 0,
        timezone: str = "UTC",
        context: dict[str, Any] | None = None,
    ) -> Schedule:
        """Schedule pipeline to run hourly."""
        self._register_func(name, pipeline_func)

        if pytz:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            next_run = now.replace(minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
        else:
            now = datetime.now()
            next_run = now.replace(minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)

        schedule = Schedule(
            pipeline_name=name,
            schedule_type="hourly",
            schedule_value=str(minute),
            pipeline_func=pipeline_func,
            context=context,
            next_run=next_run,
            timezone=timezone,
        )
        self.schedules[name] = schedule
        if self._persistence:
            self._persistence.save_schedule(schedule)
        return schedule

    def schedule_cron(
        self,
        name: str,
        pipeline_func: Callable,
        cron_expression: str,
        timezone: str = "UTC",
        context: dict[str, Any] | None = None,
    ) -> Schedule:
        """Schedule with cron expression."""
        if not croniter:
            raise ImportError("croniter is required for cron scheduling. Install with: pip install croniter")

        self._register_func(name, pipeline_func)

        if pytz:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
        else:
            now = datetime.now()

        cron = croniter(cron_expression, now)
        next_run = cron.get_next(datetime)

        schedule = Schedule(
            pipeline_name=name,
            schedule_type="cron",
            schedule_value=cron_expression,
            pipeline_func=pipeline_func,
            context=context,
            next_run=next_run,
            timezone=timezone,
        )
        self.schedules[name] = schedule
        if self._persistence:
            self._persistence.save_schedule(schedule)
        return schedule

    def unschedule(self, name: str) -> None:
        """Remove a scheduled pipeline."""
        if name in self.schedules:
            del self.schedules[name]
            if self._persistence:
                self._persistence.delete_schedule(name)

    def clear(self) -> None:
        """Remove all schedules."""
        self.schedules.clear()
        if self._persistence:
            # Delete all schedules and executions using SQLAlchemy
            with self._persistence.engine.connect() as conn:
                conn.execute(delete(self._persistence.executions))
                conn.execute(delete(self._persistence.schedules))
                conn.commit()

    def enable(self, name: str) -> None:
        """Enable a schedule."""
        if name in self.schedules:
            self.schedules[name].enabled = True
            if self._persistence:
                self._persistence.save_schedule(self.schedules[name])

    def disable(self, name: str) -> None:
        """Disable a schedule."""
        if name in self.schedules:
            self.schedules[name].enabled = False
            if self._persistence:
                self._persistence.save_schedule(self.schedules[name])

    def _run_pipeline(self, schedule: Schedule) -> None:
        """Run a scheduled pipeline."""
        # Acquire distributed lock if enabled
        if self.config.distributed:
            if not self._lock.acquire(schedule.pipeline_name):
                logger.info(f"Skipping {schedule.pipeline_name}: locked by another instance")
                return

        execution = ScheduleExecution(
            schedule_name=schedule.pipeline_name,
            started_at=datetime.now(),
        )

        pipeline_result = None
        try:
            logger.info(f"Starting scheduled run: {schedule.pipeline_name}")

            # Execute pipeline and capture result
            result = schedule.pipeline_func()

            # Check if result is a PipelineResult object
            from flowyml.core.pipeline import PipelineResult

            if isinstance(result, PipelineResult):
                pipeline_result = result
                execution.success = result.success
                # Store run_id for tracking
                execution.run_id = result.run_id
            else:
                # Assume success if no exception and result is truthy
                execution.success = bool(result)

            schedule.last_run = datetime.now(pytz.timezone(schedule.timezone)) if pytz else datetime.now()

            if self.on_success:
                self.on_success(schedule, execution)
        except Exception as e:
            logger.error(f"Schedule {schedule.pipeline_name} failed: {e}", exc_info=True)
            execution.error = str(e)
            execution.success = False
            if self.on_failure:
                self.on_failure(schedule, execution, e)
        finally:
            execution.completed_at = datetime.now()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            self.metrics.update(execution)

            # Ensure pipeline result is saved to metadata store for UI visibility
            # The pipeline should have already saved via _save_run, but we ensure it's in the UI's store
            if pipeline_result:
                try:
                    # Get the global metadata store used by UI (same as pipeline should use)
                    from flowyml.ui.backend.dependencies import get_store

                    # Get the UI's metadata store
                    ui_store = get_store()

                    # Also ensure the pipeline's metadata store is the same instance/path
                    # If the pipeline used a different store, sync to UI store

                    # Check if run is already in UI store
                    existing_run = ui_store.load_run(pipeline_result.run_id)
                    if not existing_run:
                        # Run wasn't saved to UI store, save it now
                        # Build comprehensive metadata
                        metadata = {
                            "run_id": pipeline_result.run_id,
                            "pipeline_name": pipeline_result.pipeline_name,
                            "status": "completed" if pipeline_result.success else "failed",
                            "start_time": pipeline_result.start_time.isoformat(),
                            "end_time": pipeline_result.end_time.isoformat() if pipeline_result.end_time else None,
                            "duration": pipeline_result.duration_seconds,
                            "success": pipeline_result.success,
                            "scheduled": True,  # Mark as scheduled run
                            "schedule_name": schedule.pipeline_name,
                            "steps": {
                                name: {
                                    "success": result.success,
                                    "duration": result.duration_seconds,
                                    "cached": result.cached,
                                    "retries": result.retries,
                                    "error": result.error,
                                }
                                for name, result in pipeline_result.step_results.items()
                            },
                        }

                        # Add outputs if available
                        if pipeline_result.outputs:
                            metadata["outputs"] = {
                                k: str(v)[:200] if not isinstance(v, (dict, list)) else str(v)[:200]
                                for k, v in pipeline_result.outputs.items()
                            }

                        ui_store.save_run(pipeline_result.run_id, metadata)
                        logger.info(f"✅ Saved scheduled run {pipeline_result.run_id} to UI metadata store")
                    else:
                        # Update existing run to mark as scheduled
                        if not existing_run.get("scheduled"):
                            existing_run["scheduled"] = True
                            existing_run["schedule_name"] = schedule.pipeline_name
                            ui_store.save_run(pipeline_result.run_id, existing_run)
                            logger.debug(f"Updated run {pipeline_result.run_id} to mark as scheduled")
                except Exception as e:
                    logger.warning(f"Failed to save scheduled run to UI metadata store: {e}", exc_info=True)

            if self.config.distributed:
                self._lock.release(schedule.pipeline_name)

            if self._persistence:
                self._persistence.save_schedule(schedule)
                self._persistence.save_execution(execution)

        # Calculate next run
        self._calculate_next_run(schedule)
        if self._persistence:
            self._persistence.save_schedule(schedule)

    def get_history(self, schedule_name: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get execution history for a schedule."""
        if self._persistence:
            return self._persistence.get_history(schedule_name, limit)
        return []

    def _calculate_next_run(self, schedule: Schedule) -> None:
        """Calculate next run time."""
        if pytz:
            tz = pytz.timezone(schedule.timezone)
            now = datetime.now(tz)
        else:
            now = datetime.now()

        if schedule.schedule_type == "daily":
            schedule.next_run += timedelta(days=1)
        elif schedule.schedule_type == "hourly":
            schedule.next_run += timedelta(hours=1)
        elif schedule.schedule_type == "interval":
            interval = int(schedule.schedule_value)
            schedule.next_run = now + timedelta(seconds=interval)
        elif schedule.schedule_type == "cron" and croniter:
            cron = croniter(schedule.schedule_value, now)
            schedule.next_run = cron.get_next(datetime)

    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        # Load persisted schedules on startup
        if self._persistence:
            loaded = self._persistence.load_schedules(self._pipeline_funcs)
            self.schedules.update(loaded)

        while self.running:
            self.metrics.last_heartbeat = datetime.now()

            if pytz:
                # Check schedules in their respective timezones
                for _name, schedule in self.schedules.items():
                    if not schedule.enabled or not schedule.next_run:
                        continue

                    tz = pytz.timezone(schedule.timezone)
                    now = datetime.now(tz)

                    if schedule.next_run <= now:
                        threading.Thread(target=self._run_pipeline, args=(schedule,)).start()
            else:
                now = datetime.now()
                for _name, schedule in self.schedules.items():
                    if schedule.enabled and schedule.next_run and schedule.next_run <= now:
                        threading.Thread(target=self._run_pipeline, args=(schedule,)).start()

            time.sleep(self.config.check_interval_seconds)

    def start(self, blocking: bool = False) -> None:
        """Start the scheduler."""
        if self.running:
            return

        self.running = True
        if blocking:
            self._scheduler_loop()
        else:
            self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        if self._thread:
            self._thread.join()

    def list_schedules(self) -> list[Schedule]:
        """List all schedules."""
        return list(self.schedules.values())

    def health_check(self) -> dict[str, Any]:
        """Get scheduler health status."""
        return {
            "status": "running" if self.running else "stopped",
            "num_schedules": len(self.schedules),
            "enabled_schedules": sum(1 for s in self.schedules.values() if s.enabled),
            "metrics": self.metrics.to_dict(),
            "next_runs": [
                {
                    "name": s.pipeline_name,
                    "next_run": s.next_run.isoformat() if s.next_run else None,
                }
                for s in sorted(self.schedules.values(), key=lambda x: x.next_run or datetime.max)[:5]
            ],
        }

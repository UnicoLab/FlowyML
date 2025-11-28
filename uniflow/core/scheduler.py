"""Pipeline scheduling and automation."""

import contextlib
import json
import logging
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from uniflow.core.scheduler_config import SchedulerConfig

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
    completed_at: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None
    duration_seconds: Optional[float] = None


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
    """Persist schedules to SQLite database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path.cwd() / ".uniflow_scheduler.db")
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedules (
                    name TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_name TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    success BOOLEAN,
                    error TEXT,
                    duration_seconds REAL,
                    FOREIGN KEY(schedule_name) REFERENCES schedules(name)
                )
                """,
            )

    def save_schedule(self, schedule: Schedule) -> None:
        """Save schedule to database."""
        data = schedule.to_dict()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO schedules (name, data) VALUES (?, ?)",
                (schedule.pipeline_name, json.dumps(data)),
            )

    def load_schedules(self, pipeline_funcs: dict[str, Callable]) -> dict[str, Schedule]:
        """Load all schedules from database."""
        schedules = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name, data FROM schedules")
            for name, data_json in cursor:
                try:
                    data = json.loads(data_json)
                    if name in pipeline_funcs:
                        schedules[name] = Schedule.from_dict(data, pipeline_funcs[name])
                except Exception as e:
                    logger.error(f"Failed to load schedule {name}: {e}")
        return schedules

    def delete_schedule(self, name: str) -> None:
        """Delete schedule from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM schedules WHERE name = ?", (name,))
            conn.execute("DELETE FROM executions WHERE schedule_name = ?", (name,))

    def save_execution(self, execution: ScheduleExecution) -> None:
        """Save execution record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO executions
                (schedule_name, started_at, completed_at, success, error, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    execution.schedule_name,
                    execution.started_at,
                    execution.completed_at,
                    execution.success,
                    execution.error,
                    execution.duration_seconds,
                ),
            )

    def get_history(self, schedule_name: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get execution history for a schedule."""
        history = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT started_at, completed_at, success, error, duration_seconds
                FROM executions
                WHERE schedule_name = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (schedule_name, limit),
            )
            for row in cursor:
                history.append(
                    {
                        "started_at": row[0],
                        "completed_at": row[1],
                        "success": bool(row[2]),
                        "error": row[3],
                        "duration_seconds": row[4],
                    },
                )
        return history


class DistributedLock:
    """Distributed lock for coordinating multiple scheduler instances."""

    def __init__(self, backend: str = "file", redis_url: Optional[str] = None):
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
            lock_key = f"uniflow:scheduler:lock:{schedule_name}"
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
            lock_key = f"uniflow:scheduler:lock:{schedule_name}"
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
        config: Optional[SchedulerConfig] = None,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
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
            # Re-initialize DB to clear it
            db_path = Path(self._persistence.db_path)
            if db_path.exists():
                db_path.unlink()
            self._persistence._init_db()

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

        try:
            logger.info(f"Starting scheduled run: {schedule.pipeline_name}")
            schedule.pipeline_func()
            execution.success = True
            schedule.last_run = datetime.now(pytz.timezone(schedule.timezone)) if pytz else datetime.now()

            if self.on_success:
                self.on_success(schedule, execution)
        except Exception as e:
            logger.error(f"Schedule {schedule.pipeline_name} failed: {e}")
            execution.error = str(e)
            if self.on_failure:
                self.on_failure(schedule, execution, e)
        finally:
            execution.completed_at = datetime.now()
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            self.metrics.update(execution)

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

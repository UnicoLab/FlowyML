"""Pipeline scheduling and automation."""

import time
import threading
from typing import Any
from collections.abc import Callable
from datetime import datetime, timedelta
from dataclasses import dataclass


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


class PipelineScheduler:
    """Schedule pipelines to run automatically.

    Examples:
        >>> scheduler = PipelineScheduler()
        >>> # Run daily at 2am
        >>> scheduler.schedule_daily(name="daily_training", pipeline_func=training_pipeline, hour=2)
        >>> # Run every 6 hours
        >>> scheduler.schedule_interval(name="data_refresh", pipeline_func=refresh_pipeline, hours=6)
        >>> scheduler.start()
    """

    def __init__(self):
        self.schedules: dict[str, Schedule] = {}
        self.running = False
        self._thread = None

    def schedule_daily(
        self,
        name: str,
        pipeline_func: Callable,
        hour: int = 0,
        minute: int = 0,
        context: dict[str, Any] | None = None,
    ):
        """Schedule pipeline to run daily at a specific time."""
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
        )
        self.schedules[name] = schedule
        return schedule

    def schedule_interval(
        self,
        name: str,
        pipeline_func: Callable,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        context: dict[str, Any] | None = None,
    ):
        """Schedule pipeline to run at regular intervals."""
        interval_seconds = hours * 3600 + minutes * 60 + seconds
        next_run = datetime.now() + timedelta(seconds=interval_seconds)

        schedule = Schedule(
            pipeline_name=name,
            schedule_type="interval",
            schedule_value=str(interval_seconds),
            pipeline_func=pipeline_func,
            context=context,
            next_run=next_run,
        )
        self.schedules[name] = schedule
        return schedule

    def schedule_hourly(
        self,
        name: str,
        pipeline_func: Callable,
        minute: int = 0,
        context: dict[str, Any] | None = None,
    ):
        """Schedule pipeline to run hourly."""
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
        )
        self.schedules[name] = schedule
        return schedule

    def unschedule(self, name: str) -> None:
        """Remove a scheduled pipeline."""
        if name in self.schedules:
            del self.schedules[name]

    def enable(self, name: str) -> None:
        """Enable a schedule."""
        if name in self.schedules:
            self.schedules[name].enabled = True

    def disable(self, name: str) -> None:
        """Disable a schedule."""
        if name in self.schedules:
            self.schedules[name].enabled = False

    def _run_pipeline(self, schedule: Schedule) -> None:
        """Run a scheduled pipeline."""
        try:
            schedule.pipeline_func()
            schedule.last_run = datetime.now()
        except Exception:
            pass

        # Calculate next run
        if schedule.schedule_type == "daily":
            schedule.next_run += timedelta(days=1)
        elif schedule.schedule_type == "hourly":
            schedule.next_run += timedelta(hours=1)
        elif schedule.schedule_type == "interval":
            interval = int(schedule.schedule_value)
            schedule.next_run = datetime.now() + timedelta(seconds=interval)

    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self.running:
            now = datetime.now()

            for _name, schedule in self.schedules.items():
                if schedule.enabled and schedule.next_run and schedule.next_run <= now:
                    # Run in a separate thread to avoid blocking
                    threading.Thread(target=self._run_pipeline, args=(schedule,)).start()

            time.sleep(10)  # Check every 10 seconds

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

    def list_schedules(self):
        """List all schedules."""
        if not self.schedules:
            return []

        for _name, schedule in self.schedules.items():
            if schedule.last_run:
                pass

        return list(self.schedules.values())

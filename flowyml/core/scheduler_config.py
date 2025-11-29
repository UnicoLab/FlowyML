"""Scheduler configuration."""

import os
from typing import Optional
from pydantic import BaseModel


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""

    persist_schedules: bool = True
    db_path: Optional[str] = None
    distributed: bool = False
    lock_backend: str = "file"  # "file", "redis"
    redis_url: Optional[str] = None
    check_interval_seconds: int = 10
    max_concurrent_runs: int = 5
    timezone: str = "UTC"

    @classmethod
    def from_env(cls) -> "SchedulerConfig":
        """Load from environment variables."""
        return cls(
            persist_schedules=os.getenv("FLOWYML_SCHEDULER_PERSIST", "true").lower() == "true",
            db_path=os.getenv("FLOWYML_SCHEDULER_DB_PATH"),
            distributed=os.getenv("FLOWYML_SCHEDULER_DISTRIBUTED", "false").lower() == "true",
            lock_backend=os.getenv("FLOWYML_SCHEDULER_LOCK_BACKEND", "file"),
            redis_url=os.getenv("FLOWYML_SCHEDULER_REDIS_URL"),
            check_interval_seconds=int(os.getenv("FLOWYML_SCHEDULER_CHECK_INTERVAL", "10")),
            max_concurrent_runs=int(os.getenv("FLOWYML_SCHEDULER_MAX_CONCURRENT", "5")),
            timezone=os.getenv("FLOWYML_SCHEDULER_TIMEZONE", "UTC"),
        )

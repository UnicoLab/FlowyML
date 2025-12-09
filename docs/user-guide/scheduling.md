# Pipeline Scheduling ⏰

Automate pipeline execution so you never miss a deadline.

> [!NOTE]
> **What you'll learn**: How to schedule pipelines for recurring execution with zero manual intervention
>
> **Key insight**: Manual pipeline execution doesn't scale. Scheduling turns ad-hoc jobs into reliable automation.

## Why Scheduling Matters

**Without scheduling**:
- **Manual overhead**: "Did someone run the daily ETL?"
- **Missed deadlines**: Forgetting to run the weekly report
- **No reliability**: Pipelines run only when someone remembers

**With flowyml scheduling**:
- **Zero manual work**: Pipelines run automatically
- **Multi-timezone**: Run at 9 AM local time for each region
- **Fault-tolerant**: Survives restarts, prevents duplicate runs

## Decision Guide: Scheduling Strategy

| Use Case | Schedule Type | Example |
|----------|---------------|----------|
| **Business Reports** | `Daily` at specific time | "Run sales report at 8 AM" |
| **Data Sync** | `Interval` (minutes/hours) | "Poll API every 15 minutes" |
| **Complex Timing** | `Cron` expression | "Every weekday at 9 AM, except holidays" |
| **High Frequency** | `Hourly` at specific minute | "Update cache at :00 past each hour" |

## Overview ℹ️

The `PipelineScheduler` provides:
- **Cron schedules**: Complex schedules using standard cron syntax
- **Daily schedules**: Run at specific times each day
- **Hourly schedules**: Run at specific minute each hour
- **Interval schedules**: Run at regular intervals
- **Timezone support**: Schedule in any timezone
- **Persistence**: Schedules survive restarts (SQLAlchemy-backed SQLite database)
- **Distributed**: Coordinate across multiple servers (Redis/File locking)
- **Execution History**: Track all scheduled run executions with metadata

## Quick Start 🚀

```python
from flowyml import Pipeline, PipelineScheduler, step

# Define pipeline
@step(outputs=["data"])
def fetch_data():
    return api.get_daily_data()

pipeline = Pipeline("daily_etl")
pipeline.add_step(fetch_data)

# Create scheduler (persistence enabled by default)
scheduler = PipelineScheduler()

# Schedule for daily execution at 2 AM New York time
scheduler.schedule_daily(
    name="daily_etl_job",
    pipeline_func=lambda: pipeline.run(),
    hour=2,
    minute=0,
    timezone="America/New_York"
)

# Start the scheduler
scheduler.start()
```

## Schedule Types 📅

### Cron Schedule (New!)

Use standard cron expressions for complex schedules. Requires `croniter`.

```python
# Run every weekday at 9 AM
scheduler.schedule_cron(
    name="weekday_report",
    pipeline_func=run_report,
    cron_expression="0 9 * * 1-5",
    timezone="Europe/London"
)

# Run on the first day of every month
scheduler.schedule_cron(
    name="monthly_billing",
    pipeline_func=run_billing,
    cron_expression="0 0 1 * *",
    timezone="UTC"
)
```

### Daily Schedule

Run at a specific time each day.

```python
scheduler.schedule_daily(
    name="morning_report",
    pipeline_func=run_morning_pipeline,
    hour=9,      # 9 AM
    minute=30,   # 9:30 AM
    timezone="Asia/Tokyo"
)
```

### Hourly Schedule

Run at a specific minute each hour.

```python
scheduler.schedule_hourly(
    name="hourly_sync",
    pipeline_func=run_sync_pipeline,
    minute=15    # Run at :15 past each hour (1:15, 2:15, 3:15, ...)
)
```

### Interval Schedule

Run at regular intervals.

```python
# Run every 30 minutes
scheduler.schedule_interval(
    name="frequent_check",
    pipeline_func=run_check_pipeline,
    minutes=30
)
```

## Advanced Features ⚡

### Persistence

Schedules are automatically persisted to a local SQLite database (`.flowyml_scheduler.db`) using SQLAlchemy. This ensures that schedules are not lost if the application restarts and provides better type safety and database portability.

**Technical Details:**
- Uses SQLAlchemy ORM for all database operations (no raw SQL queries)
- Supports SQLite by default, with easy migration to PostgreSQL if needed
- Automatic schema creation and migration
- Transaction-safe operations

To configure persistence:

```python
from flowyml.core.scheduler_config import SchedulerConfig

config = SchedulerConfig(
    persist_schedules=True,
    db_path="/path/to/scheduler.db"
)
scheduler = PipelineScheduler(config=config)
```

### Distributed Scheduling

For multi-server deployments, flowyml supports distributed locking to prevent duplicate executions.

**File-based Locking (Default)**: Good for single-machine, multi-process setups.
**Redis Locking**: Recommended for multi-server setups.

```python
config = SchedulerConfig(
    distributed=True,
    lock_backend="redis",
    redis_url="redis://localhost:6379/0"
)
scheduler = PipelineScheduler(config=config)
```

### Timezone Support

All schedule methods accept a `timezone` argument. Requires `pytz`.

```python
scheduler.schedule_daily(
    "global_sync",
    run_sync,
    hour=0,
    timezone="UTC"
)
```

### Monitoring & Health

The scheduler tracks metrics and health status.

```python
# Get health status
health = scheduler.health_check()
print(f"Status: {health['status']}")
print(f"Success Rate: {health['metrics']['success_rate']:.1%}")
```

### Execution History

The scheduler automatically tracks execution history for all scheduled runs, including:
- Start and completion times
- Success/failure status
- Duration
- Error messages (if any)
- Run IDs (for linking to pipeline runs in the UI)

```python
# Get execution history for a schedule
history = scheduler.get_history("daily_etl_job", limit=50)

for execution in history:
    status = "✅" if execution["success"] else "❌"
    print(f"{status} {execution['started_at']} - {execution['duration_seconds']:.2f}s")
    if execution.get("run_id"):
        print(f"   Run ID: {execution['run_id']}")
```

## Managing Schedules 🛠️

### List All Schedules

```python
schedules = scheduler.list_schedules()

for schedule in schedules:
    status = "✅ Enabled" if schedule.enabled else "⏸️ Paused"
    print(f"{status} {schedule.pipeline_name}")
    print(f"  Type: {schedule.schedule_type}")
    print(f"  Next run: {schedule.next_run} ({schedule.timezone})")
```

### Enable/Disable/Remove

```python
# Pause
scheduler.disable("daily_etl_job")

# Resume
scheduler.enable("daily_etl_job")

# Remove
scheduler.unschedule("daily_etl_job")

# Clear all
scheduler.clear()
```

## API Integration 🔌

The scheduler is fully integrated with the flowyml Backend API.

**Endpoints**:
- `GET /api/schedules`: List all schedules
- `POST /api/schedules`: Create a new schedule
- `GET /api/scheduler/health`: Get scheduler health metrics
- `POST /api/schedules/{name}/enable`: Enable schedule
- `POST /api/schedules/{name}/disable`: Disable schedule
- `DELETE /api/schedules/{name}`: Delete schedule

## Deployment 🚀

### Docker with Persistence

Mount a volume to persist the scheduler database.

```dockerfile
VOLUME /app/.flowyml_scheduler.db
CMD ["python", "scheduler.py"]
```

### Environment Variables

Configure the scheduler via environment variables:

- `flowyml_SCHEDULER_PERSIST`: "true"/"false"
- `flowyml_SCHEDULER_DB_PATH`: Path to SQLite DB
- `flowyml_SCHEDULER_DISTRIBUTED`: "true"/"false"
- `flowyml_SCHEDULER_REDIS_URL`: Redis connection string
- `flowyml_SCHEDULER_TIMEZONE`: Default timezone

## API Reference 📚

### PipelineScheduler

```python
PipelineScheduler(config: Optional[SchedulerConfig] = None)
```

**Methods**:
- `schedule_cron(name, func, cron_expression, timezone="UTC")` - Schedule using cron expression
- `schedule_daily(name, func, hour, minute, timezone="UTC")` - Schedule daily at specific time
- `schedule_hourly(name, func, minute, timezone="UTC")` - Schedule hourly at specific minute
- `schedule_interval(name, func, hours, minutes, seconds, timezone="UTC")` - Schedule at intervals
- `health_check() -> Dict` - Get scheduler health and metrics
- `get_history(schedule_name, limit=50) -> List[Dict]` - Get execution history for a schedule
- `list_schedules() -> List[Schedule]` - List all schedules
- `enable(name)` - Enable a schedule
- `disable(name)` - Disable a schedule
- `unschedule(name)` - Remove a schedule
- `clear()` - Remove all schedules
- `start()` - Start the scheduler
- `stop()` - Stop the scheduler

### SchedulerConfig

Configuration object for the scheduler.

- `persist_schedules: bool`
- `db_path: str`
- `distributed: bool`
- `lock_backend: str`
- `redis_url: str`
- `timezone: str`

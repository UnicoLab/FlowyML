# Pipeline Scheduling

Automate pipeline execution with flexible scheduling options.

## Overview

The `PipelineScheduler` allows you to run pipelines automatically at specified times or intervals:
- **Daily schedules**: Run at specific times each day
- **Hourly schedules**: Run at specific minute each hour
- **Interval schedules**: Run at regular intervals
- **Manual control**: Enable/disable schedules dynamically

## Quick Start

```python
from uniflow import Pipeline, PipelineScheduler, step

# Define pipeline
@step(outputs=["data"])
def fetch_data():
    return api.get_daily_data()

pipeline = Pipeline("daily_etl")
pipeline.add_step(fetch_data)

#Create scheduler
scheduler = PipelineScheduler()

# Schedule for daily execution at 2 AM
scheduler.schedule_daily(
    name="daily_etl_job",
    pipeline_func=lambda: pipeline.run(),
    hour=2,
    minute=0
)

# Start the scheduler
scheduler.start()

# Scheduler runs in background
# Keep your application running...
```

## Schedule Types

### Daily Schedule

Run at a specific time each day.

```python
scheduler.schedule_daily(
    name="morning_report",
    pipeline_func=run_morning_pipeline,
    hour=9,      # 9 AM
    minute=30    # 9:30 AM
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

# Run every 5 seconds
scheduler.schedule_interval(
    name="realtime_monitor",
    pipeline_func=run_monitor_pipeline,
    seconds=5
)

# Run every 2 hours
scheduler.schedule_interval(
    name="bi_hourly_task",
    pipeline_func=run_task,
    hours=2
)
```

## Managing Schedules

### List All Schedules

```python
schedules = scheduler.list_schedules()

for schedule in schedules:
    status = "✅ Enabled" if schedule.enabled else "⏸️ Paused"
    print(f"{status} {schedule.pipeline_name}")
    print(f"  Type: {schedule.schedule_type}")
    print(f"  Next run: {schedule.next_run}")
```

### Enable/Disable Schedules

```python
# Pause a schedule
scheduler.disable("daily_etl_job")

# Resume a schedule
scheduler.enable("daily_etl_job")
```

### Remove Schedules

```python
# Remove a specific schedule
scheduler.unschedule("daily_etl_job")

# Remove all schedules
scheduler.clear()
```

### Stop Scheduler

```python
# Stop the background thread
scheduler.stop()
```

## Advanced Usage

### Schedule with Context

Pass context data to pipeline runs.

```python
def run_with_config():
    context = {
        "environment": "production",
        "retry_count": 3
    }
    return pipeline.run(context=context)

scheduler.schedule_daily(
    name="prod_pipeline",
    pipeline_func=run_with_config,
    hour=0
)
```

### Multiple Pipelines

Schedule different pipelines independently.

```python
# ETL pipeline - daily at 2 AM
scheduler.schedule_daily(
    name="etl",
    pipeline_func=lambda: etl_pipeline.run(),
    hour=2
)

# Reporting - daily at 9 AM
scheduler.schedule_daily(
    name="reports",
    pipeline_func=lambda: reporting_pipeline.run(),
    hour=9
)

# Monitoring - every 15 minutes
scheduler.schedule_interval(
    name="monitor",
    pipeline_func=lambda: monitor_pipeline.run(),
    minutes=15
)
```

### Conditional Execution

```python
def run_if_needed():
    if should_run_pipeline():
        return pipeline.run()
    else:
        print("Skipping this run")
        return None

scheduler.schedule_hourly(
    name="conditional",
    pipeline_func=run_if_needed,
    minute=0
)
```

### Error Handling

```python
def safe_pipeline_run():
    try:
        result = pipeline.run()
        if not result.success:
            send_alert(f"Pipeline failed: {result.error}")
        return result
    except Exception as e:
        send_alert(f"Pipeline crashed: {e}")
        return None

scheduler.schedule_daily(
    name="safe_etl",
    pipeline_func=safe_pipeline_run,
    hour=3
)
```

## Integration with Projects

```python
from uniflow import Project, PipelineScheduler

project = Project("automated_ml")
scheduler = PipelineScheduler()

def run_project_pipeline():
    pipeline = project.create_pipeline("training")
    pipeline.add_step(train_model)
    return pipeline.run()

scheduler.schedule_daily(
    name=f"{project.name}_training",
    pipeline_func=run_project_pipeline,
    hour=2
)
```

## Integration with Versioning

```python
from uniflow import VersionedPipeline, PipelineScheduler

def run_versioned_pipeline():
    vp = VersionedPipeline("production_model")
    vp.version = "v2.0.0"

    # Add steps
    vp.add_step(load_data)
    vp.add_step(train)

    # Save version before running
    vp.save_version(metadata={"scheduled_run": True})

    # Run
    result = vp.run()

    # Log result
    print(f"Version {vp.version}: {result.success}")
    return result

scheduler.schedule_daily(
    name="versioned_training",
    pipeline_func=run_versioned_pipeline,
    hour=2
)
```

## Best Practices

### 1. Use Descriptive Names

```python
# ✅ Good
scheduler.schedule_daily("customer_churn_prediction_daily", ...)

# ❌ Bad
scheduler.schedule_daily("job1", ...)
```

### 2. Handle Failures Gracefully

```python
def resilient_pipeline():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return pipeline.run()
        except Exception as e:
            if attempt == max_retries - 1:
                send_alert(f"Pipeline failed after {max_retries} attempts")
                raise
            time.sleep(60)  # Wait before retry
```

### 3. Log Execution Details

```python
import logging

logger = logging.getLogger(__name__)

def logged_pipeline():
    logger.info("Starting scheduled pipeline run")
    start = time.time()

    result = pipeline.run()

    duration = time.time() - start
    logger.info(f"Pipeline completed in {duration:.1f}s - Success: {result.success}")

    return result

scheduler.schedule_daily("logged_job", logged_pipeline, hour=2)
```

### 4. Monitor Schedule Health

```python
def monitor_schedules():
    schedules = scheduler.list_schedules()

    for schedule in schedules:
        if not schedule.enabled:
            alert(f"Schedule {schedule.pipeline_name} is disabled")

        if schedule.last_run:
            time_since_run = datetime.now() - schedule.last_run
            if time_since_run > timedelta(days=2):
                alert(f"Schedule {schedule.pipeline_name} hasn't run in {time_since_run}")

# Run monitoring periodically
scheduler.schedule_hourly("monitor_schedules", monitor_schedules, minute=0)
```

### 5. Use Separate Scheduler Process

```python
# scheduler.py
from uniflow import PipelineScheduler

def main():
    scheduler = PipelineScheduler()

    # Load all schedules
    scheduler.schedule_daily("etl", run_etl, hour=2)
    scheduler.schedule_hourly("sync", run_sync, minute=15)

    # Start and keep running
    scheduler.start()

    # Keep process alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.stop()

if __name__ == "__main__":
    main()
```

## API Integration

Using with the PipelineRegistry for API-driven scheduling:

```python
from uniflow import pipeline_registry, register_pipeline, PipelineScheduler

# Register pipelines
@register_pipeline("daily_etl")
def create_etl_pipeline():
    pipeline = Pipeline("etl")
    pipeline.add_step(extract)
    pipeline.add_step(transform)
    pipeline.add_step(load)
    return pipeline

# Schedule from registry
scheduler = PipelineScheduler()

pipeline_factory = pipeline_registry.get("daily_etl")
scheduler.schedule_daily(
    name="etl_job",
    pipeline_func=lambda: pipeline_factory().run(),
    hour=2
)
```

## API Reference

### PipelineScheduler

```python
PipelineScheduler()
```

**Methods**:
- `schedule_daily(name, pipeline_func, hour, minute=0, context=None) -> Schedule`
- `schedule_hourly(name, pipeline_func, minute=0, context=None) -> Schedule`
- `schedule_interval(name, pipeline_func, hours=0, minutes=0, seconds=0, context=None) -> Schedule`
- `list_schedules() -> List[Schedule]`
- `enable(name)` - Enable a schedule
- `disable(name)` - Disable a schedule
- `unschedule(name)` - Remove a schedule
- `clear()` - Remove all schedules
- `start()` - Start scheduler thread
- `stop()` - Stop scheduler thread

### Schedule

**Attributes**:
- `pipeline_name: str` - Schedule name
- `schedule_type: str` - Type ('daily', 'hourly', 'interval')
- `schedule_value: str` - Schedule configuration
- `pipeline_func: Callable` - Function to execute
- `enabled: bool` - Whether schedule is active
- `last_run: Optional[datetime]` - Last execution time
- `next_run: datetime` - Next scheduled execution
- `context: Optional[Dict]` - Context data

## Deployment

### Systemd Service (Linux)

```ini
# /etc/systemd/system/uniflow-scheduler.service
[Unit]
Description=UniFlow Pipeline Scheduler
After=network.target

[Service]
Type=simple
User=uniflow
WorkingDirectory=/app
ExecStart=/usr/bin/python /app/scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker

```dockerfile
FROM python:3.9

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY scheduler.py .
COPY pipelines/ pipelines/

CMD ["python", "scheduler.py"]
```

### Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: uniflow-pipeline
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: pipeline
            image: myorg/uniflow-pipelines:latest
            command: ["python", "-c", "from pipelines import run_daily; run_daily()"]
          restartPolicy: OnFailure
```

## FAQ

**Q: Can I schedule the same pipeline multiple times?**
A: Yes! Use different schedule names:
```python
scheduler.schedule_daily("etl_morning", run_etl, hour=6)
scheduler.schedule_daily("etl_evening", run_etl, hour=18)
```

**Q: What happens if a run takes longer than the interval?**
A: The next run waits until the current one completes. Runs don't overlap.

**Q: Can I see past execution history?**
A: Use the metadata store to query past runs:
```python
from uniflow.storage.metadata import SQLiteMetadataStore

store = SQLiteMetadataStore()
runs = store.list_runs(pipeline_name="etl", limit=100)
```

**Q: How do I update a schedule?**
A: Unschedule and reschedule:
```python
scheduler.unschedule("old_job")
scheduler.schedule_daily("old_job", new_func, hour=3)
```

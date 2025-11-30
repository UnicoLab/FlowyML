# Migration Guide: FlowyML 0.x to 1.0

This guide covers the changes introduced in the orchestration refactor and how to update your existing code.

## Key Changes

1. **Orchestrator Separation**: `Pipeline.run()` now delegates to an `Orchestrator`.
2. **Async Remote Execution**: Cloud orchestrators now return `SubmissionResult` instead of blocking.
3. **ExecutionStatus Enum**: Standardized status strings.
4. **Lifecycle Hooks**: New system for `on_pipeline_start`, `on_step_end`, etc.

## Migrating Pipeline Code

### 1. Pipeline Execution

**Old:**
```python
# Pipeline.run() contained all execution logic
pipeline.run()
```

**New:**
The API remains the same for local execution, but under the hood it uses `LocalOrchestrator`.

```python
# Still works!
pipeline.run()
```

### 2. Remote Execution

**Old:**
```python
# Custom remote logic often blocked or returned raw strings
job_id = orchestrator.run_pipeline(pipeline)
```

**New:**
Returns a `SubmissionResult` object.

```python
submission = orchestrator.run_pipeline(pipeline, run_id="...")
print(f"Job ID: {submission.job_id}")

# If you need to wait:
submission.wait_for_completion()
```

### 3. Status Checking

**Old:**
Raw strings like "RUNNING", "SUCCEEDED" (provider specific).

**New:**
Use `ExecutionStatus` enum.

```python
from flowyml.core.execution_status import ExecutionStatus

status = orchestrator.get_run_status(job_id)

if status == ExecutionStatus.RUNNING:
    print("Still running...")
elif status.is_successful:
    print("Done!")
```

## Advanced Features

### Retry Policies

You can now configure retries at the orchestrator level:

```python
from flowyml.core.retry_policy import OrchestratorRetryPolicy

policy = OrchestratorRetryPolicy(max_attempts=3)
# Pass to orchestrator (implementation dependent)
```

### Scheduling

Schedule pipelines directly:

```python
# Run every hour
pipeline.schedule(schedule_type='hourly', value=0)
```

### Observability

Hook into metrics:

```python
from flowyml.core.observability import set_metrics_collector, ConsoleMetricsCollector

set_metrics_collector(ConsoleMetricsCollector())
```

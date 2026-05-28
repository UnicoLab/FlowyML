---
title: Migration Guide — FlowyML 0.x → 1.0
description: Everything you need to upgrade from FlowyML 0.x to 1.0, including breaking changes, before/after code examples, and troubleshooting.
---

<div class="hero-section" markdown>

## 🔄 Migration Guide: FlowyML 0.x → 1.0

FlowyML 1.0 introduces a powerful new orchestration architecture, async remote execution, and a unified status model. This guide walks you through every breaking change and shows you exactly how to update your code.

<span class="feature-badge">🔀 Migration</span>
<span class="feature-badge">⚠️ Breaking Changes</span>
<span class="feature-badge">✅ Compatibility</span>

</div>

## Summary of Changes

FlowyML 1.0 is a **major release** that refactors the execution engine for better extensibility, cloud support, and observability. Here's what changed at a high level:

| Area | 0.x Behavior | 1.0 Behavior |
|------|-------------|--------------|
| **Execution engine** | Monolithic `Pipeline.run()` | Pluggable `Orchestrator` system |
| **Remote execution** | Blocking, raw return values | Async `SubmissionResult` objects |
| **Status tracking** | Provider-specific strings | Unified `ExecutionStatus` enum |
| **Lifecycle hooks** | Manual callbacks | Built-in `on_pipeline_start`, `on_step_end`, etc. |
| **Retry policies** | Not supported | `OrchestratorRetryPolicy` with configurable backoff |
| **Scheduling** | External (cron / Airflow) | Native `pipeline.schedule()` API |
| **Observability** | Logging only | Pluggable `MetricsCollector` system |

!!! danger "Breaking Changes"
    The following changes **will break** existing code if not addressed:

    1. **`Pipeline.run()` internals** — While the local API surface is unchanged, any code that subclassed `Pipeline` or monkey-patched `run()` must be updated to use the new `Orchestrator` interface.
    2. **Remote execution return types** — `orchestrator.run_pipeline()` now returns a `SubmissionResult` instead of a raw string or job ID.
    3. **Status strings** — Hard-coded status comparisons like `if status == "RUNNING"` must be replaced with the `ExecutionStatus` enum.
    4. **Hook registration** — Old-style callback registration is removed in favor of the new lifecycle hook system.

---

## Step-by-Step Migration

### 1. Pipeline Execution (Local)

**The good news:** For purely local pipelines, the API is **unchanged**. Under the hood, `Pipeline.run()` now delegates to a `LocalOrchestrator`, but your code doesn't need to change.

=== "Before (0.x)"

    ```python
    from flowyml import Pipeline, step

    @step(outputs=["result"])
    def process(data):
        return data * 2

    pipeline = Pipeline("my_pipeline")
    pipeline.add_step(process)

    # Pipeline.run() contained all execution logic internally
    result = pipeline.run()
    print(result.outputs["result"])
    ```

=== "After (1.0)"

    ```python
    from flowyml import Pipeline, step

    @step(outputs=["result"])
    def process(data):
        return data * 2

    pipeline = Pipeline("my_pipeline")
    pipeline.add_step(process)

    # Identical API — now uses LocalOrchestrator internally
    result = pipeline.run()
    print(result.outputs["result"])
    ```

!!! success "No Changes Required"
    If you only run pipelines locally with `pipeline.run()`, your code works as-is in 1.0.

---

### 2. Remote Execution

This is the **biggest breaking change**. Remote orchestrators now return a `SubmissionResult` object instead of blocking until completion.

=== "Before (0.x)"

    ```python
    # 0.x — Blocking call, returned a raw job ID string
    from flowyml import Pipeline
    from flowyml.orchestrators import RemoteOrchestrator

    orchestrator = RemoteOrchestrator(url="http://server:8000")

    # Blocked until pipeline finished — no way to cancel or check progress
    job_id = orchestrator.run_pipeline(pipeline)
    print(f"Job completed: {job_id}")
    ```

=== "After (1.0)"

    ```python
    # 1.0 — Non-blocking, returns a SubmissionResult
    from flowyml import Pipeline
    from flowyml.orchestrators import RemoteOrchestrator

    orchestrator = RemoteOrchestrator(url="http://server:8000")

    # Returns immediately with a SubmissionResult
    submission = orchestrator.run_pipeline(pipeline, run_id="my-run-001")

    # Access the job ID
    print(f"Job ID: {submission.job_id}")
    print(f"Status: {submission.status}")

    # If you need blocking behavior, explicitly wait:
    submission.wait_for_completion(timeout=3600)  # Wait up to 1 hour
    print(f"Final status: {submission.status}")
    print(f"Duration: {submission.duration_seconds:.1f}s")
    ```

!!! warning "Action Required"
    If you use remote orchestrators, you **must** update your code to handle `SubmissionResult` objects. The old blocking behavior is available via `submission.wait_for_completion()`.

#### SubmissionResult API

```python
class SubmissionResult:
    job_id: str                    # Unique job identifier
    status: ExecutionStatus        # Current execution status
    duration_seconds: float        # Elapsed time (if completed)
    outputs: dict                  # Pipeline outputs (if completed)
    error: Optional[str]           # Error message (if failed)

    def wait_for_completion(
        self,
        timeout: int = 3600,      # Max wait time in seconds
        poll_interval: int = 5    # Seconds between status checks
    ) -> "SubmissionResult": ...

    def cancel(self) -> bool: ...  # Cancel a running job
```

---

### 3. Status Checking

Raw status strings are replaced by a typed `ExecutionStatus` enum with convenience properties.

=== "Before (0.x)"

    ```python
    # 0.x — Raw strings, provider-specific and error-prone
    status = orchestrator.get_run_status(job_id)

    if status == "RUNNING":
        print("Still running...")
    elif status == "SUCCEEDED":
        print("Done!")
    elif status == "FAILED":
        print("Something went wrong")
    # What about "QUEUED"? "CANCELLING"? Easy to miss cases.
    ```

=== "After (1.0)"

    ```python
    # 1.0 — Typed enum with convenience properties
    from flowyml.core.execution_status import ExecutionStatus

    status = orchestrator.get_run_status(job_id)

    if status == ExecutionStatus.RUNNING:
        print("Still running...")
    elif status.is_successful:         # True for COMPLETED / SUCCEEDED
        print("Done!")
    elif status.is_failed:             # True for FAILED / ERROR
        print("Something went wrong")
    elif status.is_terminal:           # True for any final state
        print("Execution finished")
    elif status == ExecutionStatus.QUEUED:
        print("Waiting in queue...")
    ```

#### ExecutionStatus Enum Values

| Value | Terminal? | Description |
|-------|-----------|-------------|
| `QUEUED` | ❌ | Job submitted, waiting to start |
| `RUNNING` | ❌ | Job is actively executing |
| `COMPLETED` | ✅ | All steps finished successfully |
| `FAILED` | ✅ | One or more steps failed |
| `CANCELLED` | ✅ | Job was cancelled by the user |
| `TIMEOUT` | ✅ | Job exceeded the maximum allowed duration |

---

### 4. Lifecycle Hooks

The new lifecycle hook system replaces the old manual callback pattern.

=== "Before (0.x)"

    ```python
    # 0.x — Manual callback registration (removed in 1.0)
    def my_callback(event_type, data):
        if event_type == "step_complete":
            print(f"Step done: {data['step_name']}")

    pipeline.register_callback(my_callback)
    pipeline.run()
    ```

=== "After (1.0)"

    ```python
    # 1.0 — Structured lifecycle hooks with typed events
    from flowyml.core.hooks import PipelineHook

    class MyHook(PipelineHook):
        def on_pipeline_start(self, pipeline_name, run_id, context):
            print(f"🚀 Pipeline '{pipeline_name}' started (run: {run_id})")

        def on_step_start(self, step_name, inputs):
            print(f"  ▶ Step '{step_name}' starting...")

        def on_step_end(self, step_name, outputs, duration):
            print(f"  ✅ Step '{step_name}' done in {duration:.2f}s")

        def on_pipeline_end(self, pipeline_name, run_id, status, duration):
            print(f"🏁 Pipeline finished: {status} ({duration:.2f}s)")

        def on_error(self, step_name, error):
            print(f"  ❌ Step '{step_name}' failed: {error}")

    # Register hooks
    pipeline = Pipeline("my_pipeline", hooks=[MyHook()])
    pipeline.run()
    ```

---

## New Features in 1.0

### Retry Policies

Configure automatic retries with exponential backoff at the orchestrator level:

```python
from flowyml.core.retry_policy import OrchestratorRetryPolicy

policy = OrchestratorRetryPolicy(
    max_attempts=3,              # Retry up to 3 times
    initial_delay_seconds=10,    # Wait 10s before first retry
    backoff_multiplier=2.0,      # Double the delay each retry
    retryable_errors=["OOM", "Timeout"]  # Only retry specific errors
)

orchestrator = RemoteOrchestrator(
    url="http://server:8000",
    retry_policy=policy
)
```

### Native Scheduling

Schedule pipelines directly from code — no external scheduler needed:

```python
# Run every hour at minute 0
pipeline.schedule(schedule_type="hourly", value=0)

# Run daily at 3:00 AM UTC
pipeline.schedule(schedule_type="daily", value=3)

# Custom cron expression
pipeline.schedule(schedule_type="cron", value="0 */6 * * *")

# Weekly on Monday at 9 AM
pipeline.schedule(schedule_type="weekly", value="MON:09:00")
```

### Pluggable Observability

Hook into metrics and traces with a pluggable collector system:

```python
from flowyml.core.observability import (
    set_metrics_collector,
    ConsoleMetricsCollector,
    PrometheusMetricsCollector
)

# Development: log metrics to console
set_metrics_collector(ConsoleMetricsCollector())

# Production: export to Prometheus
set_metrics_collector(PrometheusMetricsCollector(
    endpoint="http://prometheus:9090",
    job_name="flowyml"
))
```

---

## Troubleshooting

!!! bug "Common Migration Issues"

### `AttributeError: 'str' object has no attribute 'job_id'`

**Cause:** You're treating the return value of `orchestrator.run_pipeline()` as a string (0.x behavior).

**Fix:** Update your code to use the `SubmissionResult` object:

```python
# ❌ Old pattern
job_id = orchestrator.run_pipeline(pipeline)

# ✅ New pattern
submission = orchestrator.run_pipeline(pipeline, run_id="...")
job_id = submission.job_id
```

### `ImportError: cannot import name 'register_callback'`

**Cause:** The `register_callback` method was removed in 1.0.

**Fix:** Migrate to lifecycle hooks (see [Section 4](#4-lifecycle-hooks) above).

### `TypeError: 'ExecutionStatus' object is not subscriptable`

**Cause:** Comparing `ExecutionStatus` with raw strings.

**Fix:** Use the enum values:

```python
# ❌ Won't work
if status == "RUNNING":

# ✅ Use the enum
from flowyml.core.execution_status import ExecutionStatus
if status == ExecutionStatus.RUNNING:
```

### `DeprecationWarning: Dict-style resources will be removed in 2.0`

**Cause:** Using the old `resources={"cpu": "2"}` dict format.

**Fix:** Migrate to `ResourceRequirements` (still works in 1.0, but plan for 2.0):

```python
# ⚠️ Deprecated (works in 1.0, removed in 2.0)
@step(resources={"cpu": "2", "memory": "4Gi"})

# ✅ New format
from flowyml.core.resources import ResourceRequirements
@step(resources=ResourceRequirements(cpu="2", memory="4Gi"))
```

### Pipeline runs hang indefinitely after upgrade

**Cause:** A custom `Pipeline` subclass is overriding the old `run()` internals.

**Fix:** Refactor to use the `Orchestrator` interface instead:

```python
# ❌ Old: subclassing Pipeline.run()
class MyPipeline(Pipeline):
    def run(self):
        # Custom logic here — breaks in 1.0
        ...

# ✅ New: custom orchestrator
from flowyml.orchestrators import LocalOrchestrator

class MyOrchestrator(LocalOrchestrator):
    def execute(self, pipeline, run_id, context):
        # Custom pre/post logic here
        return super().execute(pipeline, run_id, context)
```

---

## Migration Checklist

Use this checklist to track your migration progress:

- [ ] Update `flowyml` to version 1.0: `pip install flowyml>=1.0`
- [ ] Replace raw status string comparisons with `ExecutionStatus` enum
- [ ] Update remote execution code to handle `SubmissionResult`
- [ ] Migrate `register_callback()` calls to lifecycle hooks
- [ ] Replace dict-style `resources={}` with `ResourceRequirements`
- [ ] Test all pipelines locally with `pipeline.run()`
- [ ] Test remote pipelines with `submission.wait_for_completion()`
- [ ] Update CI/CD scripts that parse status strings
- [ ] Review custom `Pipeline` subclasses for compatibility
- [ ] Run full integration test suite

---

## What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 📖 User Guide

Explore the full capabilities of FlowyML 1.0 in the updated user guide.

[User Guide →](core/pipelines.md)

</div>

<div class="header-card" markdown>

### ⚡ Resources & GPU

Learn how to configure step-level compute resources and GPU allocation.

[Resources Guide →](resources.md)

</div>

<div class="header-card" markdown>

### 🚀 Deployment

Deploy your upgraded pipelines to Docker, Kubernetes, or the cloud.

[Deployment Guide →](deployment.md)

</div>

</div>

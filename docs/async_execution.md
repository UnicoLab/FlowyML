# Async Execution & Cloud Orchestration

FlowyML supports asynchronous execution for cloud orchestrators, allowing you to submit jobs to remote infrastructure without blocking your local process.

## Overview

When using a `RemoteOrchestrator` (like AWS Batch, SageMaker, Vertex AI, or Azure ML), the `run_pipeline` method returns a `SubmissionResult` object immediately after the job is successfully submitted.

```python
from flowyml.stacks.aws import AWSBatchOrchestrator

# Initialize remote orchestrator
orchestrator = AWSBatchOrchestrator(
    job_queue="my-queue",
    job_definition="my-job-def"
)

# Submit pipeline (non-blocking)
result = orchestrator.run_pipeline(pipeline, run_id="run-123")

print(f"🚀 Job submitted! ID: {result.job_id}")
```

## SubmissionResult

The `SubmissionResult` object provides handles to interact with the remote job:

- `job_id`: The unique identifier of the job in the remote system.
- `wait_for_completion()`: A method that blocks until the job finishes (polling status).
- `metadata`: Dictionary containing platform-specific details (e.g., region, dashboard URL).

### Waiting for Completion

If you need to wait for the result (e.g., in a CI/CD script):

```python
# Block until finished
result.wait_for_completion()
print("✅ Job completed")
```

## Job Control & Monitoring

You can monitor and control jobs using the orchestrator instance:

### Check Status

```python
status = orchestrator.get_run_status(result.job_id)
print(f"Current Status: {status}")  # e.g., ExecutionStatus.RUNNING
```

### Cancel Job

```python
orchestrator.stop_run(result.job_id)
print("🛑 Job cancelled")
```

## Supported Platforms

| Platform | Orchestrator Class | Status Tracking | Cancellation |
|----------|-------------------|-----------------|--------------|
| **AWS** | `AWSBatchOrchestrator` | ✅ | ✅ |
| **AWS** | `SageMakerOrchestrator` | ✅ | ✅ |
| **GCP** | `VertexAIOrchestrator` | ✅ | ✅ |
| **Azure** | `AzureMLOrchestrator` | ✅ | ✅ |

## Example: Monitoring Loop

You can build custom monitoring logic:

```python
import time

result = orchestrator.run_pipeline(pipeline, run_id="monitor-demo")

while True:
    status = orchestrator.get_run_status(result.job_id)
    print(f"Status: {status}")

    if status.is_finished:
        if status.is_successful:
            print("🎉 Success!")
        else:
            print("💥 Failed!")
        break

    time.sleep(30)
```

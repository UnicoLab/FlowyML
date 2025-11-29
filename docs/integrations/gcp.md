# Google Cloud Platform (GCP) ☁️

Scale your pipelines from local prototypes to production workloads on Google Cloud.

> [!NOTE]
> **What you'll learn**: How to run flowyml pipelines on Vertex AI and store data in GCS
>
> **Key insight**: Develop locally on your laptop, then flip a switch to run on a 100-GPU cluster in the cloud.

## Why Use GCP with flowyml?

**Local limitations**:
- **Memory**: "OOM Error" on large datasets
- **Compute**: Training takes days on a CPU
- **Storage**: Hard drive full of model checkpoints

**GCP advantages**:
- **Infinite Scale**: Spin up as many machines as you need
- **Managed Services**: Vertex AI handles the infrastructure
- **Unified Data**: Store everything in GCS, accessible from anywhere

## ☁️ GCS Artifact Store

Store your pipeline artifacts (datasets, models) in Google Cloud Storage. This makes them accessible to your team and production systems.

### Configuration

```bash
# Register a stack that uses GCS
flowyml stack register gcp-prod \
    --artifact-store gs://my-bucket/flowyml-artifacts \
    --metadata-store sqlite:///flowyml.db
```

## 🚀 Vertex AI Execution

Run your pipeline steps as Vertex AI Custom Jobs. flowyml handles the Dockerization and submission automatically.

### Real-World Pattern: Hybrid Execution

Develop locally, then deploy to Vertex AI for the heavy lifting.

```python
from flowyml import Pipeline
from flowyml.integrations.gcp import VertexAIOrchestrator

pipeline = Pipeline("training_pipeline")
# ... add steps ...

# Option 1: Run locally for debugging
# pipeline.run()

# Option 2: Run on Vertex AI for production
pipeline.run(
    orchestrator=VertexAIOrchestrator(
        project="my-gcp-project",
        location="us-central1",
        machine_type="n1-standard-16", # Powerful machine!
        accelerator_type="NVIDIA_TESLA_T4",
        accelerator_count=1
    )
)
```

> [!TIP]
> **Cost Control**: Vertex AI charges by the second. flowyml ensures resources are only provisioned while your steps are running.

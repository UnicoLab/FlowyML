---
title: Google Cloud Platform Integration — FlowyML
description: "Deploy FlowyML pipelines on GCP with Vertex AI, GCS artifact storage, and Cloud Run serving."
---

<div class="hero-section" markdown>

## ☁️ Google Cloud Platform Integration

Deploy FlowyML pipelines on GCP with Vertex AI, GCS artifact storage, and Cloud Run serving.

<span class="feature-badge">🤖 Vertex AI</span>
<span class="feature-badge">☁️ GCS</span>
<span class="feature-badge">🚀 Cloud Run</span>

</div>

# Google Cloud Platform (GCP) ☁️

Scale your pipelines from local prototypes to production workloads on Google Cloud.

!!! info "What you'll learn"
    How to run flowyml pipelines on Vertex AI and store data in GCS. Develop locally, then flip a switch to run on a 100-GPU cluster.

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

### Recommended: Stack-Based Execution (Automatic Orchestrator)

**The best practice is to use a GCP stack**, which automatically provides the orchestrator, executor, artifact store, and all other components. This is the core concept of stacks - they encapsulate all infrastructure configuration.

```python
from flowyml import Pipeline
from flowyml.stacks.gcp import GCPStack

# Create GCP stack with Vertex AI orchestrator
gcp_stack = GCPStack(
    name="production",
    project_id="my-gcp-project",
    region="us-central1",
    bucket_name="my-artifacts-bucket",
    service_account="my-sa@my-project.iam.gserviceaccount.com"
)

# Create pipeline with stack
pipeline = Pipeline("training_pipeline", stack=gcp_stack)
# ... add steps ...

# Run pipeline - automatically uses Vertex AI orchestrator from stack!
pipeline.run()
```

**Or use active stack from configuration:**

```python
from flowyml import Pipeline
from flowyml.stacks.registry import set_active_stack

# Set active stack (from flowyml.yaml or programmatically)
set_active_stack("gcp-production")

# Pipeline automatically uses active stack's orchestrator
pipeline = Pipeline("training_pipeline")
pipeline.add_step(...)
pipeline.run()  # Uses Vertex AI orchestrator from active stack!
```

### Alternative: Explicit Orchestrator Override

If you need to override the stack's orchestrator for a specific run:

```python
from flowyml import Pipeline
from flowyml.stacks.gcp import VertexAIOrchestrator

pipeline = Pipeline("training_pipeline")
# ... add steps ...

# Override orchestrator for this run only
pipeline.run(
    orchestrator=VertexAIOrchestrator(
        project_id="my-gcp-project",
        region="us-central1",
        service_account="my-sa@my-project.iam.gserviceaccount.com"
    )
)
```

!!! tip "Stack-Based is Better"
    Using a stack ensures all components (orchestrator, artifact store, metadata store, container registry) work together seamlessly.

!!! tip "Cost Control"
    Vertex AI charges by the second. flowyml ensures resources are only provisioned while your steps are running.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### ☁️ AWS Integration
Run FlowyML pipelines on AWS with SageMaker orchestration and S3 artifact storage.

[Explore →](aws.md)

</div>

<div class="header-card" markdown>

### ☁️ Azure Integration
Deploy on Azure with Azure ML, Blob Storage, and AKS orchestration.

[Learn more →](azure.md)

</div>

<div class="header-card" markdown>

### 🚀 Deployment
Learn about production deployment strategies and best practices.

[View Guide →](../deployment.md)

</div>

</div>

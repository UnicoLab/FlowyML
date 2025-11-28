# Google Cloud Platform (GCP) Integration

UniFlow allows you to run pipelines on GCP Vertex AI or use GCS as an artifact store.

## ☁️ GCS Artifact Store

Store your pipeline artifacts (datasets, models) in Google Cloud Storage.

### Configuration

```bash
uniflow stack register gcp-stack \
    --artifact-store gs://my-bucket/uniflow-artifacts \
    --metadata-store sqlite:///uniflow.db
```

Or in Python:

```python
from uniflow.stacks import GCPStack

stack = GCPStack(
    name="production-gcp",
    artifact_store="gs://my-bucket/artifacts"
)
stack.activate()
```

## 🚀 Vertex AI Execution

Run your pipeline steps as Vertex AI Custom Jobs.

### Requirements

- GCP Project with Vertex AI API enabled.
- Docker installed locally (to build step images).

### Usage

```python
from uniflow import Pipeline
from uniflow.integrations.gcp import VertexAIOrchestrator

pipeline = Pipeline("vertex_pipeline")
# ... add steps ...

# Run on Vertex AI
pipeline.run(
    orchestrator=VertexAIOrchestrator(
        project="my-gcp-project",
        location="us-central1",
        machine_type="n1-standard-4"
    )
)
```

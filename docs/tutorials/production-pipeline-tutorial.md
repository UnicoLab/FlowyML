# 🏭 Production Pipeline Tutorial

A complete, end-to-end guide for deploying FlowyML pipelines to production. By the end of this tutorial, you'll have a fully containerized pipeline running on a remote orchestrator with tracking, artifact storage, and monitoring.

<div class="hero-section" markdown>

## 🎯 What You'll Build

A complete ML pipeline with Docker containerization, GPU resources, cloud storage, experiment tracking, scheduling, and monitoring — ready for production.

</div>

---

## 📋 Prerequisites

Before you start, make sure you have:

- ✅ Python 3.10+ installed
- ✅ Docker installed and running
- ✅ A cloud account (GCP or AWS) — we'll use **GCP** in this tutorial
- ✅ `gcloud` CLI configured (or `aws` CLI for AWS)

```bash
# Install FlowyML with all extras
pip install "flowyml[all]"

# Verify installation
flowyml --version
```

---

## 1️⃣ Project Setup

### Create a New Project

```bash
# Create project
flowyml init production-demo
cd production-demo

# Project structure
tree
```

```
production-demo/
├── flowyml.yaml           # Stack configuration
├── requirements.txt       # Python dependencies
├── Dockerfile             # (Optional) Custom Docker image
├── README.md
└── src/
    ├── __init__.py
    ├── pipeline.py        # Your pipeline code
    ├── steps/
    │   ├── __init__.py
    │   ├── data_loader.py
    │   ├── preprocessor.py
    │   └── trainer.py
    └── utils/
        └── helpers.py
```

!!! tip "📁 Best practice"
    Keep your steps in separate files under `src/steps/`. This makes them independently testable and reusable across pipelines.

---

## 2️⃣ Dependency Management

### Option A: `requirements.txt` (Simple)

```txt linenums="1"
# requirements.txt
flowyml[all]>=1.9.0
scikit-learn>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
mlflow>=2.8.0
google-cloud-aiplatform>=1.38.0
google-cloud-storage>=2.10.0
```

### Option B: `pyproject.toml` (Poetry)

```toml linenums="1"
# pyproject.toml
[tool.poetry]
name = "production-demo"
version = "0.1.0"
description = "Production ML pipeline with FlowyML"
python = "^3.11"

[tool.poetry.dependencies]
flowyml = {version = "^1.9.0", extras = ["all"]}
scikit-learn = "^1.3.0"
pandas = "^2.0.0"
mlflow = "^2.8.0"
google-cloud-aiplatform = "^1.38.0"
```

```bash
# If using Poetry
poetry install
poetry export -f requirements.txt -o requirements.txt  # For Docker
```

!!! important "🔑 Which one to use?"
    - **`requirements.txt`** — Simpler, universally supported, works with any Docker setup
    - **`pyproject.toml` (Poetry)** — Better dependency resolution, lockfiles for reproducibility

    **For production**, we recommend starting with `requirements.txt`. Use Poetry if your team already has a Poetry workflow.

---

## 3️⃣ Stack Configuration

### Local Development Stack

Start with a local stack for development and testing:

```yaml linenums="1"
# flowyml.yaml — local development
stacks:
  local:
    orchestrator: { type: local }
    artifact_store: { type: local, path: "./artifacts" }
    experiment_tracker:
      type: mlflow
      tracking_uri: http://localhost:5000

active_stack: local
```

### Cloud Production Stack (GCP)

Add a production stack that uses Vertex AI:

```yaml linenums="1"
# flowyml.yaml — full multi-stack config
stacks:
  local:
    orchestrator: { type: local }
    artifact_store: { type: local, path: "./artifacts" }
    experiment_tracker:
      type: mlflow
      tracking_uri: http://localhost:5000

  gcp-prod:
    orchestrator:
      type: vertex_ai
      project: ${GCP_PROJECT}
      location: us-central1
      staging_bucket: gs://my-staging-bucket

    artifact_store:
      type: gcs
      bucket: ${GCS_BUCKET}
      prefix: production/

    container_registry:
      type: gcr
      project: ${GCP_PROJECT}
      location: us-central1
      repository: ml-pipelines

    experiment_tracker:
      type: mlflow
      tracking_uri: ${MLFLOW_TRACKING_URI}

    model_registry:
      type: vertex_model_registry

    model_deployer:
      type: vertex_endpoint

    artifact_routing:
      Model:
        store: gcs
        register: true
        deploy: true
        deploy_condition: manual
      Dataset:
        store: gcs
        path: "{run_id}/datasets/{step_name}"
      Metrics:
        log_to_tracker: true

  # Optional: AWS alternative
  aws-staging:
    orchestrator:
      type: sagemaker
      region: us-east-1
      role_arn: ${SAGEMAKER_ROLE_ARN}
    artifact_store:
      type: s3
      bucket: ${S3_BUCKET}

active_stack: local
```

---

## 4️⃣ Write the Pipeline

### Step 1: Data Loader

```python linenums="1"
# src/steps/data_loader.py
from flowyml import step
import pandas as pd

@step(
    outputs=["raw_data"],
    resources={"cpu": "2", "memory": "4Gi"}
)
def load_data(source_path: str = "s3://data-lake/training.csv") -> pd.DataFrame:
    """Load raw data from cloud storage.

    Resources: 2 CPU cores, 4GB RAM — suitable for data loading.
    """
    print(f"📥 Loading data from {source_path}")
    df = pd.read_csv(source_path)
    print(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")
    return df
```

### Step 2: Preprocessor

```python linenums="1"
# src/steps/preprocessor.py
from flowyml import step
import pandas as pd
from sklearn.preprocessing import StandardScaler

@step(
    inputs=["raw_data"],
    outputs=["train_data", "test_data"],
    resources={"cpu": "4", "memory": "8Gi"}
)
def preprocess(raw_data: pd.DataFrame, test_size: float = 0.2):
    """Clean, transform, and split data.

    Resources: 4 CPU cores, 8GB RAM — feature engineering is CPU-heavy.
    """
    from sklearn.model_selection import train_test_split

    # Feature engineering
    scaler = StandardScaler()
    features = raw_data.drop("target", axis=1)
    scaled = pd.DataFrame(scaler.fit_transform(features), columns=features.columns)
    scaled["target"] = raw_data["target"].values

    # Split
    train, test = train_test_split(scaled, test_size=test_size, random_state=42)
    print(f"📊 Train: {len(train)} rows, Test: {len(test)} rows")
    return train, test
```

### Step 3: Trainer (with GPU)

```python linenums="1"
# src/steps/trainer.py
from flowyml import step
from flowyml.core import Model, Metrics
import pandas as pd

@step(
    inputs=["train_data", "test_data"],
    outputs=["model", "metrics"],
    resources={
        "cpu": "8",
        "memory": "32Gi",
        "accelerator_type": "NVIDIA_TESLA_T4",
        "accelerator_count": 1,
    }
)
def train_and_evaluate(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    n_estimators: int = 100,
    max_depth: int = 10,
):
    """Train and evaluate a model.

    Resources: 8 CPUs, 32GB RAM, 1x T4 GPU.
    GPU allocation via the `resources` dict in the @step decorator.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score, precision_score

    # Train
    X_train = train_data.drop("target", axis=1)
    y_train = train_data["target"]
    X_test = test_data.drop("target", axis=1)
    y_test = test_data["target"]

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=42,
    )
    clf.fit(X_train, y_train)

    # Evaluate
    predictions = clf.predict(X_test)
    acc = accuracy_score(y_test, predictions)
    f1 = f1_score(y_test, predictions, average="weighted")

    print(f"🎯 Accuracy: {acc:.4f}, F1: {f1:.4f}")

    # Return typed artifacts — auto-routed based on flowyml.yaml
    model = Model(data=clf, name="classifier", version="1.0.0", framework="sklearn")
    metrics = Metrics({"accuracy": acc, "f1_score": f1, "precision": precision_score(y_test, predictions, average="weighted")})

    return model, metrics
```

### Step 4: Assemble the Pipeline

```python linenums="1"
# src/pipeline.py
from flowyml import Pipeline, context
from steps.data_loader import load_data
from steps.preprocessor import preprocess
from steps.trainer import train_and_evaluate

def create_pipeline(env: str = "local"):
    """Create a production-ready pipeline."""

    # Context with hyperparameters
    ctx = context(
        source_path="gs://my-data-lake/training_v2.csv",
        test_size=0.2,
        n_estimators=200,
        max_depth=15,
    )

    # Build pipeline
    pipeline = Pipeline("production_classifier", context=ctx)
    pipeline.add_step(load_data)
    pipeline.add_step(preprocess)
    pipeline.add_step(train_and_evaluate)

    return pipeline

if __name__ == "__main__":
    pipeline = create_pipeline()
    result = pipeline.run()

    if result.success:
        print("✅ Pipeline completed successfully!")
        print(f"📊 Metrics: {result.outputs.get('metrics')}")
    else:
        print(f"❌ Pipeline failed: {result.error}")
```

---

## 5️⃣ Docker & Containerization

### When FlowyML Builds Images for You

With `auto_build: true` (the default for remote orchestrators), FlowyML:

1. Generates a Dockerfile from your config
2. Installs dependencies from `requirements.txt`
3. Copies your source code into the image
4. Builds the image locally
5. Pushes it to your configured container registry
6. Submits the pipeline with the image URI

**You don't need to do anything extra — just run:**

```bash
FLOWYML_STACK=gcp-prod python src/pipeline.py
```

### When You Need a Custom Dockerfile

Create a custom Dockerfile for:

- Custom system packages (OpenCV, ffmpeg, CUDA)
- Multi-stage builds for smaller images
- Pre-baked model weights or data

```dockerfile linenums="1"
# Dockerfile
FROM python:3.11-slim AS builder

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Runtime stage ---
FROM python:3.11-slim

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Your code
COPY src/ /app/src/
COPY flowyml.yaml /app/flowyml.yaml

WORKDIR /app
```

Build and push:

```bash
# Build
docker build -t us-central1-docker.pkg.dev/my-project/ml-pipelines/classifier:v1.0 .

# Push
docker push us-central1-docker.pkg.dev/my-project/ml-pipelines/classifier:v1.0
```

Reference in config:

```yaml linenums="1"
plugins:
  docker:
    auto_build: false
    image: us-central1-docker.pkg.dev/my-project/ml-pipelines/classifier:v1.0
```

---

## 6️⃣ Step Grouping for Efficiency

Co-locate related steps in the same container to avoid cold-start overhead:

```python linenums="1"
# Steps in the same execution_group share a container
@step(outputs=["raw"], execution_group="preprocessing")
def load(): ...

@step(inputs=["raw"], outputs=["clean"], execution_group="preprocessing")
def clean(raw): ...

@step(inputs=["clean"], outputs=["features"], execution_group="preprocessing")
def featurize(clean): ...

# This step runs in its own container (heavy GPU workload)
@step(
    inputs=["features"],
    outputs=["model"],
    resources={"cpu": "8", "memory": "32Gi", "accelerator_type": "NVIDIA_TESLA_T4", "accelerator_count": 1}
)
def train(features): ...
```

!!! info "📊 Resource aggregation"
    For grouped steps, FlowyML allocates the **maximum** of all participants' resources. If step A needs 2 CPUs and step B needs 4 CPUs, the group gets 4 CPUs.

---

## 7️⃣ Tracking & Observability

### MLflow Setup

```bash
# Start local MLflow server (for development)
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --port 5000
```

```yaml linenums="1"
# flowyml.yaml — tracking config
stacks:
  local:
    experiment_tracker:
      type: mlflow
      tracking_uri: http://localhost:5000
```

### FlowyML Dashboard

```bash
# Start the FlowyML UI
flowyml ui start

# Access at http://localhost:8080
```

The dashboard provides:

- 📊 **Pipeline DAG** — Visual graph showing step dependencies
- ⚡ **Real-time execution** — Steps highlight as they run
- 🔍 **Artifact inspection** — Click any step to see inputs/outputs
- 📜 **Run history** — Compare different runs side-by-side
- 📈 **Metrics over time** — Track model performance across runs

---

## 8️⃣ Scheduling & Automation

### Cron Scheduling

```python linenums="1"
from flowyml import PipelineScheduler

scheduler = PipelineScheduler()

# Retrain model daily at 3 AM
scheduler.schedule_daily(
    "daily_retrain",
    lambda: create_pipeline("gcp-prod").run(),
    hour=3
)

# Run data quality checks every 6 hours
scheduler.schedule_interval(
    "data_quality",
    lambda: data_quality_pipeline.run(),
    hours=6
)

scheduler.start()
```

### CLI Scheduling

```bash
# Schedule via CLI
flowyml schedule add \
  --name "daily_retrain" \
  --pipeline src/pipeline.py \
  --stack gcp-prod \
  --cron "0 3 * * *"

# List schedules
flowyml schedule list

# Disable a schedule
flowyml schedule disable daily_retrain
```

---

## 9️⃣ Running the Full Pipeline

### Local Development

```bash
# Run locally (default stack)
python src/pipeline.py

# Or via CLI
flowyml run src/pipeline.py
```

### Cloud Production

```bash
# Set environment variables
export GCP_PROJECT=my-project
export GCS_BUCKET=my-ml-artifacts
export MLFLOW_TRACKING_URI=https://mlflow.company.com

# Option 1: Environment variable
FLOWYML_STACK=gcp-prod python src/pipeline.py

# Option 2: CLI with stack flag
flowyml run src/pipeline.py --stack gcp-prod

# Option 3: Set default stack
flowyml stack set gcp-prod
flowyml run src/pipeline.py
```

### What Happens When You Run on a Remote Orchestrator

```
1. FlowyML reads flowyml.yaml → selects "gcp-prod" stack
2. Generates a Dockerfile (or uses your custom one)
3. Builds the Docker image locally
4. Pushes to Google Artifact Registry
5. Submits the pipeline to Vertex AI Pipelines
6. Each step runs as a container on Vertex AI:
   - load_data        → 2 CPU, 4GB RAM
   - preprocess       → 4 CPU, 8GB RAM
   - train_and_evaluate → 8 CPU, 32GB RAM, 1x T4 GPU
7. Artifacts are saved to GCS
8. Metrics are logged to MLflow
9. Model is registered in Vertex AI Model Registry
10. You monitor via FlowyML UI or GCP Console
```

---

## 🔟 Complete `flowyml.yaml` Reference

```yaml linenums="1"
# flowyml.yaml — Production-ready configuration
stacks:
  # ── Local Development ──
  local:
    orchestrator: { type: local }
    artifact_store: { type: local, path: "./artifacts" }
    experiment_tracker:
      type: mlflow
      tracking_uri: http://localhost:5000

  # ── GCP Production ──
  gcp-prod:
    orchestrator:
      type: vertex_ai
      project: ${GCP_PROJECT}
      location: us-central1
      staging_bucket: gs://${GCS_BUCKET}-staging

    artifact_store:
      type: gcs
      bucket: ${GCS_BUCKET}
      prefix: production/

    container_registry:
      type: gcr
      project: ${GCP_PROJECT}
      location: us-central1
      repository: ml-pipelines

    experiment_tracker:
      type: mlflow
      tracking_uri: ${MLFLOW_TRACKING_URI}

    model_registry:
      type: vertex_model_registry

    model_deployer:
      type: vertex_endpoint

    artifact_routing:
      Model:
        store: gcs
        register: true
        deploy: true
        deploy_condition: manual
      Dataset:
        store: gcs
        path: "{run_id}/datasets/{step_name}"
      Metrics:
        log_to_tracker: true

  # ── AWS Alternative ──
  aws-prod:
    orchestrator:
      type: sagemaker
      region: us-east-1
      role_arn: ${SAGEMAKER_ROLE_ARN}
    artifact_store:
      type: s3
      bucket: ${S3_BUCKET}
      region: us-east-1
    container_registry:
      type: ecr
      repository: ml-pipelines
      region: us-east-1

# ── Docker Configuration ──
docker:
  auto_build: true
  base_image: python:3.11-slim
  requirements_file: requirements.txt
  include_files:
    - src/
    - configs/

# ── Pipeline Defaults ──
pipeline_defaults:
  resources:
    cpu: "2"
    memory: "8Gi"
    timeout: 3600

active_stack: local
```

---

## ✅ Production Checklist

Before deploying to production, verify:

- [ ] `flowyml stack validate` passes with no errors
- [ ] All environment variables are set (`GCP_PROJECT`, `GCS_BUCKET`, etc.)
- [ ] Docker is running and authenticated to your registry
- [ ] MLflow server is accessible from the cloud environment
- [ ] IAM permissions are configured (GCP: `roles/aiplatform.user`, AWS: SageMaker role)
- [ ] `requirements.txt` is up-to-date with all dependencies
- [ ] Pipeline runs successfully locally before deploying remotely
- [ ] Monitoring and alerting are configured (Slack, email)
- [ ] Scheduling is set up for recurring runs

---

## 📚 Next Steps

<div class="header-grid" markdown>

<div class="header-card" markdown>
### ⚙️ Stack Configuration
Multi-stack management, environment variables, and all plugin options.

→ **[Stack Configuration Guide](../plugins/stack-configuration.md)**
</div>

<div class="header-card" markdown>
### 🔀 Type-Based Routing
Auto-route Models, Datasets, and Metrics to the right infrastructure.

→ **[Type Routing Guide](../plugins/type_routing.md)**
</div>

<div class="header-card" markdown>
### 🚀 Deployment Guide
Deploy FlowyML as a centralized hub with PostgreSQL and Docker.

→ **[Deployment Guide](../production_deployment.md)**
</div>

</div>

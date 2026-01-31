# FlowyML Native Plugins - Implementation Roadmap

> **Native plugins are the default and recommended approach** for FlowyML.
> ZenML integration is legacy/optional.

---

## Core Design Principle

> **TRUE SEPARATION OF CONCERNS: Zero plugin imports in user code. Stack config handles everything automatically based on types and artifacts.**

### User Code (Pure ML Logic Only)

```python
# train.py - THIS CODE NEVER CHANGES, NEVER IMPORTS PLUGINS
from flowyml import pipeline, step
from flowyml.core import Model, Dataset  # Type annotations

@step
def load_data() -> Dataset:
    return pd.read_csv("data.csv")

@step
def train_model(data: Dataset) -> Model:
    model = sklearn.fit(data)
    return model

@step
def evaluate(model: Model, data: Dataset) -> dict:
    return {"accuracy": model.score(data)}

@pipeline
def training_pipeline():
    data = load_data()
    model = train_model(data)
    metrics = evaluate(model, data)
    return model
```

> **Note: No `from flowyml.plugins import ...` anywhere!**

### Stack Config (Handles ALL Infrastructure)

```yaml
# flowyml.yaml - THIS IS WHERE ALL MAGIC HAPPENS

stack:
  # Where to run the pipeline
  orchestrator:
    type: vertex_ai  # or sagemaker, kubernetes, local
    project: ${GCP_PROJECT}
    location: us-central1

  # Where to store artifacts by TYPE
  artifact_routing:
    Dataset:  # Type-based routing!
      store: gcs
      path_template: "datasets/{run_id}/{step_name}"
    Model:
      store: gcs
      path_template: "models/{run_id}/{step_name}"
      register: true  # Auto-register to model registry
    dict:
      store: gcs
      path_template: "metrics/{run_id}/{step_name}"

  # Model registry for Model types
  model_registry:
    type: vertex_model_registry
    project: ${GCP_PROJECT}
    auto_register_models: true  # Auto-register any Model output

  # Experiment tracking
  experiment_tracker:
    type: mlflow
    tracking_uri: ${MLFLOW_URI}
    auto_log_metrics: true  # Auto-log any dict outputs as metrics

  # Container registry for Docker images
  container_registry:
    type: gcr
    project: ${GCP_PROJECT}
```

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│  YOUR CODE (Pure ML, No Infrastructure)                             │
│                                                                     │
│  @step                                                              │
│  def train() -> Model:     <- FlowyML sees return type is 'Model'   │
│      return trained_model                                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
         FlowyML Runtime inspects types and routes automatically
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  flowyml.yaml                                                       │
│                                                                     │
│  artifact_routing:                                                  │
│    Model:                   <- Config says: Model types go to GCS   │
│      store: gcs             <- and auto-register to model registry  │
│      register: true                                                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Runtime automatically:                                             │
│  1. Saves model to gs://bucket/models/{run_id}/train                │
│  2. Registers in Vertex Model Registry                              │
│  3. Logs to MLflow experiment                                       │
│                                                                     │
│  USER DID NOTHING - just returned a Model!                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Switch Clouds = Change Config Only

```bash
# Run on GCP
FLOWYML_CONFIG=flowyml.gcp.yaml flowyml run training_pipeline

# Run on AWS (SAME CODE, different config)
FLOWYML_CONFIG=flowyml.aws.yaml flowyml run training_pipeline
```

---

## Priority Legend

| Priority | Description |
|----------|-------------|
| 🔴 P0 | Critical - Must have for production use |
| 🟠 P1 | High - Important for complete stack |
| 🟡 P2 | Medium - Nice to have |
| 🟢 P3 | Low - Future enhancement |

---

## GCP Stack (Google Cloud Platform)

### ✅ Implemented

| Plugin | File | Status |
|--------|------|--------|
| GCS Artifact Store | `stores/gcs.py` | ✅ Complete |
| GCR/Artifact Registry | `registries/gcr.py` | ✅ Complete |
| Vertex AI Pipelines | `orchestrators/vertex_ai.py` | ✅ Complete |

### 🔲 To Implement

#### 🔴 P0 - Model Registry & Deployment

| Plugin | Description | File | Dependencies |
|--------|-------------|------|--------------|
| **Vertex Model Registry** | Register, version, and manage ML models | `gcp/model_registry.py` | `google-cloud-aiplatform` |
| **Vertex Endpoints** | Deploy models to online prediction endpoints | `gcp/endpoints.py` | `google-cloud-aiplatform` |
| **Vertex Batch Prediction** | Run batch prediction jobs | `gcp/batch_prediction.py` | `google-cloud-aiplatform` |

```yaml
# flowyml.yaml - Target config
plugins:
  model_registry:
    type: vertex_model_registry
    project: my-project
    location: us-central1

  model_deployer:
    type: vertex_endpoints
    project: my-project
    location: us-central1
```

#### 🟠 P1 - Training & Compute

| Plugin | Description | File | Dependencies |
|--------|-------------|------|--------------|
| **Vertex Training Jobs** | Run custom training jobs | `gcp/training.py` | `google-cloud-aiplatform` |
| **Vertex Custom Containers** | Train with custom Docker containers | `gcp/custom_training.py` | `google-cloud-aiplatform` |
| **Vertex Hyperparameter Tuning** | Automated hyperparameter search | `gcp/hptuning.py` | `google-cloud-aiplatform` |

```python
# Target API
from flowyml.plugins import run_training_job

run_training_job(
    script="train.py",
    machine_type="n1-standard-8",
    accelerator_type="NVIDIA_TESLA_T4",
    accelerator_count=1,
)
```

#### 🟡 P2 - Data & Feature Engineering

| Plugin | Description | File | Dependencies |
|--------|-------------|------|--------------|
| **BigQuery** | Query and load data from BigQuery | `gcp/bigquery.py` | `google-cloud-bigquery` |
| **Vertex Feature Store** | Managed feature store | `gcp/feature_store.py` | `google-cloud-aiplatform` |
| **Dataflow** | Batch/stream data processing | `gcp/dataflow.py` | `apache-beam[gcp]` |

#### 🟢 P3 - Monitoring & Advanced

| Plugin | Description | File | Dependencies |
|--------|-------------|------|--------------|
| **Vertex Model Monitoring** | Monitor model performance | `gcp/monitoring.py` | `google-cloud-aiplatform` |
| **Vertex Explainability** | Model explanations | `gcp/explainability.py` | `google-cloud-aiplatform` |
| **Cloud Logging** | Centralized logging | `gcp/logging.py` | `google-cloud-logging` |

---

## AWS Stack (Amazon Web Services)

### ✅ Implemented

| Plugin | File | Status |
|--------|------|--------|
| S3 Artifact Store | `stores/s3.py` | ✅ Complete |
| ECR Registry | `registries/ecr.py` | ✅ Complete |
| SageMaker Pipelines | `orchestrators/sagemaker.py` | ✅ Complete |

### 🔲 To Implement

#### 🔴 P0 - Model Registry & Deployment

| Plugin | Description | File | Dependencies |
|--------|-------------|------|--------------|
| **SageMaker Model Registry** | Register and version models | `aws/model_registry.py` | `sagemaker` |
| **SageMaker Endpoints** | Real-time inference endpoints | `aws/endpoints.py` | `sagemaker` |
| **SageMaker Batch Transform** | Batch inference jobs | `aws/batch_transform.py` | `sagemaker` |
| **SageMaker Serverless** | Serverless inference | `aws/serverless.py` | `sagemaker` |

```yaml
# flowyml.yaml - Target config
plugins:
  model_registry:
    type: sagemaker_model_registry
    region: us-east-1

  model_deployer:
    type: sagemaker_endpoints
    region: us-east-1
    instance_type: ml.m5.xlarge
```

#### 🟠 P1 - Training & Compute

| Plugin | Description | File | Dependencies |
|--------|-------------|------|--------------|
| **SageMaker Training Jobs** | Custom training jobs | `aws/training.py` | `sagemaker` |
| **SageMaker Hyperparameter Tuning** | Automated HP search | `aws/hptuning.py` | `sagemaker` |
| **SageMaker Processing** | Data processing jobs | `aws/processing.py` | `sagemaker` |
| **SageMaker Experiments** | Experiment tracking | `aws/experiments.py` | `sagemaker` |

```python
# Target API
from flowyml.plugins import run_training_job

run_training_job(
    script="train.py",
    instance_type="ml.p3.2xlarge",
    instance_count=1,
)
```

#### 🟡 P2 - Data & Feature Engineering

| Plugin | Description | File | Dependencies |
|--------|-------------|------|--------------|
| **SageMaker Feature Store** | Managed feature store | `aws/feature_store.py` | `sagemaker` |
| **AWS Glue** | ETL jobs | `aws/glue.py` | `boto3` |
| **Athena** | Query data in S3 | `aws/athena.py` | `boto3` |
| **Redshift** | Data warehouse queries | `aws/redshift.py` | `boto3`, `redshift-connector` |

#### 🟢 P3 - Monitoring & Advanced

| Plugin | Description | File | Dependencies |
|--------|-------------|------|--------------|
| **SageMaker Model Monitor** | Monitor models in production | `aws/monitoring.py` | `sagemaker` |
| **SageMaker Clarify** | Bias detection and explainability | `aws/clarify.py` | `sagemaker` |
| **CloudWatch** | Logs and metrics | `aws/cloudwatch.py` | `boto3` |
| **Step Functions** | Workflow orchestration | `aws/step_functions.py` | `boto3` |

---

## Base Classes to Add

```python
# flowyml/plugins/base.py - New plugin types

class ModelRegistryPlugin(BasePlugin):
    """Base class for model registries."""
    def register_model(self, model, name, version=None, **kwargs) -> str: ...
    def get_model(self, name, version=None) -> Any: ...
    def list_models(self) -> list: ...
    def delete_model(self, name, version=None) -> bool: ...

class ModelDeployerPlugin(BasePlugin):
    """Base class for model deployers."""
    def deploy(self, model, endpoint_name, **config) -> str: ...
    def predict(self, endpoint_name, data) -> Any: ...
    def undeploy(self, endpoint_name) -> bool: ...
    def list_endpoints(self) -> list: ...

class TrainingJobPlugin(BasePlugin):
    """Base class for training job runners."""
    def run_job(self, script, **config) -> str: ...
    def get_job_status(self, job_id) -> dict: ...
    def cancel_job(self, job_id) -> bool: ...
    def list_jobs(self) -> list: ...

class BatchPredictionPlugin(BasePlugin):
    """Base class for batch prediction."""
    def run_batch(self, model, input_path, output_path, **config) -> str: ...
    def get_batch_status(self, job_id) -> dict: ...
```

---

## Stack Configuration Examples

### Complete GCP Stack

```yaml
# flowyml.yaml
plugins:
  experiment_tracker:
    type: mlflow
    tracking_uri: ${MLFLOW_URI}

  artifact_store:
    type: gcs
    bucket: ${GCS_BUCKET}
    project: ${GCP_PROJECT}

  container_registry:
    type: gcr
    project: ${GCP_PROJECT}
    use_artifact_registry: true

  orchestrator:
    type: vertex_ai
    project: ${GCP_PROJECT}
    location: ${GCP_REGION:-us-central1}

  model_registry:
    type: vertex_model_registry
    project: ${GCP_PROJECT}
    location: ${GCP_REGION:-us-central1}

  model_deployer:
    type: vertex_endpoints
    project: ${GCP_PROJECT}
    location: ${GCP_REGION:-us-central1}
```

### Complete AWS Stack

```yaml
# flowyml.yaml
plugins:
  experiment_tracker:
    type: mlflow
    tracking_uri: ${MLFLOW_URI}

  artifact_store:
    type: s3
    bucket: ${S3_BUCKET}
    region: ${AWS_REGION}

  container_registry:
    type: ecr
    repository: ${ECR_REPO}
    region: ${AWS_REGION}

  orchestrator:
    type: sagemaker
    role_arn: ${SAGEMAKER_ROLE}
    region: ${AWS_REGION}

  model_registry:
    type: sagemaker_model_registry
    region: ${AWS_REGION}

  model_deployer:
    type: sagemaker_endpoints
    region: ${AWS_REGION}
```

---

## Implementation Order

### Phase 1: Model Registry & Deployment (P0)
1. [ ] Add base classes (`ModelRegistryPlugin`, `ModelDeployerPlugin`)
2. [ ] Vertex Model Registry
3. [ ] Vertex Endpoints
4. [ ] SageMaker Model Registry
5. [ ] SageMaker Endpoints

### Phase 2: Training Jobs (P1)
6. [ ] Add base class (`TrainingJobPlugin`)
7. [ ] Vertex Training Jobs
8. [ ] SageMaker Training Jobs
9. [ ] Vertex Hyperparameter Tuning
10. [ ] SageMaker Hyperparameter Tuning

### Phase 3: Batch Processing (P1)
11. [ ] Add base class (`BatchPredictionPlugin`)
12. [ ] Vertex Batch Prediction
13. [ ] SageMaker Batch Transform

### Phase 4: Feature Stores (P2)
14. [ ] Vertex Feature Store
15. [ ] SageMaker Feature Store

### Phase 5: Monitoring (P3)
16. [ ] Vertex Model Monitoring
17. [ ] SageMaker Model Monitor

---

## Target User Experience

### The Code (Pure ML, No Infrastructure Imports)

```python
# train.py - ZERO PLUGIN IMPORTS, JUST FLOWYML CORE
from flowyml import pipeline, step
from flowyml.core import Model, Dataset, Metrics

@step
def load_data(path: str) -> Dataset:
    """Load training data."""
    return pd.read_csv(path)

@step(resources={"gpu": 1})
def train_model(data: Dataset, learning_rate: float = 0.001) -> Model:
    """Train the model."""
    model = MyModel().fit(data, lr=learning_rate)
    return model  # FlowyML sees Model type → auto-stores + registers

@step
def evaluate(model: Model, data: Dataset) -> Metrics:
    """Evaluate model performance."""
    return {"accuracy": 0.95, "f1": 0.92}  # Auto-logged to tracker

@step
def deploy_for_inference(model: Model) -> str:
    """Deploy model to endpoint."""
    return model  # Config determines WHERE it deploys

@pipeline
def training_pipeline(data_path: str):
    data = load_data(data_path)
    model = train_model(data)
    metrics = evaluate(model, data)
    endpoint = deploy_for_inference(model)
    return model

# Run locally
if __name__ == "__main__":
    training_pipeline("data.csv")
```

> **No `from flowyml.plugins import ...` anywhere!**
> The stack config handles all routing based on types.

### The Config (Controls Everything)

```yaml
# flowyml.yaml - GCP Production
stack:
  orchestrator:
    type: vertex_ai
    project: ${GCP_PROJECT}

  artifact_routing:
    Dataset: { store: gcs, path: "data/{run_id}" }
    Model: { store: gcs, path: "models/{run_id}", register: true }
    Metrics: { log_to_tracker: true }

  model_registry:
    type: vertex_model_registry
    auto_register: true  # Any Model output auto-registers

  model_deployer:
    type: vertex_endpoints
    auto_deploy: true  # deploy_for_inference step triggers this

  experiment_tracker:
    type: mlflow
    auto_log_metrics: true  # Metrics type auto-logs

  container_registry:
    type: gcr
```

### Switching Clouds

```bash
# Same code, different config
FLOWYML_CONFIG=flowyml.aws.yaml flowyml run training_pipeline --path data.csv
```

```yaml
# flowyml.aws.yaml - Just change types
stack:
  orchestrator: { type: sagemaker }
  model_registry: { type: sagemaker_model_registry }
  model_deployer: { type: sagemaker_endpoints }
  artifact_routing:
    Model: { store: s3, register: true }
```

### Key Implementation Requirements

1. **Type-Based Routing**: FlowyML runtime inspects step return types and routes to configured plugins
2. **Auto-Registration**: `Model` outputs trigger model registry automatically when `register: true`
3. **Auto-Logging**: `Metrics`/`dict` outputs log to experiment tracker automatically
4. **Auto-Deployment**: Steps that return `Model` to deployment steps trigger configured deployer
5. **Zero User Imports**: User code ONLY imports `flowyml.core` types, NEVER plugins

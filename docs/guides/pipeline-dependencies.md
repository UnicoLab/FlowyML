# Container-Aware Pipelines & Dependency Management

This guide explains how to wire Python dependencies, Docker images, and stack resources together so every pipeline step (or execution group of steps) runs inside the right environment. It also includes a full Keras example covering datasets, models, callbacks, versioning, and experiment tracking.

## 1. Declare Dependencies Close to Your Code

Use `pyproject.toml` (Poetry) to describe every library the pipeline and its steps require. Keep training-only packages in a dedicated group/extra so the runtime image installs only what it needs:

```toml
[tool.poetry.dependencies]
python = "^3.11"
flowyml = "^0.1.0"
rich = "^13.7"

[tool.poetry.group.training.dependencies]
tensorflow = "^2.16"
keras = "^3.0"
ml-dtypes = "^0.4"
scikit-learn = "^1.5"
cloudpathlib = "^0.18"

[tool.poetry.extras]
training = ["tensorflow", "keras", "scikit-learn"]
```

> Tip: `poetry export -f requirements.txt --with training -o build/requirements.txt` gives you a frozen list when you prefer `requirements.txt`.

## 2. Connect Dependencies to the Stack Configuration

Reference the Dockerfile/Poetry/requirements entrypoint inside `flowyml.yaml`. The orchestrator reads this section whenever it builds or validates container images for a stack.

```yaml
# flowyml.yaml
stacks:
  prod-gcp:
    type: gcp
    project_id: ${GCP_PROJECT}
    region: us-central1
    container_registry:
      type: gcr
      uri: gcr.io/${GCP_PROJECT}
    orchestrator:
      type: vertex_ai
      service_account: ${GCP_SA}

docker:
  dockerfile: ./docker/training.Dockerfile   # auto-detected if omitted
  build_context: .
  use_poetry: true                           # copies pyproject + poetry.lock
  requirements_file: build/requirements.txt  # optional override
  base_image: python:3.11-slim
  env_vars:
    PYTHONUNBUFFERED: "1"
    TF_CPP_MIN_LOG_LEVEL: "2"
  build_args:
    POETRY_EXTRA: training

resources:
  default:
    cpu: "4"
    memory: "16Gi"
    disk_size: "100Gi"
  gpu_training:
    cpu: "16"
    memory: "64Gi"
    gpu: nvidia-l4
    gpu_count: 1
    machine_type: n1-standard-16
```

flowyml automatically infers a Dockerfile (`Dockerfile`, `docker/Dockerfile`, `.docker/Dockerfile`) and Poetry usage if you omit the `docker` block.

## 3. Provide Pipeline-Level Docker & Resource Overrides

For special workloads, override the stack defaults directly from code using `DockerConfig` and `ResourceConfig`. You can scope resources to entire execution groups by assigning the same `execution_group` to each `@step`.

```python
from flowyml.stacks.components import DockerConfig, ResourceConfig

train_docker = DockerConfig(
    dockerfile="./docker/training.Dockerfile",
    image="gcr.io/my-project/fraud-training:latest",
    build_context=".",
    requirements=["tensorflow==2.16.2", "keras>=3.0", "pandas>=2.2"],
    env_vars={"TF_FORCE_GPU_ALLOW_GROWTH": "true"},
)

gpu_resources = ResourceConfig(
    cpu="16",
    memory="64Gi",
    gpu="nvidia-l4",
    gpu_count=1,
    disk_size="200Gi",
)

result = pipeline.run(
    context={"epochs": 25, "bucket": "gs://fraud-data"},
    resources=gpu_resources,
    docker_config=train_docker,
)
```

Because the stack knows its `container_registry`, remote orchestrators such as Vertex AI receive the final `image_uri` and the aggregated resource envelope for each grouped step.

## 4. Build and Push Runtime Images

flowyml does not own your registry credentials; push images with Docker/Buildx and let stacks reference them:

```bash
docker build -f docker/training.Dockerfile -t fraud-training:latest .
docker tag fraud-training:latest gcr.io/${GCP_PROJECT}/fraud-training:v3
docker push gcr.io/${GCP_PROJECT}/fraud-training:v3

# Point stack or DockerConfig to the pushed image URI
```

When the registry block is present in `flowyml.yaml`, running `flowyml stack apply prod-gcp` prints the exact image URI that remote jobs must use. If you need multi-arch images, plug Buildx and push once—flowyml only cares about the resulting `image` reference.

## 5. Full Keras Pipeline Example

### Project Structure

```
fraud-detection/
├── docker/
│   └── training.Dockerfile
├── pipelines/
│   └── fraud_training.py
├── pyproject.toml
└── flowyml.yaml
```

### Dockerfile (docker/training.Dockerfile)

```dockerfile
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ENV POETRY_VERSION=1.8.3 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --with training --no-root

COPY . .
CMD ["python", "pipelines/fraud_training.py"]
```

### Pipeline Code (pipelines/fraud_training.py)

```python
import os
import pandas as pd
import tensorflow as tf
from flowyml import Pipeline, step, Dataset, Model, Metrics, context
from flowyml.stacks.components import DockerConfig, ResourceConfig
from flowyml.integrations.keras import FlowymlKerasCallback
from flowyml.tracking.experiment import Experiment

pipeline_ctx = context(project="fraud-ml", run_mode="training")
experiment = Experiment("fraud-detection-v3")

train_resources = ResourceConfig(cpu="16", memory="64Gi", gpu="nvidia-l4", gpu_count=1)
train_docker = DockerConfig(image=os.environ.get("TRAINING_IMAGE"))


@step(outputs=["raw_events"], execution_group="data_ingest")
def load_events(bucket: str) -> Dataset:
    df = pd.read_parquet(f"{bucket}/events/latest.parquet")
    return Dataset.create(
        data=df,
        name="raw_events",
        version="2024.05",
        properties={"rows": len(df), "source": bucket},
    )


@step(inputs=["raw_events"], outputs=["feature_table"], execution_group="data_ingest")
def build_features(raw_events: Dataset) -> Dataset:
    df = raw_events.data
    df["amount_zscore"] = (df.amount - df.amount.mean()) / df.amount.std()
    df["is_night"] = (df.tx_hour < 6).astype(int)
    return Dataset.create(
        data=df,
        name="feature_table",
        parent=raw_events,
        version="2024.05",
        properties={"features": len(df.columns)},
    )


@step(inputs=["feature_table"], outputs=["keras_model"], execution_group="training_cluster")
def train_model(feature_table: Dataset, epochs: int) -> Model:
    df = feature_table.data
    X = df.drop(columns=["label"]).values
    y = df["label"].values

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(X.shape[1],)),
        tf.keras.layers.Dense(256, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])

    model.compile(optimizer=tf.keras.optimizers.Adam(3e-4), loss="binary_crossentropy", metrics=["AUC"])

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_auc", patience=3, mode="max", restore_best_weights=True),
        FlowymlKerasCallback(experiment_name=experiment.name, project="fraud-ml", auto_log_history=True),
    ]

    history = model.fit(
        X,
        y,
        validation_split=0.2,
        epochs=epochs,
        batch_size=512,
        callbacks=callbacks,
        verbose=1,
    )

    return Model.create(
        data=model,
        name="fraud-detector",
        version="v3",
        parent=feature_table,
        properties={"best_val_auc": max(history.history["val_auc"])},
    )


@step(inputs=["keras_model", "feature_table"], outputs=["eval_metrics"], execution_group="training_cluster")
def evaluate_model(keras_model: Model, feature_table: Dataset) -> Metrics:
    df = feature_table.data.sample(frac=0.2, random_state=42)
    X = df.drop(columns=["label"]).values
    y = df["label"].values
    loss, auc = keras_model.data.evaluate(X, y, verbose=0)
    return Metrics.create(
        name="fraud_validation",
        version="v3",
        loss=float(loss),
        auc=float(auc),
        parent=keras_model,
    )


@step(inputs=["keras_model", "eval_metrics"], execution_group="registry")
def register_assets(keras_model: Model, eval_metrics: Metrics) -> dict:
    artifact_uri = f"gs://fraud-models/{keras_model.version}"  # push serialized model separately
    experiment.log_run(
        run_id=keras_model.version,
        metrics={"auc": eval_metrics.properties.get("auc", 0.0)},
        parameters={"model_uri": artifact_uri},
    )
    return {"model_uri": artifact_uri, "metrics": eval_metrics.to_dict()}


pipeline = Pipeline("fraud_training", context=pipeline_ctx, project="fraud-ml")
pipeline.add_step(load_events)
pipeline.add_step(build_features)
pipeline.add_step(train_model)
pipeline.add_step(evaluate_model)
pipeline.add_step(register_assets)

if __name__ == "__main__":
    result = pipeline.run(
        context={"bucket": os.environ["FRAUD_BUCKET"], "epochs": 20},
        resources=train_resources,
        docker_config=train_docker,
    )
    print(result.summary())
```

### What This Example Demonstrates

- **Dependencies** come from Poetry (`--with training`) so the Docker image installs TensorFlow/Keras without bloating lightweight services.
- **Docker Integration** references a concrete Dockerfile, builds locally, and pushes to the stack registry so remote orchestrators run an identical environment.
- **Resource Groups** use `execution_group` to co-locate steps that must share the same GPU machine, while lighter steps remain isolated.
- **Assets & Versioning** (`Dataset.create`, `Model.create`, `Metrics.create`) tag every artifact with semantic versions so downstream pipelines can pin specific dataset/model combinations.
- **Experiment Tracking** leverages `Experiment` plus `FlowymlKerasCallback` to log training curves and final metrics that appear in the UI and CLI (`flowyml experiment list`).

With these pieces in place, any pipeline can describe its dependency tree, reference the correct Dockerfile or Poetry group, and ship container images to the chosen registry so stacks and resources always know which runtime to boot.

# 🌊 FlowyML — Agent Skills Reference

> **Version**: 1.10.0 · **License**: Apache 2.0 · **Python**: ≥3.10
> **Repository**: https://github.com/UnicoLab/FlowyML
> **Docs**: https://unicolab.github.io/FlowyML/latest
> **PyPI**: https://pypi.org/project/flowyml/

---

## Purpose

This document is the authoritative reference for **any AI coding agent** (Claude, Gemini, Antigravity, Copilot, Cursor, or others) working with FlowyML.
After reading this file, an agent should be able to:

1. Understand what FlowyML is and what problems it solves
2. Scaffold a new ML/GenAI project with the correct structure
3. Write pipelines, steps, assets, and evaluations correctly
4. Configure enterprise stacks (AzureML, Databricks, GCP, AWS)
5. Set up experiment tracking with MLflow or the built-in tracker
6. Manage secrets via HashiCorp Vault, Azure Key Vault, or AWS Secrets Manager
7. Instrument GenAI applications with transparent tracing
8. Use the CLI, UI dashboard, and plugin system effectively

---

## Table of Contents

- [1. What is FlowyML?](#1-what-is-flowyml)
- [2. Installation](#2-installation)
- [3. Project Structure](#3-project-structure)
- [4. Core Concepts](#4-core-concepts)
  - [4.1 Pipelines & Steps](#41-pipelines--steps)
  - [4.2 Context](#42-context)
  - [4.3 Assets (First-Class Artifacts)](#43-assets-first-class-artifacts)
  - [4.4 Type-Based Artifact Routing](#44-type-based-artifact-routing)
  - [4.5 Caching](#45-caching)
  - [4.6 Conditional & Control Flow](#46-conditional--control-flow)
  - [4.7 Map Tasks & Dynamic Workflows](#47-map-tasks--dynamic-workflows)
  - [4.8 Error Handling & Resilience](#48-error-handling--resilience)
- [5. Stacks & Multi-Environment Configuration](#5-stacks--multi-environment-configuration)
- [6. Enterprise Stack Registry](#6-enterprise-stack-registry)
  - [6.1 Stack Definitions (YAML)](#61-stack-definitions-yaml)
  - [6.2 Policy Engine](#62-policy-engine)
  - [6.3 Backend Adapters](#63-backend-adapters)
  - [6.4 Secrets Management (Vault, Key Vault, etc.)](#64-secrets-management-vault-key-vault-etc)
- [7. Experiment Tracking & Tracing](#7-experiment-tracking--tracing)
  - [7.1 Built-in Experiment Tracker](#71-built-in-experiment-tracker)
  - [7.2 MLflow Integration](#72-mlflow-integration)
  - [7.3 Leaderboard & Run Comparison](#73-leaderboard--run-comparison)
- [8. GenAI Observability](#8-genai-observability)
  - [8.1 Framework-Agnostic Tracing](#81-framework-agnostic-tracing)
  - [8.2 LangGraph / LangChain Integration](#82-langgraph--langchain-integration)
  - [8.3 OpenAI Integration](#83-openai-integration)
  - [8.4 Cost Estimation](#84-cost-estimation)
- [9. Evaluations Framework](#9-evaluations-framework)
- [10. Plugin System](#10-plugin-system)
- [11. Cloud Provider Integrations](#11-cloud-provider-integrations)
  - [11.1 Google Cloud (Vertex AI)](#111-google-cloud-vertex-ai)
  - [11.2 AWS (SageMaker)](#112-aws-sagemaker)
  - [11.3 Azure ML](#113-azure-ml)
  - [11.4 Databricks](#114-databricks)
- [12. Monitoring & Notifications](#12-monitoring--notifications)
- [13. Model Registry & Serving](#13-model-registry--serving)
- [14. CLI Reference](#14-cli-reference)
- [15. Configuration Reference (flowyml.yaml)](#15-configuration-reference-flowymlyaml)
- [16. Common Patterns & Recipes](#16-common-patterns--recipes)
- [17. Testing](#17-testing)

---

## 1. What is FlowyML?

FlowyML is an **enterprise-grade ML pipeline orchestration framework** that bridges rapid experimentation and production deployment. Key differentiators:

- **Pure Python** — No DSLs, no YAML pipelines. Decorators + classes.
- **Assets as first-class citizens** — `Model`, `Dataset`, `Metrics`, `Prompt`, `Checkpoint`, `FeatureSet`, `Report` with automatic lineage.
- **Type-based artifact routing** — Return a `Model` from a step and FlowyML automatically routes it to the correct cloud storage + model registry.
- **Multi-stack architecture** — Switch between local/staging/production with one environment variable.
- **Enterprise governance** — Policy engine, stack locking, audit trails, signed stacks.
- **GenAI-native** — Built-in LLM tracing, token/cost tracking, LangGraph/LangChain/OpenAI integrations.
- **29+ evaluation scorers** — Classification, regression, GenAI (LLM-as-judge), plus adapters for DeepEval, RAGAS, and Phoenix.

---

## 2. Installation

```bash
# Core only
pip install flowyml

# With all extras (recommended for full capabilities)
pip install "flowyml[all]"

# Specific cloud extras
pip install "flowyml[gcp]"       # Vertex AI + GCS + GCR
pip install "flowyml[aws]"       # SageMaker + S3 + ECR
pip install "flowyml[azure]"     # AzureML + Blob + ACR

# GenAI extras
pip install "flowyml[genai]"     # LangGraph + LangChain + OpenAI
pip install "flowyml[langchain]" # LangChain only
pip install "flowyml[langgraph]" # LangGraph + LangChain
pip install "flowyml[openai]"    # OpenAI only

# ML framework extras
pip install "flowyml[pytorch]"
pip install "flowyml[tensorflow]"
pip install "flowyml[sklearn]"
```

**CLI entry points** (installed automatically):
```bash
flowyml --help    # Full CLI
flowy --help      # Short alias
```

---

## 3. Project Structure

A typical FlowyML project:

```
my-ml-project/
├── flowyml.yaml            # Stack configuration (multi-env)
├── stacks/                 # Enterprise stack definitions (YAML)
│   ├── aml_cpu_small.yaml
│   └── gcp_gpu_large.yaml
├── pipelines/
│   ├── training.py
│   └── inference.py
├── steps/
│   ├── data_loading.py
│   ├── preprocessing.py
│   └── training.py
├── tests/
│   └── test_pipeline.py
├── .flowyml/               # Auto-generated local state
│   ├── artifacts/          # Local artifact store
│   ├── metadata.db         # SQLite metadata
│   └── stacks/             # Local stack definitions
└── pyproject.toml
```

Initialize a new project:
```bash
flowyml init my-project
# or interactively
flowyml init
```

---

## 4. Core Concepts

### 4.1 Pipelines & Steps

```python
from flowyml import Pipeline, step, context

# Define steps with the @step decorator
@step(outputs=["dataset"])
def load_data(source: str = "s3://bucket/data.csv"):
    """Load and return training data."""
    import pandas as pd
    return pd.read_csv(source)

@step(inputs=["dataset"], outputs=["model"])
def train_model(dataset, learning_rate: float = 0.01, epochs: int = 100):
    """Train an ML model."""
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier()
    model.fit(dataset.drop("target", axis=1), dataset["target"])
    return model

@step(inputs=["model", "dataset"], outputs=["metrics"])
def evaluate(model, dataset):
    """Evaluate the model and return metrics."""
    score = model.score(dataset.drop("target", axis=1), dataset["target"])
    return {"accuracy": score}

# Build and run the pipeline
ctx = context(learning_rate=0.05, epochs=200)
pipeline = Pipeline("training_pipeline", context=ctx)
pipeline.add_step(load_data)
pipeline.add_step(train_model)
pipeline.add_step(evaluate)

result = pipeline.run()
print(result)
```

**Key `@step` parameters:**
- `inputs` — List of input artifact names (from previous steps)
- `outputs` — List of output artifact names (for downstream steps)
- `resources` — `ResourceConfig(cpu="4", memory="16Gi", gpu="nvidia-tesla-v100")`
- `retry` — `RetryConfig(max_retries=3, delay=10)`
- `cache` — `CacheStrategy.CONTENT_HASH` / `.NONE` / `.STEP_HASH`
- `timeout` — Maximum step execution time in seconds
- `image` — Docker image override for remote execution

### 4.2 Context

The context injects parameters into steps automatically:

```python
from flowyml import context, Pipeline

# Parameters are auto-injected into matching step function arguments
ctx = context(
    learning_rate=0.01,
    batch_size=64,
    epochs=100,
    model_name="classifier_v2",
)

pipeline = Pipeline("train", context=ctx)
```

### 4.3 Assets (First-Class Artifacts)

FlowyML provides typed asset classes with automatic serialization, versioning, and lineage:

```python
from flowyml import Model, Dataset, Metrics, Prompt, Checkpoint, FeatureSet, Report

# Model — ML model with metadata and framework detection
@step(outputs=["model"])
def train(dataset) -> Model:
    clf = RandomForestClassifier().fit(X, y)
    return Model(
        obj=clf,
        name="classifier",
        framework="sklearn",
        metadata={"accuracy": 0.95},
    )

# Dataset — Tabular data with profiling and validation
@step(outputs=["dataset"])
def load() -> Dataset:
    df = pd.read_csv("data.csv")
    return Dataset(
        data=df,
        name="training_data",
        description="Q1 customer data",
    )

# Prompt — Versioned prompt templates for GenAI
prompt = Prompt(
    template="Summarize: {text}",
    name="summarizer_v1",
    variables=["text"],
    model="gpt-4o",
)

# Checkpoint — Resume interrupted training
checkpoint = Checkpoint(
    state={"epoch": 50, "weights": model.state_dict()},
    name="training_checkpoint",
)

# FeatureSet — Named feature collections
features = FeatureSet(
    data=feature_df,
    name="user_features",
    feature_names=["age", "tenure", "spend"],
)

# Metrics — Structured metric reporting
metrics = Metrics(
    values={"accuracy": 0.95, "f1": 0.93, "auc": 0.97},
    name="eval_results",
)

# Report — Rich HTML/Markdown reports
report = Report(
    content=html_content,
    name="model_report",
    report_type="html",
)
```

### 4.4 Type-Based Artifact Routing

Define WHERE artifacts go in `flowyml.yaml` — the pipeline code never changes:

```yaml
# flowyml.yaml
stacks:
  production:
    orchestrator: { type: vertex_ai, project: my-gcp-project }
    artifact_routing:
      Model:
        store: gcs
        path: "{run_id}/models/{artifact_name}"
        register: true            # Auto-register in model registry
        deploy: true
        deploy_condition: auto    # "manual" | "auto" | "on_approval"
        deploy_min_metrics:
          accuracy: 0.9
      Dataset:
        store: gcs
        path: "{run_id}/data/{artifact_name}"
      Metrics:
        log_to_tracker: true      # Auto-log to experiment tracker
      Prompt:
        store: gcs
        path: "prompts/{artifact_name}/v{version}"
```

### 4.5 Caching

FlowyML provides multi-level intelligent caching:

```python
from flowyml import step, CacheStrategy, SmartCache, ContentBasedCache, memoize

# Step-level caching
@step(cache=CacheStrategy.CONTENT_HASH)
def expensive_computation(data):
    """Skipped if input data hash hasn't changed."""
    return transform(data)

# Function-level memoization
@memoize(ttl=3600)
def fetch_remote_data(url: str):
    return requests.get(url).json()

# Advanced content-based caching
cache = ContentBasedCache(backend="redis", ttl=7200)
cache = SmartCache()  # Adaptive: local → shared → content-hash
```

### 4.6 Conditional & Control Flow

```python
from flowyml import when, unless, If, Switch, Condition

# Simple conditional
@step
@when(lambda ctx: ctx.get("run_training", True))
def train_model(data):
    ...

# If/else branching
pipeline.add_step(If(
    condition=lambda ctx: ctx["model_type"] == "deep",
    then_step=train_deep_model,
    else_step=train_sklearn_model,
))

# Multi-way switch
pipeline.add_step(Switch(
    key="environment",
    cases={
        "dev": lightweight_eval,
        "staging": full_eval,
        "prod": full_eval_with_alerts,
    },
))
```

### 4.7 Map Tasks & Dynamic Workflows

```python
from flowyml import map_task, dynamic, Pipeline

# Parallel map — distribute work across a collection
@map_task(concurrency=8, retries=2, min_success_ratio=0.95)
def process_document(doc: dict) -> dict:
    """Each document is processed independently with retry."""
    return transform(doc)

# Dynamic pipeline — generate DAG at runtime
@dynamic(outputs=["best_model"])
def hyperparameter_search(config: dict):
    sub = Pipeline("hp_search")
    for lr in config["learning_rates"]:
        sub.add_step(train_with_lr(lr))
    return sub

# Sub-pipelines
from flowyml import sub_pipeline

@sub_pipeline(name="preprocessing")
def preprocess_pipeline():
    p = Pipeline("preprocess")
    p.add_step(clean_data)
    p.add_step(feature_engineering)
    return p
```

### 4.8 Error Handling & Resilience

```python
from flowyml import retry, on_failure, CircuitBreaker, RetryConfig, FallbackHandler

# Automatic retry with exponential backoff
@step(retry=RetryConfig(max_retries=3, delay=10, backoff_factor=2.0))
def flaky_api_call(url: str):
    return requests.get(url).json()

# Retry decorator
@retry(max_retries=5, exceptions=[ConnectionError, TimeoutError])
def call_external_service():
    ...

# Failure hooks
@on_failure(handler=lambda e, ctx: notify_slack(str(e)))
@step
def critical_step(data):
    ...

# Circuit breaker for external services
breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)

@breaker
def external_api():
    ...
```

---

## 5. Stacks & Multi-Environment Configuration

FlowyML's stack system lets you run the **same pipeline code** on different infrastructure:

```yaml
# flowyml.yaml — Multi-stack configuration
stacks:
  local:
    orchestrator: { type: local }
    artifact_store: { type: local, path: ".flowyml/artifacts" }
    metadata_store: { path: ".flowyml/metadata.db" }

  staging:
    orchestrator: { type: vertex_ai, project: ${GCP_PROJECT_ID}, region: us-central1 }
    artifact_store: { type: gcs, bucket: ${GCP_STAGING_BUCKET} }
    container_registry: { type: gcr, uri: gcr.io/${GCP_PROJECT_ID} }
    experiment_tracker: { type: mlflow, tracking_uri: ${MLFLOW_TRACKING_URI} }

  production:
    orchestrator: { type: vertex_ai, project: ${GCP_PROJECT_ID}, region: us-central1 }
    artifact_store: { type: gcs, bucket: ${GCP_PROD_BUCKET} }
    container_registry: { type: gcr, uri: gcr.io/${GCP_PROJECT_ID} }
    model_registry: { type: vertex_model_registry }
    model_deployer: { type: vertex_endpoint }
    alerter: { type: slack, webhook_url: ${SLACK_WEBHOOK} }
    experiment_tracker: { type: mlflow, tracking_uri: ${MLFLOW_TRACKING_URI} }
    artifact_routing:
      Model:
        store: gcs
        register: true
        deploy: true
        deploy_condition: on_approval

active_stack: local
```

**Switching stacks:**

```bash
# Via environment variable
export FLOWYML_STACK=production
python pipeline.py

# Via CLI
flowyml run pipeline.py --stack production
```

```python
# Via code — context manager
from flowyml import use_stack

with use_stack("production"):
    pipeline.run()

# Via StackConfig hydration
from flowyml.plugins.stack_config import get_stack_manager
manager = get_stack_manager()
live_stack = manager.get_stack("production").to_stack()
pipeline = Pipeline("train", stack=live_stack)
```

---

## 6. Enterprise Stack Registry

The Enterprise Stack Registry enables **platform teams** to define, govern, version, and distribute execution stacks while **data scientists** consume them transparently.

```
Pipeline Code  →  Stack Selector  →  Enterprise Registry  →  Policy Engine  →  Backend Adapter
                                                                                      ↓
                                                              Local / AzureML / Kubernetes / Databricks / Ray
```

### 6.1 Stack Definitions (YAML)

Create governed stack definitions as Kubernetes-style YAML:

```yaml
# stacks/aml_cpu_small.yaml
apiVersion: flowyml.io/v1
kind: Stack
metadata:
  name: aml_cpu_small
  version: 1.2.0
  description: Approved AzureML CPU stack for standard workloads
  owner: ml-platform-team
  tags: [azureml, cpu, production]
spec:
  backend: azureml              # local | azureml | kubernetes | ray | databricks | gcp | aws | custom
  runtime:
    pythonVersion: "3.11"
    baseImage: "myregistry.azurecr.io/flowyml/sklearn:1.2.0"
    dependencyManager: poetry   # pip | uv | poetry | conda | pipenv
    autoBuild: true
    autoPush: true
  compute:
    type: cpu                   # cpu | gpu | tpu
    size: Standard_DS3_v2
    region: francecentral
    minInstances: 0
    maxInstances: 4
  storage:
    artifactStore: azure_blob   # local | azure_blob | s3 | gcs | minio
    uri: "az://ml-artifacts/production"
  secrets:
    provider: hashicorp_vault   # azure_key_vault | aws_secrets_manager | gcp_secret_manager | hashicorp_vault | env | local
    scope: ml/production
  observability:
    logs: true
    metrics: true
    traces: true
  policies:
    allowExternalNetwork: false
    maxRuntimeMinutes: 480
    maxEstimatedCostUsd: 100.0
    allowedPythonPackages: []    # Empty = all allowed
    deniedPythonPackages: [subprocess32]
    requireSignedStack: true
  permissions:
    allowedGroups: [ml-engineers, data-scientists]
    allowedProjects: [fraud-detection, recommendation]
  security:
    signature:
      enabled: true
      provider: cosign
```

**Loading and using enterprise stacks:**

```python
from flowyml.stacks.enterprise import StackDefinition, StackResolver

# From YAML file
stack_def = StackDefinition.from_yaml("stacks/aml_cpu_small.yaml")
live_stack = stack_def.to_stack()
pipeline = Pipeline("train", stack=live_stack)

# Auto-resolve (CLI arg → env var → project config → registry default)
resolver = StackResolver.auto()
stack_def = resolver.resolve(stack="aml_cpu_small")

# Resolve from URI (Git, HTTP, local)
stack_def = resolver.resolve_from_uri("github://myorg/ml-stacks@v1.2#aml_cpu_small")
```

### 6.2 Policy Engine

Enforce governance rules before pipeline execution:

```python
from flowyml.stacks.enterprise import PolicyEngine, PolicyContext

engine = PolicyEngine()

# Built-in rules (all automatically available)
# - StackExistsRule          — Stack must exist in registry
# - StackLockedRule          — Stack version must match lock file
# - UserPermissionRule       — User must be in allowedGroups
# - ProjectPermissionRule    — Project must be in allowedProjects
# - BackendAllowedRule       — Backend must be in allowed list
# - BaseImageApprovedRule    — Docker image must be approved
# - PackageAllowListRule     — Only allowed packages
# - PackageDenyListRule      — No denied packages
# - ExternalNetworkRule      — Network access policy
# - MaxRuntimeRule           — Enforce max runtime
# - CostLimitRule            — Enforce cost caps
# - SignedStackRule          — Require cryptographic signatures

result = engine.evaluate(PolicyContext(
    stack=stack_def,
    user="data-scientist-1",
    project="fraud-detection",
))
if not result.passed:
    print(f"Policy violations: {result.violations}")
```

### 6.3 Backend Adapters

FlowyML maps pipeline concepts to platform-native primitives:

| FlowyML Concept | AzureML          | Databricks       | GCP Vertex AI     | AWS SageMaker      |
|-----------------|------------------|-------------------|-------------------|---------------------|
| Stack           | Environment + Compute | Cluster + Runtime | CustomJob Config  | Processing Job      |
| Pipeline        | Job              | Workflow          | PipelineJob       | Pipeline Execution  |
| Artifacts       | Data / Model     | MLflow Artifacts  | Artifact Registry | S3 Artifacts        |
| Secrets         | Key Vault        | Scope Secrets     | Secret Manager    | Secrets Manager     |
| Tracking        | MLflow (managed) | MLflow (built-in) | Vertex Experiments| SageMaker Experiments|

```python
# AzureML adapter
from flowyml.stacks.enterprise.adapters import AzureMLBackendAdapter

adapter = AzureMLBackendAdapter(
    subscription_id="...",
    resource_group="ml-rg",
    workspace_name="ml-workspace",
)
adapter.validate_stack(stack_def)
```

### 6.4 Secrets Management (Vault, Key Vault, etc.)

FlowyML natively supports **6 secrets providers** — configure once in the stack YAML, access transparently:

| Provider              | Config Key           | Install Extra        |
|-----------------------|----------------------|----------------------|
| HashiCorp Vault       | `hashicorp_vault`    | `hvac` package       |
| Azure Key Vault       | `azure_key_vault`    | `flowyml[azure]`     |
| AWS Secrets Manager   | `aws_secrets_manager`| `flowyml[aws]`       |
| GCP Secret Manager    | `gcp_secret_manager` | `flowyml[gcp]`       |
| Environment Variables | `env`                | Built-in             |
| Local (.env files)    | `local`              | Built-in             |

**Stack YAML configuration:**

```yaml
# HashiCorp Vault
spec:
  secrets:
    provider: hashicorp_vault
    scope: secret/data/ml/production
    # Vault address via VAULT_ADDR env var
    # Auth via VAULT_TOKEN or VAULT_ROLE_ID + VAULT_SECRET_ID

# Azure Key Vault
spec:
  secrets:
    provider: azure_key_vault
    scope: ml-keyvault-prod
    # Auth via DefaultAzureCredential (managed identity, CLI, env vars)

# AWS Secrets Manager
spec:
  secrets:
    provider: aws_secrets_manager
    scope: ml/production
    # Auth via standard AWS credential chain

# Environment variables (default)
spec:
  secrets:
    provider: env
```

> **Important**: Secrets are **never hardcoded** in FlowyML. All authentication is delegated to the native provider's credential chain (e.g., `DefaultAzureCredential`, `VAULT_TOKEN`, AWS credential chain). FlowyML just reads secrets by key from the configured provider.

---

## 7. Experiment Tracking & Tracing

FlowyML provides **transparent, built-in experiment tracking** that works automatically with pipelines, plus first-class MLflow integration for enterprise environments.

### 7.1 Built-in Experiment Tracker

Every pipeline run is automatically tracked in the SQLite metadata store and visible in the FlowyML UI:

```python
from flowyml import Experiment, Pipeline

# Create an experiment (auto-persisted to SQLite + UI)
exp = Experiment(
    name="baseline_training",
    description="Baseline model with default hyperparameters",
    tags={"team": "ml-core", "sprint": "Q2"},
)

# Run pipeline — tracking happens automatically
pipeline = Pipeline("train", context=ctx)
result = pipeline.run()

# Log additional metrics to the experiment
exp.log_run(
    run_id=result.run_id,
    metrics={"accuracy": 0.95, "f1": 0.93, "latency_ms": 12.5},
    parameters={"learning_rate": 0.01, "epochs": 100},
)

# Compare runs and find the best
best_run = exp.get_best_run(metric="accuracy", maximize=True)
comparison = exp.compare_runs(metric="accuracy")
```

**Automatic pipeline tracking** — every `pipeline.run()` automatically records:
- Run ID, status, duration
- Step-level timing and cache hits
- All parameters from the context
- Output artifacts with lineage
- GenAI metrics (tokens, cost) if applicable

### 7.2 MLflow Integration

For enterprise environments, FlowyML includes a **native MLflow tracker plugin**:

```python
from flowyml.plugins import get_plugin

# Initialize MLflow tracker
tracker = get_plugin("mlflow",
    tracking_uri="http://mlflow-server:5000",  # Or Databricks managed MLflow
    experiment_name="fraud_detection",
)

# Use directly
tracker.start_run("training_v3", tags={"model": "xgboost"})
tracker.log_params({"learning_rate": 0.01, "max_depth": 6})
tracker.log_metrics({"accuracy": 0.95, "auc": 0.97}, step=100)
tracker.log_model(model, "model", model_type="sklearn", registered_model_name="fraud_classifier")
tracker.end_run()

# Enable autologging (scikit-learn, PyTorch, TensorFlow, XGBoost)
tracker.autolog()             # All frameworks
tracker.autolog("sklearn")    # Specific framework
```

**Config-driven MLflow (recommended):**

```yaml
# flowyml.yaml
stacks:
  production:
    experiment_tracker:
      type: mlflow
      tracking_uri: ${MLFLOW_TRACKING_URI}     # Works with Databricks managed MLflow
      registry_uri: ${MLFLOW_REGISTRY_URI}      # Optional: separate model registry
      experiment_name: my_experiments
```

```python
# Code — no setup needed, config drives everything
from flowyml.plugins.stack import start_run, log_metrics, log_params, end_run

start_run("training_v3")
log_params({"lr": 0.01})
log_metrics({"accuracy": 0.95})
end_run()
```

### 7.3 Leaderboard & Run Comparison

```python
from flowyml import ModelLeaderboard, compare_runs

# Create a leaderboard from experiment runs
leaderboard = ModelLeaderboard(experiment_name="fraud_detection")
leaderboard.add_entry(
    model_name="xgboost_v1",
    metrics={"accuracy": 0.95, "f1": 0.93},
    parameters={"max_depth": 6},
)

# Compare specific runs
comparison = compare_runs(
    run_ids=["run_001", "run_002", "run_003"],
    metrics=["accuracy", "f1", "latency"],
)
```

---

## 8. GenAI Observability

FlowyML provides **deep, transparent observability** for GenAI applications — from simple LLM calls to complex multi-agent systems.

### 8.1 Framework-Agnostic Tracing

The base tracing layer works with any LLM provider and records tokens, cost, latency, and artifacts:

```python
from flowyml import trace_genai, observe_genai, span

# Context manager — trace a block of GenAI code
with trace_genai("rag_pipeline", project="chatbot") as tracer:
    # Start a span for an LLM call
    llm_span = tracer.start_span("llm", "generate_answer", inputs={"prompt": "..."})
    response = call_llm(prompt)
    llm_span.set_tokens(prompt_tokens=150, completion_tokens=80, model="gpt-4o")
    tracer.end_span(llm_span, outputs={"response": response})

    # Save artifacts (prompts, documents, intermediate results)
    tracer.save_artifact("system_prompt", "prompt", system_prompt_text)
    tracer.save_artifact("retrieved_docs", "document", documents)

# Prints a beautiful summary with tokens, cost, duration, and DAG

# Decorator — auto-trace any function
@observe_genai(name="answer_question", project="chatbot")
def answer(question: str) -> str:
    return call_llm(question)

# Generic span for custom instrumentation
@span("fetch_context")
def fetch_context(query: str) -> list:
    return vector_db.search(query)
```

**Automatic features:**
- Token counting (prompt + completion)
- Cost estimation for 20+ models (OpenAI, Anthropic, Google, Mistral, Cohere)
- Canvas DAG visualization in the FlowyML UI
- Artifact persistence (prompts, responses, documents)
- Session-level aggregation (total tokens, cost, errors)

### 8.2 LangGraph / LangChain Integration

```python
from flowyml import FlowyMLCallbackHandler, trace_graph, observe

# LangGraph — full graph tracing with node-level spans
@trace_graph(name="agent_workflow", project="support-bot")
def run_agent(question: str):
    app = create_langgraph_app()
    handler = FlowyMLCallbackHandler()
    return app.invoke({"input": question}, config={"callbacks": [handler]})

# LangChain — chain tracing
from flowyml import trace_chain, instrument_chain

@trace_chain(name="rag_chain")
def rag_query(question: str):
    chain = build_rag_chain()
    return chain.invoke(question)

# Auto-instrument existing chains
instrument_chain(my_chain, project="chatbot")
```

### 8.3 OpenAI Integration

```python
from flowyml import TracedOpenAI, patch_openai, trace_openai

# Drop-in replacement (recommended)
client = TracedOpenAI(project="my-app")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
# Automatically traced with tokens, cost, and latency

# Monkey-patch existing client
import openai
client = openai.OpenAI()
patch_openai(client, project="my-app")

# Decorator
@trace_openai(name="summarize", project="my-app")
def summarize(text: str) -> str:
    ...
```

### 8.4 Cost Estimation

FlowyML includes a built-in cost table for 20+ models:

```python
from flowyml.integrations.base import estimate_cost, MODEL_COSTS

# Automatic cost estimation
cost = estimate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
# $0.0075

# Supported models include:
# OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-4, gpt-3.5-turbo, o1, o1-mini, o3-mini
# Anthropic: claude-3-5-sonnet, claude-3-opus, claude-3-haiku
# Google: gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash
# Mistral: mistral-large, mistral-medium, mistral-small
# Cohere: command-r-plus, command-r
```

---

## 9. Evaluations Framework

Production-grade evaluation system with **29+ scorers** and adapters for DeepEval, RAGAS, and Phoenix:

```python
from flowyml.evals import evaluate, EvalDataset, EvalSuite, get_scorer, make_judge

# Create evaluation dataset
data = EvalDataset.create_genai("qa_test", examples=[
    {"input": "What is ML?", "expected": "Machine Learning is...", "actual": "ML stands for..."},
])

# Run evaluation with multiple scorers
result = evaluate(
    data=data,
    scorers=[
        get_scorer("relevance"),
        get_scorer("faithfulness"),
        get_scorer("coherence"),
        get_scorer("ragas.faithfulness"),     # RAGAS adapter
        get_scorer("deepeval.hallucination"), # DeepEval adapter
    ],
)

# Check for regressions
result.notify_if_regression(threshold=0.05)

# LLM-as-Judge
judge = make_judge(
    criteria="Evaluate the response for accuracy and helpfulness",
    model="gpt-4o",
)

# Evaluation suites for CI/CD
suite = EvalSuite("regression_tests")
suite.add_test("accuracy", get_scorer("accuracy"), min_score=0.9)
suite.add_test("latency", get_scorer("latency"), max_value=500)
suite.run(data)

# Judge Arena — compare multiple LLMs
from flowyml.evals import JudgeArena
arena = JudgeArena(models=["gpt-4o", "claude-3-5-sonnet"])
arena.run(test_prompts)

# Scheduled evaluations
from flowyml.evals import EvalSchedule
schedule = EvalSchedule(
    suite=suite,
    cron="0 */6 * * *",  # Every 6 hours
    notify_on_regression=True,
)
```

**Scorer categories:**
- **Classification**: accuracy, precision, recall, f1, auc, confusion_matrix
- **Regression**: mae, mse, rmse, r2, mape
- **GenAI**: relevance, faithfulness, coherence, toxicity, bias, hallucination
- **Adapters**: `ragas.*`, `deepeval.*`, `phoenix.*`

---

## 10. Plugin System

FlowyML's extensible plugin architecture:

```python
from flowyml.plugins import get_plugin, install, list_available

# List available plugins
plugins = list_available()

# Install and use a plugin
tracker = get_plugin("mlflow", tracking_uri="http://localhost:5000")

# Plugin types available:
# - ExperimentTracker   — MLflow, Weights & Biases (WandB)
# - ArtifactStorePlugin — GCS, S3, Azure Blob, MinIO
# - OrchestratorPlugin  — Vertex AI, SageMaker, Local
# - ContainerRegistryPlugin — GCR, ECR, DockerHub
# - ModelRegistryPlugin — MLflow Model Registry, Vertex, SageMaker
# - ModelDeployerPlugin — Vertex Endpoints, SageMaker, Cloud Run
# - DataValidatorPlugin — Deepchecks
# - AlerterPlugin       — Slack
# - FeatureStorePlugin  — (extensible base)
```

**Creating custom plugins:**

```python
from flowyml.plugins.base import ExperimentTracker, PluginMetadata, PluginType

class MyCustomTracker(ExperimentTracker):
    METADATA = PluginMetadata(
        name="my_tracker",
        description="Custom experiment tracker",
        plugin_type=PluginType.EXPERIMENT_TRACKER,
        version="1.0.0",
    )

    def start_run(self, run_name, experiment_name=None, tags=None):
        ...
    def end_run(self, status="FINISHED"):
        ...
    def log_params(self, params):
        ...
    def log_metrics(self, metrics, step=None):
        ...

# Register via entry points in pyproject.toml:
# [project.entry-points."flowyml.plugins"]
# my_tracker = "my_package:MyCustomTracker"
```

---

## 11. Cloud Provider Integrations

### 11.1 Google Cloud (Vertex AI)

```bash
pip install "flowyml[gcp]"
```

```yaml
# flowyml.yaml
stacks:
  gcp-prod:
    orchestrator:
      type: vertex_ai
      project: ${GCP_PROJECT_ID}
      region: us-central1
      service_account: ${GCP_SA}
    artifact_store:
      type: gcs
      bucket: ${GCP_BUCKET}
    container_registry:
      type: gcr
      uri: gcr.io/${GCP_PROJECT_ID}
    model_registry:
      type: vertex_model_registry
    model_deployer:
      type: vertex_endpoint
```

### 11.2 AWS (SageMaker)

```bash
pip install "flowyml[aws]"
```

```yaml
stacks:
  aws-prod:
    orchestrator:
      type: sagemaker
      region: us-east-1
      role_arn: ${SAGEMAKER_ROLE}
    artifact_store:
      type: s3
      bucket: ${S3_BUCKET}
    container_registry:
      type: ecr
      uri: ${AWS_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com
    model_registry:
      type: sagemaker_model_registry
    model_deployer:
      type: sagemaker
```

### 11.3 Azure ML

```bash
pip install "flowyml[azure]"
```

```yaml
stacks:
  azure-prod:
    orchestrator:
      type: azure_ml
      subscription_id: ${AZURE_SUBSCRIPTION_ID}
      resource_group: ${AZURE_RG}
      workspace_name: ${AZURE_WORKSPACE}
    artifact_store:
      type: azure_blob
      container: ml-artifacts
    # Auth via DefaultAzureCredential (Managed Identity, CLI, env vars)
```

**Enterprise stack YAML for AzureML:**

```yaml
apiVersion: flowyml.io/v1
kind: Stack
metadata:
  name: azureml_production
  version: 2.0.0
  owner: ml-platform
spec:
  backend: azureml
  runtime:
    pythonVersion: "3.11"
    baseImage: "myregistry.azurecr.io/flowyml/base:latest"
  compute:
    type: gpu
    size: Standard_NC6s_v3
    region: westeurope
  storage:
    artifactStore: azure_blob
    uri: "az://ml-artifacts/production"
  secrets:
    provider: azure_key_vault
    scope: ml-keyvault-prod
```

### 11.4 Databricks

FlowyML supports Databricks as an enterprise backend. Use the `databricks` backend in stack definitions:

```yaml
apiVersion: flowyml.io/v1
kind: Stack
metadata:
  name: databricks_production
  version: 1.0.0
  owner: ml-platform
  tags: [databricks, production, mlflow]
spec:
  backend: databricks
  runtime:
    pythonVersion: "3.11"
  compute:
    type: gpu
    size: Standard_NC6s_v3
  storage:
    artifactStore: s3           # Or azure_blob depending on Databricks workspace
    uri: "s3://databricks-ml-artifacts/"
  secrets:
    provider: hashicorp_vault   # Or env for Databricks-native secrets
    scope: databricks/production
  observability:
    logs: true
    metrics: true
    traces: true
```

**Databricks + MLflow tracking (managed MLflow):**

```yaml
# flowyml.yaml
stacks:
  databricks:
    experiment_tracker:
      type: mlflow
      tracking_uri: databricks    # Uses Databricks-managed MLflow
```

```python
# In code — MLflow is natively available in Databricks
from flowyml.plugins import get_plugin

tracker = get_plugin("mlflow", tracking_uri="databricks")
tracker.start_run("training_v1", experiment_name="/Shared/fraud_detection")
tracker.log_params({"lr": 0.01})
tracker.log_metrics({"accuracy": 0.95})
tracker.log_model(model, "model", registered_model_name="fraud_classifier")
tracker.autolog()  # Enable autologging for sklearn/pytorch/etc.
tracker.end_run()
```

> **Note**: When running on Databricks, set `tracking_uri: databricks` or use the `MLFLOW_TRACKING_URI=databricks` environment variable. FlowyML's MLflow tracker automatically delegates to the managed MLflow instance.

---

## 12. Monitoring & Notifications

```python
from flowyml import (
    trace_llm, detect_drift, compute_stats,
    configure_notifications, NotificationManager,
    ConsoleNotifier, SlackNotifier, EmailNotifier,
)

# Data drift detection
drift_result = detect_drift(reference_data, production_data)

# Compute data statistics
stats = compute_stats(dataset)

# LLM call tracing
@trace_llm(name="generate_summary")
def generate(text: str) -> str:
    return openai.chat.completions.create(...)

# Notifications
configure_notifications(
    slack_webhook="https://hooks.slack.com/...",
    email_config={"smtp_host": "...", "from": "alerts@company.com"},
)

notifier = NotificationManager()
notifier.send("Pipeline completed!", channel="slack")

# Observability with Prometheus & OpenTelemetry
from flowyml.core.observability import PrometheusMetricsCollector, set_metrics_collector

set_metrics_collector(PrometheusMetricsCollector())

# FlowyML includes OpenTelemetry instrumentation:
# - opentelemetry-api
# - opentelemetry-sdk
# - opentelemetry-instrumentation-fastapi
# - opentelemetry-exporter-prometheus
```

---

## 13. Model Registry & Serving

```python
from flowyml import ModelRegistry, ModelVersion, ModelStage

# Built-in model registry
registry = ModelRegistry()
registry.register(
    name="fraud_classifier",
    model=model,
    version="1.0.0",
    stage=ModelStage.STAGING,
    metadata={"accuracy": 0.95, "framework": "sklearn"},
)

# Promote to production
registry.transition_stage("fraud_classifier", "1.0.0", ModelStage.PRODUCTION)

# Load a model
model = registry.load("fraud_classifier", version="1.0.0")

# Model serving (FastAPI-based)
from flowyml.serving import ModelServer

server = ModelServer(model=model, name="fraud-api")
server.serve(host="0.0.0.0", port=8080)
# Serves at /predict with automatic request/response validation
```

**Cloud model registries** (via plugins):
- **Vertex AI Model Registry** — `type: vertex_model_registry`
- **SageMaker Model Registry** — `type: sagemaker_model_registry`
- **MLflow Model Registry** — `type: mlflow`

---

## 14. CLI Reference

```bash
# Project management
flowyml init [project-name]        # Initialize a new project
flowyml run <pipeline.py>          # Run a pipeline
flowyml run <pipeline.py> --stack production  # Run with specific stack

# Stack management
flowyml stack list                 # List configured stacks
flowyml stack show [name]          # Show stack details
flowyml stack set <name>           # Set active stack
flowyml stack init --tracker mlflow --store gcs  # Initialize stack config

# Experiments
flowyml experiment list            # List experiments
flowyml experiment show <name>     # Show experiment details
flowyml experiment compare         # Compare runs

# Models
flowyml model list                 # List registered models
flowyml model serve <name>         # Serve a model
flowyml model deploy <name>        # Deploy to cloud endpoint

# Plugins
flowyml plugin list                # List available plugins
flowyml plugin install <name>      # Install a plugin

# Evaluations
flowyml eval run <suite>           # Run evaluation suite
flowyml eval compare               # Compare evaluation results

# UI Dashboard
flowyml ui                         # Launch the web dashboard

# Enterprise
flowyml enterprise stack list      # List enterprise stacks
flowyml enterprise stack validate  # Validate stack definitions
flowyml enterprise audit           # View audit logs

# Templates
flowyml template list              # List available pipeline templates
flowyml template create <name>     # Create from template
```

---

## 15. Configuration Reference (flowyml.yaml)

Complete reference for `flowyml.yaml`:

```yaml
# ─── Stack Definitions ───
stacks:
  <stack-name>:
    orchestrator:
      type: local | vertex_ai | sagemaker | azure_ml
      # Provider-specific config...
    artifact_store:
      type: local | gcs | s3 | azure_blob | minio
      path: <local-path>       # For local
      bucket: <bucket-name>    # For cloud
    experiment_tracker:
      type: mlflow
      tracking_uri: <uri>
      experiment_name: <name>
    model_registry:
      type: vertex_model_registry | sagemaker_model_registry | mlflow
    model_deployer:
      type: vertex_endpoint | sagemaker | gcp_cloud_run
    container_registry:
      type: gcr | ecr | dockerhub
      uri: <registry-uri>
    alerter:
      type: slack
      webhook_url: <url>
    data_validator:
      type: deepchecks
    metadata_store:
      path: <db-path>
    artifact_routing:
      Model:
        store: <store-name>
        path: "{run_id}/models/{artifact_name}"
        register: true | false
        deploy: true | false
        deploy_condition: manual | auto | on_approval
        deploy_min_metrics: { accuracy: 0.9 }
      Dataset:
        store: <store-name>
        path: "{run_id}/data/{artifact_name}"
      Metrics:
        log_to_tracker: true

# ─── Active Stack ───
active_stack: local

# ─── Resource Profiles ───
resources:
  default:
    cpu: "2"
    memory: "8Gi"
  gpu_training:
    cpu: "8"
    memory: "32Gi"
    gpu: nvidia-tesla-v100
    gpu_count: 2

# ─── Docker Config ───
docker:
  base_image: "python:3.11-slim"
  dockerfile: ./Dockerfile
  use_poetry: true
  env_vars:
    PYTHONUNBUFFERED: "1"
```

---

## 16. Common Patterns & Recipes

### Full ML Training Pipeline with Tracking

```python
from flowyml import Pipeline, step, context, Experiment, Model, Dataset, Metrics

@step(outputs=["dataset"])
def load_data(source: str = "data.csv") -> Dataset:
    import pandas as pd
    df = pd.read_csv(source)
    return Dataset(data=df, name="training_data")

@step(inputs=["dataset"], outputs=["model"])
def train(dataset: Dataset, learning_rate: float = 0.01) -> Model:
    from sklearn.ensemble import GradientBoostingClassifier
    X, y = dataset.data.drop("target", axis=1), dataset.data["target"]
    clf = GradientBoostingClassifier(learning_rate=learning_rate)
    clf.fit(X, y)
    return Model(obj=clf, name="gb_classifier", framework="sklearn")

@step(inputs=["model", "dataset"], outputs=["metrics"])
def evaluate(model: Model, dataset: Dataset) -> Metrics:
    X, y = dataset.data.drop("target", axis=1), dataset.data["target"]
    score = model.obj.score(X, y)
    return Metrics(values={"accuracy": score}, name="eval_results")

# Configure and run
exp = Experiment(name="gradient_boosting", description="GB classifier experiments")
ctx = context(learning_rate=0.05, source="s3://bucket/data.csv")

pipeline = Pipeline("training", context=ctx)
pipeline.add_step(load_data).add_step(train).add_step(evaluate)

result = pipeline.run()
exp.log_run(result.run_id, metrics=result.outputs.get("metrics"))
```

### GenAI RAG Pipeline with Tracing

```python
from flowyml import Pipeline, step, trace_genai, observe_genai

@step(outputs=["context"])
@observe_genai(name="retrieve_docs", project="chatbot")
def retrieve(query: str):
    docs = vector_store.similarity_search(query, k=5)
    return docs

@step(inputs=["context"], outputs=["answer"])
def generate(context, query: str):
    with trace_genai("generate_answer", project="chatbot") as tracer:
        prompt = f"Context: {context}\n\nQuestion: {query}"
        tracer.save_artifact("prompt", "prompt", prompt)

        span = tracer.start_span("llm", "gpt4o_generate")
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        span.set_tokens(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            model="gpt-4o",
        )
        answer = response.choices[0].message.content
        tracer.end_span(span, outputs={"answer": answer})

    return answer
```

### Enterprise Pipeline with Vault + AzureML

```python
from flowyml import Pipeline, step
from flowyml.stacks.enterprise import StackDefinition, StackResolver

# Resolve the enterprise stack (reads from flowyml.yaml → FLOWYML_STACK env → registry)
resolver = StackResolver.auto()
stack_def = resolver.resolve()

# Secrets are automatically resolved from the configured provider (e.g., Vault)
pipeline = Pipeline("enterprise_train", stack=stack_def.to_stack())
pipeline.add_step(load_data)
pipeline.add_step(train_model)
pipeline.add_step(evaluate)
pipeline.run()
```

### Keras Integration

```python
from flowyml import FlowymlKerasCallback

# Add to any Keras training for automatic tracking
model.fit(
    X_train, y_train,
    epochs=100,
    callbacks=[FlowymlKerasCallback(
        pipeline_name="keras_training",
        log_weights=True,
    )],
)
```

### Pipeline Scheduling

```python
from flowyml import PipelineScheduler

scheduler = PipelineScheduler()
scheduler.schedule(
    pipeline=training_pipeline,
    cron="0 2 * * *",          # Every day at 2 AM
    name="nightly_retrain",
    context=context(source="latest"),
)
scheduler.start()
```

### Pipeline Versioning & Snapshots

```python
from flowyml import VersionedPipeline, freeze_pipeline

versioned = VersionedPipeline(pipeline, version="1.0.0")
snapshot = freeze_pipeline(pipeline)  # Immutable snapshot with all code + config
```

---

## 17. Testing

```bash
# Run all tests
pytest

# Run with parallel execution
pytest -n auto --dist=worksteal

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests

# Coverage report
pytest --cov=flowyml --cov-report=html
```

**Writing tests for FlowyML pipelines:**

```python
import pytest
from flowyml import Pipeline, step, context

def test_pipeline_execution():
    @step(outputs=["result"])
    def add(a: int = 1, b: int = 2):
        return a + b

    ctx = context(a=3, b=4)
    pipeline = Pipeline("test", context=ctx)
    pipeline.add_step(add)

    result = pipeline.run()
    assert result.success
    assert result.outputs["result"] == 7
```

---

## Quick Import Reference

```python
# ─── Core ───
from flowyml import Pipeline, step, context, Context

# ─── Assets ───
from flowyml import Model, Dataset, Metrics, Prompt, Checkpoint, FeatureSet, Report, Artifact

# ─── Control Flow ───
from flowyml import when, unless, If, Switch, map_task, dynamic, sub_pipeline

# ─── Error Handling ───
from flowyml import retry, on_failure, CircuitBreaker, RetryConfig

# ─── Stacks ───
from flowyml import Stack, LocalStack, use_stack, ResourceConfig

# ─── Enterprise ───
from flowyml.stacks.enterprise import StackDefinition, EnterpriseStackRegistry, PolicyEngine, StackResolver

# ─── Tracking ───
from flowyml import Experiment, Run, ModelLeaderboard, compare_runs

# ─── Plugins (MLflow, etc.) ───
from flowyml.plugins import get_plugin, install, list_available
from flowyml.plugins.stack import start_run, end_run, log_params, log_metrics, log_artifact

# ─── GenAI Observability ───
from flowyml import trace_genai, observe_genai, span, BaseTracer, TraceSession, TraceSpan
from flowyml import FlowyMLCallbackHandler, trace_graph  # LangGraph
from flowyml import TracedOpenAI, patch_openai             # OpenAI
from flowyml import trace_chain, instrument_chain           # LangChain

# ─── Evaluations ───
from flowyml.evals import evaluate, EvalDataset, EvalSuite, get_scorer, make_judge, JudgeArena

# ─── Monitoring ───
from flowyml import trace_llm, detect_drift, compute_stats
from flowyml import configure_notifications, SlackNotifier, EmailNotifier

# ─── Model Registry & Serving ───
from flowyml import ModelRegistry, ModelVersion, ModelStage
from flowyml.serving import ModelServer

# ─── Storage ───
from flowyml import ArtifactCatalog, ArtifactStore, LocalArtifactStore

# ─── Advanced ───
from flowyml import PipelineScheduler, VersionedPipeline, freeze_pipeline
from flowyml import SmartCache, ContentBasedCache, memoize
from flowyml import StepDebugger, PipelineDebugger, debug_step, profile_step
from flowyml import FlowymlKerasCallback
```

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `FLOWYML_STACK` | Active stack name | `production` |
| `FLOWYML_ENV` | Environment name (resolves to stack via config) | `staging` |
| `MLFLOW_TRACKING_URI` | MLflow server URI | `http://mlflow:5000` or `databricks` |
| `VAULT_ADDR` | HashiCorp Vault address | `https://vault.company.com:8200` |
| `VAULT_TOKEN` | Vault authentication token | `s.xxxxx` |
| `GCP_PROJECT_ID` | Google Cloud project | `my-gcp-project` |
| `AWS_DEFAULT_REGION` | AWS region | `us-east-1` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription | `xxxxxxxx-xxxx-...` |

---

> **Built with ❤️ by [UnicoLab](https://unicolab.ai)**

# Welcome to UniFlow 🌊

<p align="center">
  <img src="logo.png" width="350" alt="UniFlow Logo"/>
  <br>
  <em>The Enterprise-Grade ML Pipeline Framework for Humans</em>
</p>

---

**UniFlow** is a production-ready ML pipeline orchestration framework designed to bridge the gap between rapid experimentation and enterprise deployment. It combines the simplicity of a Python script with the power of a full-fledged MLOps platform.

<div class="grid cards" markdown>

-   :rocket: **Zero Boilerplate**
    ---
    Define steps as pure Python functions. No YAML, no DSLs, no complex wiring. Just code.

-   :brain: **Auto-Context Injection**
    ---
    Parameters are automatically injected into steps based on type hints and names.

-   :zap: **Smart Caching**
    ---
    Intelligent caching strategies (code hash, input hash) to skip redundant computations.

-   :eye: **Real-Time UI**
    ---
    Beautiful, dark-mode dashboard to monitor pipelines, visualize DAGs, and inspect artifacts.

</div>

## 🌟 Everything You Can Do

UniFlow is packed with features to handle every aspect of the ML lifecycle.

### 🏗️ Core Orchestration
- **Unified Pipelines**: Define DAGs using standard Python functions.
- **Conditional Execution**: Dynamic branching logic (`If`, `Switch`) based on runtime data.
- **Parallel Execution**: Run independent steps concurrently on threads or processes.
- **Pipeline Templates**: Reusable workflow patterns for standardizing team practices.
- **Human-in-the-Loop**: Pause pipelines for manual approval steps.

### 📦 Asset Management
- **First-Class Assets**: Specialized classes for `Dataset`, `Model`, `Metrics`, and `FeatureSet`.
- **Lineage Tracking**: Automatically track the provenance of every artifact.
- **Model Registry**: Version and manage models from development to production.
- **Artifact Store**: Pluggable storage backends (Local, S3, GCS, Azure).

### 🏭 Production Features
- **Project Isolation**: Multi-tenant support with isolated workspaces.
- **Pipeline Versioning**: Git-like versioning for pipelines. Compare and rollback.
- **Automated Scheduling**: Cron-style scheduling for recurring jobs.
- **Notifications**: Alerts via Slack, Email, or custom webhooks on success/failure.
- **Error Handling**: Automatic retries, circuit breakers, and fallback logic.

### 🔍 Observability & Debugging
- **Interactive Debugging**: Breakpoints (`StepDebugger`) and execution tracing.
- **LLM Tracing**: Trace GenAI calls (tokens, latency, cost) with `@trace_llm`.
- **Data Drift Detection**: Monitor distribution shifts with Population Stability Index (PSI).
- **Model Leaderboard**: Track and compare model performance across runs.
- **System Monitoring**: Built-in CPU/Memory and pipeline health monitoring.

### 🔌 Integrations
- **Framework Agnostic**: Works with PyTorch, TensorFlow, Keras, Scikit-learn, HuggingFace.
- **Cloud Native**: Deploy execution to Vertex AI, AWS SageMaker (coming soon).
- **Keras Callback**: Automatic experiment tracking for Keras models.

## ⚡️ Quick Start

```python
from uniflow import Pipeline, step, context

@step(outputs=["dataset"])
def load_data():
    return [1, 2, 3, 4, 5]

@step(inputs=["dataset"], outputs=["model"])
def train_model(dataset, learning_rate: float = 0.01):
    # 'learning_rate' is automatically injected from context!
    print(f"Training on {len(dataset)} items with lr={learning_rate}")
    return "my_trained_model"

# Run it!
ctx = context(learning_rate=0.05)
pipeline = Pipeline("quickstart", context=ctx)
pipeline.add_step(load_data)
pipeline.add_step(train_model)

pipeline.run()
```

## 📚 Documentation Guide

<div class="grid cards" markdown>

-   :rocket: **[Getting Started](getting-started.md)**
    ---
    Build your first pipeline in 5 minutes.

-   :book: **[User Guide](user-guide/projects.md)**
    ---
    Master projects, versioning, and scheduling.

-   :zap: **[Advanced Features](advanced/caching.md)**
    ---
    Deep dive into caching, parallelism, and debugging.

-   :plug: **[Integrations](integrations/keras.md)**
    ---
    Connect with Keras, GCP, and more.

</div>

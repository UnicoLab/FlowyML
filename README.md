# 🌊 UniFlow

<p align="center">
  <img src="docs/logo.png" width="350" alt="UniFlow Logo"/>
  <br>
  <em>The Enterprise-Grade ML Pipeline Framework for Humans</em>
  <br>
  <br>
  <p align="center">
    <a href="https://github.com/UnicoLab/UniFlow/actions"><img src="https://img.shields.io/github/actions/workflow/status/UnicoLab/UniFlow/ci.yml?branch=main" alt="CI Status"></a>
    <a href="https://pypi.org/project/uniflow/"><img src="https://img.shields.io/pypi/v/uniflow" alt="PyPI Version"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
    <a href="https://unicolab.ai"><img src="https://img.shields.io/badge/UnicoLab-ai-red.svg" alt="UnicoLab"></a>
  </p>
</p>

---

**UniFlow** is the comprehensive ML pipeline framework that combines the **simplicity of a Python script** with the **power of an enterprise MLOps platform**.

## 🚀 Why UniFlow?

| Feature | UniFlow | Traditional Orchestrators |
|---------|---------|---------------------------|
| **Developer Experience** | 🐍 **Native Python** - No DSLs, no YAML hell. | 📜 Complex YAML or rigid DSLs. |
| **Context Awareness** | 🧠 **Auto-Injection** - Params are just function args. | 🔌 Manual wiring of every parameter. |
| **Caching** | ⚡ **Multi-Level** - Smart content-hashing & memoization. | 🐢 Basic file-timestamp checking. |
| **Asset Management** | 📦 **First-Class Assets** - Models & Datasets with lineage. | 📁 Generic file paths only. |
| **Architecture** | 🏗️ **Modular Stacks** - Local, Cloud, Hybrid. | 🔒 Vendor lock-in or complex setup. |

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
- **API Execution**: Trigger pipelines remotely via REST API.

## 📦 Installation

```bash
# Install core
poetry add uniflow

# Install with UI support
poetry add "uniflow[ui]"

# Install with all features (recommended for dev)
poetry add "uniflow[all]"
```

## ⚡ Quick Start

```python
from uniflow import Pipeline, step, context, Dataset, Model

# 1. Define your configuration (Auto-injected!)
ctx = context(
    learning_rate=0.01,
    batch_size=32,
    epochs=10
)

# 2. Define your steps (Pure Python)
@step(outputs=["dataset"])
def load_data(batch_size: int):
    # 'batch_size' is automatically injected from context!
    print(f"Loading data with batch size: {batch_size}")
    return Dataset.create(data=[1, 2, 3], name="mnist")

@step(inputs=["dataset"], outputs=["model"])
def train(dataset: Dataset, learning_rate: float, epochs: int):
    print(f"Training on {dataset.name} with lr={learning_rate}")
    # Simulate training...
    return Model.create(artifact={"weights": "..."}, score=0.98)

# 3. Run it!
pipeline = Pipeline("mnist_training", context=ctx)
pipeline.add_step(load_data)
pipeline.add_step(train)

result = pipeline.run()

print(f"Run ID: {result.run_id}")
print(f"Model Score: {result.outputs['model'].score}")
```

## 🖥️ The UniFlow UI

Visualize your workflows, inspect artifacts, and monitor runs in real-time.

```bash
# Start the UI server
uniflow ui start --open-browser
```

Visit **http://localhost:8080** to access the dashboard.

## 📚 Documentation

- **[Getting Started](docs/getting-started.md)**: Your first 5 minutes with UniFlow.
- **[Core Concepts](docs/core/pipelines.md)**: Deep dive into Pipelines, Steps, and Context.
- **[Advanced Features](docs/advanced/caching.md)**: Learn about Caching, Parallelism, and Conditional Execution.
- **[API Reference](docs/api/core.md)**: Detailed class and function documentation.

## 🤝 Contributing

We love contributions! Check out our [Contributing Guide](CONTRIBUTING.md) to get started.

## 📝 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---
<p align="center">
  <strong>Built with ❤️ by <a href="https://unicolab.ai">UnicoLab</a></strong>
</p>

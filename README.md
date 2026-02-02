# 🌊 flowyml

<p align="center">
  <img src="docs/logo.png" width="350" alt="flowyml Logo"/>
  <br>
  <em>The Enterprise-Grade ML Pipeline Framework for Humans</em>
  <br>
  <br>
  <p align="center">
    <a href="https://github.com/UnicoLab/FlowyML/actions"><img src="https://img.shields.io/github/actions/workflow/status/UnicoLab/FlowyML/ci.yml?branch=main" alt="CI Status"></a>
    <a href="https://pypi.org/project/flowyml/"><img src="https://img.shields.io/pypi/v/flowyml" alt="PyPI Version"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
    <a href="https://unicolab.ai"><img src="https://img.shields.io/badge/UnicoLab-ai-red.svg" alt="UnicoLab"></a>
  </p>
</p>

---

**FlowyML** is a lightweight yet powerful ML pipeline orchestration framework. It bridges the gap between rapid experimentation and enterprise production by making assets first-class citizens. Write pipelines in pure Python, and scale them to production without changing a single line of code.

## 🚀 Why FlowyML?

| Feature | FlowyML | Traditional Orchestrators |
|---------|---------|---------------------------|
| **Developer Experience** | 🐍 **Native Python** - No DSLs, no YAML hell. | 📜 Complex YAML or rigid DSLs. |
| **Type-Based Routing** | 🧠 **Auto-Routing** - Define WHAT, we handle WHERE. | 🔌 Manual wiring to cloud buckets. |
| **Smart Caching** | ⚡ **Multi-Level** - Smart content-hashing skips re-runs. | 🐢 Basic file-timestamp checking. |
| **Asset Management** | 📦 **First-Class Assets** - Models & Datasets with lineage. | 📁 Generic file paths only. |
| **Multi-Stack** | 🌍 **Abstract Infra** - Switch local/prod with one env var. | 🔒 Vendor lock-in or complex setup. |
| **GenAI Ready** | 🤖 **LLM Tracing** - Built-in token & cost tracking. | 🧩 Requires external tools. |

---

## ⚡️ Quick Start

This is a complete, multi-step ML pipeline with auto-injected context:

```python
from flowyml import Pipeline, step, context

@step(outputs=["dataset"])
def load_data(batch_size: int = 32):
    return [i for i in range(batch_size)]

@step(inputs=["dataset"], outputs=["model"])
def train_model(dataset, learning_rate: float = 0.01):
    print(f"Training on {len(dataset)} items with lr={learning_rate}")
    return "model_v1"

# Configure and Run
ctx = context(learning_rate=0.05, batch_size=64)
pipeline = Pipeline("quickstart", context=ctx)
pipeline.add_step(load_data).add_step(train_model)

pipeline.run()
```

---

## 🌟 Key Features

### 1. 🧠 Type-Based Artifact Routing (New in 1.8.0)
Define artifact types in code, and FlowyML automatically routes them to your cloud infrastructure.
```python
@step
def train(...) -> Model:
    # Auto-saved to GCS/S3 and registered to Vertex AI / SageMaker
    return Model(obj, name="classifier")
```

### 2. 🌍 Multi-Stack Configuration
Manage local, staging, and production environments in a single `flowyml.yaml`.
```bash
export FLOWYML_STACK=production
python pipeline.py  # Now runs on Vertex AI with GCS storage
```

### 3. 🛡️ Intelligent Step Grouping
Group consecutive steps to run in the same container. Perfect for reducing overhead while maintaining clear step boundaries.

### 4. 📊 Built-in Observability
Beautiful dark-mode dashboard to monitor pipelines, visualize DAGs, and inspect artifacts in real-time.

---

## 📦 Installation

```bash
# Install core
pip install flowyml

# Install with everything (recommended)
pip install "flowyml[all]"
```

## 📚 Documentation

Visit [docs.flowyml.ai](https://docs.flowyml.ai) for:
- **[Getting Started](https://docs.flowyml.ai/getting-started)**
- **[Core Concepts](https://docs.flowyml.ai/core/pipelines)**
- **[Type-Based Routing](https://docs.flowyml.ai/plugins/type_routing)**
- **[API Reference](https://docs.flowyml.ai/api/core)**

---
<p align="center">
  <strong>Built with ❤️ by <a href="https://unicolab.ai">UnicoLab</a></strong>
</p>

# Welcome to FlowyML 🌊

<p align="center">
  <img src="logo.png" width="400" alt="flowyml Logo"/>
  <br>
  <strong>The Enterprise-Grade ML Pipeline Framework for Humans</strong>
</p>

---

**FlowyML** is designed for the modern MLOps team that values speed, reproducibility, and simplicity. We combine the **simplicity of a Python script** with the **scaling power of an enterprise platform**.

> [!TIP]
> **The FlowyML Promise**: Write your code once locally. Scale it to Vertex AI or SageMaker in production by changing a single environment variable. No refactoring, no infrastructure code in your business logic.

---

## 💎 The FlowyML Philosophy

Why do teams choose FlowyML over traditional orchestrators?

1.  **Pure Python, Zero DSLs**: If you can write a Python function, you can write a FlowyML pipeline. No complex YAML structures or rigid DSLs to learn.
2.  **Infrastructure as a Detail**: Treat your cloud infrastructure as a configuration choice, not a coding requirement.
3.  **Asset-First Lineage**: We don't just track files; we track **Assets**. Models, Datasets, and Metrics are first-class citizens with automatic lineage and metadata.
4.  **Developer Happiness**: Intelligent caching, local debugging, and a beautiful UI make iteration loops significantly faster.

---

## 🌟 Next-Gen Execution Engine

### 🧠 Type-Based Artifact Routing
*New in 1.8.0.* Define **WHAT** an artifact is, and let FlowyML handle **WHERE** it goes.
```python
@step
def train_model(...) -> Model:
    # Automatically saved to GCS/S3 and registered
    # to your Model Registry (Vertex AI, SageMaker, etc.)
    return Model(obj, name="classifier", version="1.0.0")
```

### 🌍 Multi-Stack Context
Switch between Local, Staging, and Production environments instantly. Your code remains clean while FlowyML handles the infrastructure heavy lifting.
```bash
# Locally: uses local disk and orchestrator
python pipeline.py

# Production: uses Vertex AI, GCS, and Model Registry
FLOWYML_STACK=gcp-prod python pipeline.py
```

### ⚡ Intelligent Caching & Observability
Never re-run the same computation twice. Our smart caching system (code hash + input hash) saves time and money. Monitor everything in real-time with our **premium dark-mode UI**.

---

## 🔌 The Universal Plugin Ecosystem

FlowyML features a **powerful native plugin system** that allows you to integrate with ANY ML tool without adding heavy framework dependencies to your core project.

<div class="grid cards" markdown>

-   :material-cloud-sync: **Orchestrators**
    ---
    **Vertex AI**, **SageMaker**, **Kubernetes**, **Ray**, **Airflow**.

-   :material-database: **Storage**
    ---
    **GCS**, **S3**, **Azure Blob**, **Local FS**.

-   :material-chart-bell-curve-cumulative: **Trackers**
    ---
    **MLflow**, **Weights & Biases**, **Neptune**, **TensorBoard**.

-   :material-robot-industrial: **Registries & Deployers**
    ---
    **Vertex AI**, **SageMaker**, **MLflow**, **Kubernetes Endpoints**.

</div>

---

## ⚡️ Quick Start in 30 Seconds

This is a complete, multi-step ML pipeline with auto-injected context and typed outputs.

```python
from flowyml import Pipeline, step, context, Model

@step(outputs=["dataset"])
def load_data():
    return [1, 2, 3, 4, 5]

@step(inputs=["dataset"], outputs=["model"])
def train_model(dataset, learning_rate: float = 0.01) -> Model:
    # 'learning_rate' is automatically injected from context!
    print(f"Training on {len(dataset)} items with lr={learning_rate}")
    return Model(data="weights", name="mnist_model", version="1.0.0")

# Configure and Run
ctx = context(learning_rate=0.05)
pipeline = Pipeline("quickstart", context=ctx)
pipeline.add_step(load_data).add_step(train_model)

pipeline.run()
```

---

## 🗺️ Master the Platform

<div class="grid cards" markdown>

-   :rocket: **[Getting Started](getting-started.md)**
    ---
    Build your first pipeline in 5 minutes. Learn the basics of Steps and Pipelines.

-   :book: **[Core Concepts](core/pipelines.md)**
    ---
    Deep dive into the heart of FlowyML: Pipelines, Steps, Context, and Asset Lineage.

-   :zap: **[Advanced Features](advanced/caching.md)**
    ---
    Master Caching, Parallelism, Conditional Execution, and Step Grouping.

-   :chart_with_upwards_trend: **[User Guide](user-guide/projects.md)**
    ---
    Versioning, scheduling, model leaderboards, and UI metrics.

-   :plug: **[Plugins & Stacks](plugins/overview.md)**
    ---
    Cloud integrations, model registries, type-based routing, and stack management.

-   :test_tube: **[Practical Examples](#️-ready-to-use-examples)**
    ---
    Browse working code for pipelines, UI integration, and cloud deployments.

-   :hammer_and_wrench: **[API Reference](api/core.md)**
    ---
    Full technical documentation for classes, functions, and decorators.

</div>

---

## 🏗️ Practical Examples

Explore real-world implementations in the [examples/](https://github.com/UnicoLab/FlowyML/tree/main/examples) directory:

-   **[Complete Demo](https://github.com/UnicoLab/FlowyML/blob/main/examples/complete_demo.py)**: A massive tour of versioning, projects, notifications, and data drift detection.
-   **[Pipeline Showcase](https://github.com/UnicoLab/FlowyML/blob/main/examples/pipeline_showcase.py)**: Complex branching, caching, and multi-asset management.
-   **[UI Integration](https://github.com/UnicoLab/FlowyML/blob/main/examples/ui_integration_example.py)**: How to monitor your pipelines in real-time with the web dashboard.
-   **[Conditional execution](https://github.com/UnicoLab/FlowyML/blob/main/examples/conditional_pipeline.py)**: Dynamic workflows that branch based on data quality or metrics.
-   **[Resource Optimization](https://github.com/UnicoLab/FlowyML/blob/main/examples/step_grouping_example.py)**: Using Step Grouping to optimize compute costs and performance.
-   **[Advanced Orchestration](https://github.com/UnicoLab/FlowyML/blob/main/examples/advanced_orchestration.py)**: Master lifecycle hooks and retry policies.
-   **[Simple Pipeline](https://github.com/UnicoLab/FlowyML/blob/main/examples/simple_pipeline.py)**: The absolute basics of FlowyML.

---

**Questions?** [Open an issue on GitHub](https://github.com/UnicoLab/FlowyML/issues) or join our community of MLOps enthusiasts.

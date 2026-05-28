---
title: FAQ — FlowyML
description: "Frequently asked questions about FlowyML — the artifact-centric ML pipeline framework. Covers setup, features, deployment, and comparisons."
---

<div class="hero-section" markdown>

## ❓ Frequently Asked Questions

Quick answers to the most common questions about FlowyML.

<span class="feature-badge">🤔 Common Questions</span>
<span class="feature-badge">💡 Quick Answers</span>
<span class="feature-badge">🔗 Deep Links</span>

</div>

<div class="faq-section" markdown>

## Getting Started

??? question "What is FlowyML and how is it different from Airflow or Prefect?"
    FlowyML is an **artifact-centric** ML pipeline framework. Unlike Airflow and Prefect which are task-based (you wire steps together with arrows), FlowyML steps declare what data they **produce** and **consume**. The execution graph builds itself automatically.

    This means zero manual DAG wiring, automatic data lineage, and type-safe connections between steps.

    [:octicons-arrow-right-24: Full comparison →](why-flowyml.md)

??? question "What Python version does FlowyML require?"
    FlowyML requires **Python 3.10 or higher**. We recommend using the latest stable Python release for the best performance.

    ```bash
    python --version  # Must be 3.10+
    pip install flowyml
    ```

    [:octicons-arrow-right-24: Installation guide →](INSTALLATION.md)

??? question "Can I use FlowyML with my existing MLflow or Weights & Biases setup?"
    Yes! FlowyML integrates natively with both MLflow and W&B through its **plugin system**. You can log experiments, track metrics, and manage models using your existing infrastructure.

    ```python
    # Example: MLflow integration
    from flowyml.plugins import MLflowTracker
    pipeline.with_plugin(MLflowTracker(tracking_uri="http://localhost:5000"))
    ```

    [:octicons-arrow-right-24: MLflow integration →](integrations/mlflow.md) · [:octicons-arrow-right-24: W&B integration →](integrations/wandb.md)

## Architecture & Design

??? question "What does 'artifact-centric' actually mean?"
    In FlowyML, **artifacts are first-class citizens**. Instead of defining execution order manually, you define:

    - What each step **outputs** (e.g., a `Model`, `Dataset`, or `Metrics`)
    - What each step **inputs** (consumes from other steps)

    FlowyML automatically resolves dependencies and builds the DAG. This means you never write `step_a >> step_b` arrows.

    [:octicons-arrow-right-24: Artifact-centric philosophy →](artifact-centric.md)

??? question "How does FlowyML's caching work?"
    FlowyML uses **content-based hashing** to determine if a step needs re-execution. It computes a hash from:

    - The step's source code
    - Input artifact content hashes
    - Step configuration parameters

    If the hash matches a previous run, the step is skipped and cached results are used. This is more reliable than file-timestamp caching.

    [:octicons-arrow-right-24: Caching guide →](advanced/caching.md)

??? question "What's the relationship between FlowyML and FlowyML Notebook?"
    **FlowyML** is the pipeline framework — it runs production ML workflows.

    **FlowyML Notebook** is a companion reactive notebook environment (replacing Jupyter) designed for ML experimentation. Notebooks can be promoted to FlowyML pipelines with one click.

    They work together but are independent packages:
    ```bash
    pip install flowyml           # The pipeline framework
    pip install flowyml-notebook   # The reactive notebook
    ```

    [:octicons-arrow-right-24: FlowyML Notebook →](flowyml-notebook.md)

## Deployment & Production

??? question "How do I deploy FlowyML to production?"
    FlowyML supports three deployment tiers:

    1. **Local** — Default. Run with `python pipeline.py`
    2. **Docker Compose** — Containerized with `docker-compose up`
    3. **Cloud** — GCP Vertex AI, AWS SageMaker, or Azure ML

    Switch between environments with a single config change:
    ```bash
    export FLOWYML_STACK=production
    python pipeline.py  # Now runs on cloud infrastructure
    ```

    [:octicons-arrow-right-24: Deployment guide →](deployment.md) · [:octicons-arrow-right-24: Production guide →](production_deployment.md)

??? question "Does FlowyML support GPU workloads?"
    Yes. Steps can declare resource requirements including GPU:

    ```python
    @step(outputs=["model"], resources={"gpu": 1, "memory": "16Gi"})
    def train_model(dataset: list) -> Model:
        # GPU-accelerated training
        ...
    ```

    When using cloud orchestrators (Vertex AI, SageMaker), GPU resources are automatically provisioned.

    [:octicons-arrow-right-24: Resource requirements →](core/steps.md)

??? question "Can I use FlowyML in CI/CD pipelines?"
    Absolutely. FlowyML is designed for CI/CD integration:

    - **Evaluation gates**: Use `EvalAssert` to fail builds when model quality degrades
    - **Dry-run mode**: Validate pipeline structure without execution
    - **Scheduling**: Set up recurring pipeline runs with cron expressions

    ```yaml
    # GitHub Actions example
    - name: Run pipeline
      run: flowyml run --stack ci --dry-run
    ```

    [:octicons-arrow-right-24: CI/CD evaluation →](advanced/eval-ci-cd.md)

## Data & Storage

??? question "How do I handle large datasets?"
    FlowyML handles large datasets through:

    - **Streaming materializers** — Process data in chunks without loading everything into memory
    - **Content-hash caching** — Large datasets are only transferred once; subsequent runs use cached versions
    - **Cloud artifact stores** — Store datasets in GCS, S3, or Azure Blob Storage
    - **Map tasks** — Distribute processing across parallel workers

    [:octicons-arrow-right-24: Map tasks →](advanced/map-tasks.md) · [:octicons-arrow-right-24: Materializers →](advanced/materializers.md)

??? question "What storage backends does FlowyML support?"
    | Backend | Type | Use Case |
    |---------|------|----------|
    | Local filesystem | Artifact Store | Development |
    | Google Cloud Storage | Artifact Store | Production (GCP) |
    | Amazon S3 | Artifact Store | Production (AWS) |
    | Azure Blob Storage | Artifact Store | Production (Azure) |
    | SQLite | Metadata Store | Development |
    | PostgreSQL | Metadata Store | Production |
    | MLflow | Experiment Tracker | Experiment logging |
    | W&B | Experiment Tracker | Experiment logging |

    [:octicons-arrow-right-24: Plugins overview →](plugins/overview.md)

## Open Source

??? question "Is FlowyML open source?"
    Yes! FlowyML is fully open source under a permissive license. You can find the source code, contribute, and report issues on GitHub.

    [:octicons-arrow-right-24: GitHub →](https://github.com/UnicoLab/FlowyML) · [:octicons-arrow-right-24: Contributing →](contributing.md)

</div>

---

!!! tip "Still have questions?"
    Check the [Glossary](glossary.md) for terminology, or explore the [Getting Started guide](getting-started.md) for a hands-on introduction.

---

## 🚀 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>

### 🚀 Getting Started
Build your first pipeline in 5 minutes with the quick start tutorial.

[Start Building →](getting-started.md)

</div>

<div class="header-card" markdown>

### 📖 Glossary
Look up FlowyML-specific terms and concepts with linked references.

[Browse Glossary →](glossary.md)

</div>

<div class="header-card" markdown>

### 🤔 Why FlowyML?
Detailed comparison with Airflow, Prefect, ZenML, and Metaflow.

[See Comparison →](why-flowyml.md)

</div>

</div>

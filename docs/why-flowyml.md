---
title: Why FlowyML? — The Case for Artifact-Centric Pipelines
description: Understand why FlowyML takes a fundamentally different approach to ML orchestration and how it compares to Airflow, ZenML, Prefect, and Metaflow.
---

<div class="hero-section" markdown>

## 🤔 Why FlowyML?

Every ML framework promises to make pipelines easy. FlowyML actually delivers — by rethinking the problem from first principles. Here's why teams switch from traditional orchestrators and never look back.

<span class="feature-badge">📦 Artifact-Centric</span>
<span class="feature-badge">⚡ Zero Boilerplate</span>
<span class="feature-badge">☁️ Multi-Cloud</span>
<span class="feature-badge">🤖 GenAI Native</span>

</div>

---

## 🎯 The Problem with Traditional Orchestrators

Most ML orchestrators were born from **data engineering** — they think in terms of **tasks** (verbs). You manually wire steps together, manage data handoff paths, and hope nothing breaks when you switch clouds.

!!! warning "The Traditional Way"
    ```python
    # Airflow / Prefect / Luigi style
    load_task = LoadDataTask()
    train_task = TrainModelTask()
    eval_task = EvaluateTask()

    # Manual wiring — YOU decide the order
    load_task >> train_task >> eval_task

    # Manual data passing — YOU manage paths
    train_task.set_upstream(load_task)
    train_task.params["data_path"] = "s3://bucket/data/train.csv"
    ```

This approach creates three fundamental problems:

1. **Brittle wiring** — Add a step, rewire everything. Remove a step, rewire everything.
2. **Lost lineage** — Data flows through opaque paths. "Which model was trained on which dataset?" becomes a detective game.
3. **Cloud lock-in** — Hardcoded `s3://` paths and cloud-specific APIs everywhere.

---

## 💎 The FlowyML Way: Artifacts First

FlowyML flips the paradigm. Instead of telling the system **how** steps connect, you declare **what** each step produces and consumes. The DAG builds itself.

!!! success "The FlowyML Way"
    ```python
    from flowyml import step, Pipeline, context, Model, Dataset

    @step(outputs=["dataset"])
    def load_data() -> Dataset:
        return Dataset.from_csv("data.csv")

    @step(inputs=["dataset"], outputs=["model"])
    def train(dataset: Dataset, learning_rate: float) -> Model:
        return Model(train_classifier(dataset, lr=learning_rate))

    @step(inputs=["model", "dataset"], outputs=["metrics"])
    def evaluate(model: Model, dataset: Dataset) -> dict:
        return {"accuracy": model.score(dataset)}

    # No arrows. No wiring. Just run.
    pipeline = Pipeline("training", context=context(learning_rate=0.01))
    pipeline.add_step(load_data).add_step(train).add_step(evaluate)
    pipeline.run()
    ```

FlowyML **inferred** that `train` depends on `load_data` (both reference `dataset`) and that `evaluate` depends on both. The DAG is built from data dependencies, not manual arrows.

---

## 📊 FlowyML vs. The Competition

### Feature Comparison

| Capability | Airflow | Prefect | ZenML | Metaflow | **FlowyML** |
|---|:---:|:---:|:---:|:---:|:---:|
| **Core paradigm** | Task DAGs | Task flows | Pipeline/Step | Flow/Step | **Artifact-Centric** |
| **DAG construction** | Manual `>>` | Manual `.submit()` | Manual wiring | Linear `@step` | **Auto-inferred** |
| **Data handoff** | XCom / files | Results | Artifact Store | S3 datastore | **Typed catalog** |
| **Type safety** | None | None | Runtime | None | **Build-time** |
| **Cloud switching** | Rewrite DAGs | Use blocks | Stack swap | `@batch` only | **One env var** |
| **Built-in UI** | Yes | Cloud only | Dashboard | Metadata UI | **Full dashboard** |
| **GenAI observability** | No | No | No | No | **Built-in** |
| **Evaluation framework** | No | No | No | No | **29+ scorers** |
| **Model registry** | No | No | Plugin | No | **Built-in** |
| **LLM cost tracking** | No | No | No | No | **Built-in** |
| **Learning curve** | High (YAML) | Medium | Medium | Low | **Very Low** |
| **License** | Apache 2.0 | Mixed | Apache 2.0 | Apache 2.0 | **Apache 2.0** |

### Philosophy Comparison

<div class="pitch-grid" markdown>

<div class="pitch-card" markdown>
### 🔧 Airflow
Built for **ETL and data engineering**. DAGs defined in Python but execution model is task-centric. Complex scheduler, complex deployment (Kubernetes, Celery). Best for: batch data pipelines at scale.

**Weakness for ML:** No native artifact types, no model registry, no experiment tracking.
</div>

<div class="pitch-card" markdown>
### 🌀 Prefect
Built for **modern data workflows**. Python-native with decorators. Cloud-first with Prefect Cloud. Good DX. Best for: data engineering teams who want a modern Airflow alternative.

**Weakness for ML:** No artifact-centric design, no ML-specific features, cloud lock-in for full features.
</div>

<div class="pitch-card" markdown>
### 🚀 ZenML
Built for **MLOps pipelines**. Stack-based infrastructure abstraction. Closest to FlowyML in philosophy. Best for: teams who want MLOps without vendor lock-in.

**Weakness for ML:** Manual step wiring, no built-in GenAI observability, smaller eval ecosystem.
</div>

</div>

---

## ⚡ What Makes FlowyML Different

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 📦 Artifacts Are First-Class
Models, Datasets, Metrics aren't just files — they're **typed objects** with automatic versioning, lineage tracking, and cloud routing. Define the type, and FlowyML handles storage.
</div>

<div class="header-card" markdown>
### 🔀 DAGs Build Themselves
Declare `inputs` and `outputs` on each step. FlowyML analyzes data dependencies and builds the execution graph. Add or remove steps without rewiring anything.
</div>

<div class="header-card" markdown>
### ☁️ One Env Var to Production
`FLOWYML_STACK=production python pipeline.py` — same code, different infrastructure. Switch from local to GCP Vertex AI to AWS SageMaker with zero code changes.
</div>

<div class="header-card" markdown>
### 🤖 GenAI Native
Built-in LLM tracing, cost tracking, and evaluation for LangGraph, LangChain, OpenAI SDK, or any framework. No LangSmith subscription needed — it's all included.
</div>

<div class="header-card" markdown>
### 🎯 29+ Evaluation Scorers
Classification, regression, and GenAI scorers with CI/CD quality gates. Adapters for DeepEval, RAGAS, and Phoenix. Judge Arena for A/B testing evaluators.
</div>

<div class="header-card" markdown>
### 🖥️ Beautiful Dashboard
Dark-mode web UI with DAG visualization, experiment comparison, model training curves, GenAI trace viewer, and asset browser — all in real-time via WebSocket.
</div>

</div>

---

## 🏁 Ready to Try?

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🚀 5-Minute Quick Start
Build your first pipeline from scratch.

```bash
pip install flowyml
```

[Get Started →](getting-started.md)
</div>

<div class="header-card" markdown>
### 📓 Visual Pipeline Design
Use the reactive notebook companion.

```bash
pip install flowyml-notebook
```

[FlowyML Notebook →](flowyml-notebook.md)
</div>

<div class="header-card" markdown>
### ✨ Explore Features
Deep dive into all 20+ capabilities.

[Features Explorer →](FEATURES.md)
</div>

</div>

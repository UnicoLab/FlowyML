# Welcome to FlowyML 🌊

<p align="center">
  <img src="logo.png" width="350" alt="flowyml Logo"/>
  <br>
  <em>The Enterprise-Grade ML Pipeline Framework for Humans</em>
</p>

---

**FlowyML** is a production-ready ML pipeline orchestration framework that bridges the gap between rapid experimentation and enterprise deployment. Write pipelines as simple Python scripts, then scale them to production without rewriting a single line.

> [!TIP]
> **The promise**: Go from notebook to production in hours, not weeks. FlowyML handles orchestration, caching, versioning, and monitoring — so you can focus on ML, not infrastructure.

## 🎯 Why FlowyML?

### The Problem FlowyML Solves

Most ML teams face the same painful trade-offs:

- **Quick prototyping tools** (notebooks, scripts) don't scale to production
- **Enterprise MLOps platforms** require steep learning curves and complex configuration
- **Orchestration frameworks** force you into rigid patterns or obscure DSLs
- **Experiment tracking** is disconnected from execution and deployment

**FlowyML eliminates these trade-offs.** It's designed for the way data scientists actually work — with pure Python — while providing enterprise-grade capabilities when you need them.

### What Makes FlowyML Different

<div class="grid cards" markdown>

-   :rocket: **Zero Boilerplate**
    ---
    Define steps as pure Python functions. No YAML, no DSLs, no complex wiring. Just `@step` decorators and you're done.

    **Why this matters**: Reduces pipeline development time by 70% compared to traditional frameworks. Your team spends time on ML, not on orchestration syntax.

-   :brain: **Auto-Context Injection**
    ---
    Parameters are automatically injected into steps based on type hints. Change a hyperparameter once, it flows everywhere.

    **Why this matters**: Eliminates configuration management headaches. Run the same pipeline with different configs for dev/staging/prod without code changes.

-   :zap: **Smart Caching**
    ---
    Intelligent caching strategies (code hash, input hash) skip expensive recomputation. Only re-run what actually changed.

    **Why this matters**: Saves compute costs by 40-60% in iterative development. A 3-hour pipeline becomes 20 minutes when you're tweaking one step.

-   :eye: **Real-Time UI**
    ---
    Beautiful, dark-mode dashboard to monitor pipelines, visualize DAGs, and inspect artifacts as they execute.

    **Why this matters**: Debug production issues in minutes instead of hours. See exactly what's happening, when it's happening.

</div>

## 💡 Real-World Impact

Here's what FlowyML delivers in practice:

| Challenge | Without FlowyML | With FlowyML |
|-----------|----------------|--------------|
| **Dev → Production** | 4-8 weeks of rewriting | Hours using same code |
| **Pipeline iteration** | Full re-runs (hours) | Cached steps (minutes) |
| **Debugging failures** | Parse logs, guess state | Visual DAG + artifact inspection |
| **Team collaboration** | Divergent scripts | Standardized, versioned pipelines |
| **Multi-environment** | Rewrite for each | Single pipeline, multiple stacks |
| **Experiment tracking** | Manual logging | Automatic lineage + versioning |

> [!IMPORTANT]
> **Production-Ready from Day One**: FlowyML isn't just for prototypes. It's built for regulated industries, multi-tenant deployments, and enterprise scale. But you can start simple and grow into those features.

## 🚀 Feature Showcase

FlowyML isn't just another orchestrator. It's a complete toolkit for building, debugging, and deploying ML applications.

### 1. Zero-Boilerplate Orchestration
Write pipelines as standard Python functions. No YAML, no DSLs, no complex wiring.

```python
@step(outputs=["data"])
def load():
    return [1, 2, 3]

@step(inputs=["data"], outputs=["model"])
def train(data):
    return Model.train(data)

# It's just Python!
pipeline = Pipeline("simple").add_step(load).add_step(train)
pipeline.run()
```

### 2. 🧠 Intelligent Caching
Don't waste time re-running successful steps. FlowyML's multi-strategy caching understands your code and data.

- **Code Hash**: Re-runs only when you change the code.
- **Input Hash**: Re-runs only when input data changes.
- **Time-based**: Re-runs after a specific duration.

```python
# Only re-runs if 'data' changes, ignoring code changes
@step(cache="input_hash", outputs=["processed"])
def expensive_processing(data):
    return process(data)
```

### 3. 🤖 LLM & GenAI Ready
Built-in tools for the new era of AI. Trace token usage, latency, and costs automatically.

```python
from flowyml import trace_llm

@step
@trace_llm(model="gpt-4", tags=["production"])
def generate_summary(text: str):
    # flowyml automatically tracks tokens, cost, and latency
    return openai.ChatCompletion.create(...)
```

### 4. ⚡ Efficient Step Grouping
Group consecutive steps to run in the same container/executor. Perfect for reducing overhead while maintaining clear step boundaries.

```python
from flowyml.core.resources import ResourceRequirements, GPUConfig

# Group preprocessing steps - they'll share the same container
@step(outputs=["raw"], execution_group="preprocessing",
      resources=ResourceRequirements(cpu="2", memory="4Gi"))
def load_data():
    return fetch_from_source()

@step(inputs=["raw"], outputs=["clean"], execution_group="preprocessing",
      resources=ResourceRequirements(cpu="4", memory="8Gi"))
def clean_data(raw):
    return preprocess(raw)

# FlowyML automatically:
# ✅ Analyzes DAG for consecutive steps
# ✅ Aggregates resources (cpu="4", memory="8Gi")
# ✅ Executes in same environment (no container restart)
```

> [!TIP]
> **Why this matters**: Traditional frameworks (like ZenML) run each step in a separate container, creating unnecessary overhead. FlowyML's intelligent grouping lets you maintain clean step separation while optimizing execution.

### 5. 🔀 Dynamic Workflows
Real-world ML isn't linear. Build complex, adaptive workflows with conditional logic and branching.

```python
from flowyml import If, Switch

# Run 'deploy' only if model accuracy > 0.9
pipeline.add_step(
    If(condition=lambda ctx: ctx["accuracy"] > 0.9)
    .then(deploy_model)
    .else_(notify_team)
)

# Multi-way branching
pipeline.add_step(
    Switch(selector=lambda ctx: ctx["model_type"])
    .case("classification", train_classifier)
    .case("regression", train_regressor)
    .default(train_generic)
)
```

### 6. 🧩 Universal Plugin System
Extend with any tool. Even wrap and reuse ZenML components!

```python
from flowyml.stacks.plugins import load_component

# Load any ZenML orchestrator
k8s_orch = load_component(
    "zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator"
)

# Use ZenML integrations
mlflow_tracker = load_component("zenml:zenml.integrations.mlflow.MLflowExperimentTracker")
great_expectations = load_component("zenml:zenml.integrations.great_expectations.DataValidator")
```

> [!IMPORTANT]
> **Best of Both Worlds**: FlowyML's plugin system gives you access to ZenML's entire ecosystem while maintaining FlowyML's superior developer experience.

### 7. 👤 Human-in-the-Loop
Pause pipelines for manual approval, review, or intervention.

```python
from flowyml import approval

pipeline.add_step(train_model)
pipeline.add_step(
    approval(
        name="approve_deployment",
        approver="ml-team",
        timeout_seconds=3600,
        auto_approve_if=lambda: os.getenv("CI") == "true"
    )
)
pipeline.add_step(deploy_model)
```

### 8. 📊 Built-in Experiment Tracking
No external tools needed. Tracking is built-in and automatic.

```python
from flowyml.tracking import Experiment

exp = Experiment(
    name="baseline_training",
    description="Baseline model experiments",
    tags={"framework": "pytorch", "version": "v1"}
)

exp.log_run(
    run_id="run_001",
    metrics={"accuracy": 0.95, "loss": 0.12},
    parameters={"lr": 0.01, "batch_size": 32}
)

# Get best performing run
best = exp.get_best_run("accuracy", maximize=True)
```

### 9. 🏆 Model Leaderboard & Registry
Track, compare, version, and stage your models.

```python
from flowyml import ModelLeaderboard
from flowyml.core import Model

# Leaderboard for model comparison
leaderboard = ModelLeaderboard(metric="accuracy", higher_is_better=True)
leaderboard.add_score(model_name="bert-base", run_id="run_123", score=0.92)
leaderboard.display()  # Beautiful console output

# Model registry with stages
model = Model.create(artifact=trained_model, score=0.95)
model.register(name="text_classifier", stage="production", version="v1.2.0")
```

### 10. 📅 Built-in Scheduling
Schedule recurring jobs without external orchestrators.

```python
from flowyml import PipelineScheduler

scheduler = PipelineScheduler()

# Daily at 2 AM
scheduler.schedule_daily(
    name="daily_training",
    pipeline_func=lambda: pipeline.run(),
    hour=2, minute=0
)

# Every 6 hours
scheduler.schedule_interval(
    name="data_refresh",
    pipeline_func=lambda: refresh_pipeline.run(),
    hours=6
)

scheduler.start()  # Non-blocking
```

### 11. 🔔 Smart Notifications
Slack, Email, and custom alerts. All built-in.

```python
from flowyml import configure_notifications, get_notifier

configure_notifications(
    console=True,
    slack_webhook="https://hooks.slack.com/services/YOUR/WEBHOOK",
    email_config={...}
)

# Automatic notifications
# - Pipeline start/success/failure
# - Data drift detection
# - Manual triggers available

notifier = get_notifier()
notifier.notify("Model deployed!", level="success")
```

### 12. 🎯 Interactive Debugging
Set breakpoints, inspect state, and debug like regular Python code.

```python
from flowyml import StepDebugger

debugger = StepDebugger()
debugger.set_breakpoint("train_model")

# Run with debugging enabled
pipeline.run(debug=True)

# When breakpoint hits:
# - Inspect variables
# - Check intermediate outputs
# - Step through execution
```

### 13. 📦 First-Class Asset Types
Specialized types for ML workflows. Not just generic files.

```python
from flowyml.core import Dataset, Model, Metrics, FeatureSet

# Type-safe ML assets with metadata
dataset = Dataset.create(
    data=df,
    name="training_data",
    metadata={"source": "postgres", "rows": 10000}
)

model = Model.create(
    artifact=trained_model,
    score=0.95,
    metadata={"framework": "pytorch", "params": {...}}
)

metrics = Metrics.create(values={"accuracy": 0.95, "f1": 0.93})
```

### 14. 🔄 Smart Retries & Circuit Breakers
Handle failures gracefully. Production-ready from day one.

```python
# Automatic retries
@step(retry=3, timeout=300)
def flaky_api_call():
    return external_api.fetch()

# Circuit breakers prevent cascading failures
# Automatically stops calling failing dependencies
```

### 15. 📈 Data Drift Detection
Monitor distribution shifts. Trigger retraining automatically.

```python
from flowyml import detect_drift

drift_result = detect_drift(
    reference_data=train_feature,
    current_data=prod_feature,
    threshold=0.1  # PSI threshold
)

if drift_result['drift_detected']:
    print(f"⚠️ Drift detected! PSI: {drift_result['psi']:.4f}")
    trigger_retraining()
```

### 16. 🌐 Pipeline Versioning
Git-like versioning for pipelines. Track changes, compare, rollback.

```python
from flowyml import VersionedPipeline

pipeline = VersionedPipeline("training", version="v1.0.0")
pipeline.add_step(load_data)
pipeline.add_step(train_model)
pipeline.save_version()

# Make changes
pipeline.add_step(evaluate)
pipeline.version = "v1.1.0"
pipeline.save_version()

# Compare versions
diff = pipeline.compare_with("v1.0.0")
```

### 17. 🏭 Enterprise Production Features
Everything you need to run mission-critical workloads.

- **🔄 Automatic Retries**: Handle transient failures gracefully.
- **⏰ Scheduling**: Built-in cron scheduler for recurring jobs.
- **🔔 Notifications**: Slack/Email alerts on success or failure.
- **🛡️ Circuit Breakers**: Stop cascading failures automatically.

### 18. 🔌 Universal Integrations
Works with your existing stack.

- **ML Frameworks**: PyTorch, TensorFlow, Keras, Scikit-learn, HuggingFace.
- **Cloud Providers**: AWS, GCP, Azure (via plugins).
- **Tools**: MLflow, Weights & Biases, Great Expectations.

## ⚡️ Quick Start

See how simple it is — this is a complete, runnable ML pipeline:

```python
from flowyml import Pipeline, step, context

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

That's it. No YAML. No config files. No boilerplate. Just Python.

## 🚀 Ready to Build Better Pipelines?

<div class="grid cards" markdown>

-   :rocket: **[Getting Started](getting-started.md)**
    ---
    Build your first pipeline in 5 minutes. No prior MLOps experience required.

-   :book: **[Core Concepts](core/pipelines.md)**
    ---
    Understand pipelines, steps, context, and assets — the building blocks of FlowyML.

-   :zap: **[Advanced Features](advanced/caching.md)**
    ---
    Deep dive into caching, parallelism, debugging, and production patterns.

-   :chart_with_upwards_trend: **[User Guide](user-guide/projects.md)**
    ---
    Master projects, versioning, scheduling, and multi-tenant deployments.

-   :plug: **[Integrations](integrations/keras.md)**
    ---
    Connect with Keras, GCP, and your existing ML stack.

-   :hammer_and_wrench: **[API Reference](api/core.md)**
    ---
    Complete API documentation for every class and function.

</div>

---

**Questions? Issues?** [Open an issue on GitHub](https://github.com/UnicoLab/FlowyML/issues) or check out the [Resources](resources.md) page for community links.

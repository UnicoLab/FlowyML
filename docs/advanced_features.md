# ⚡ Advanced Features — Feature Encyclopedia

FlowyML isn't just for building DAGs; it's an enterprise-grade platform designed to handle the complexities of production machine learning. This guide is your gateway to every advanced capability.

<div class="hero-section" markdown>

## 🗺️ Master Every Feature

From intelligent caching to GenAI observability — these are the features that set FlowyML apart from every other ML framework.

</div>

---

## 📚 Feature Index

<div class="header-grid" markdown>

<div class="header-card" markdown>
### ⚡ Execution & Performance
- **[Step Grouping](#-step-grouping)** — Co-locate steps in one container
- **[Caching](advanced/caching.md)** — Skip redundant compute
- **[Parallel Execution](advanced/parallel.md)** — Run steps concurrently
- **[Map Tasks](advanced/map-tasks.md)** — Fan-out processing
</div>

<div class="header-card" markdown>
### 🧠 Intelligence & AI
- **[GenAI Observability](#-genai--llm-observability)** — LLM tracing & costing
- **[Evaluations](evaluations.md)** — 17+ built-in scorers
- **[Judge Arena](advanced/eval-arena.md)** — A/B test evaluators
- **[Dynamic Workflows](#-dynamic-sub-pipelines)** — Runtime DAG generation
</div>

<div class="header-card" markdown>
### 🛡️ Reliability & Ops
- **[Checkpointing](#-checkpointing)** — Resume from failures
- **[Error Handling](advanced/error-handling.md)** — Retries & circuit breakers
- **[Notifications](#-notification-hub)** — Slack, Email, Custom
- **[Drift Detection](#-data-drift-monitoring)** — Statistical monitors
</div>

</div>

---

## ⚡ Step Grouping

**Step Grouping** allows you to run multiple consecutive steps in the same execution environment (container/process). This is critical for optimizing performance when you have many small steps.

!!! tip "🎯 When to use"
    Use grouping for small, sequential tasks (clean → transform → validate) that don't need separate containers. Skip it for heavy compute steps that benefit from isolated resources.

```python linenums="1"
from flowyml import step

# These three steps will execute in ONE container
@step(outputs=["raw"], execution_group="prep")
def load(): ...

@step(inputs=["raw"], outputs=["clean"], execution_group="prep")
def clean(raw): ...

@step(inputs=["clean"], outputs=["stats"], execution_group="prep")
def analyze(clean): ...
```

!!! info "📊 Resource Aggregation"
    FlowyML intelligently calculates the resources needed for a group by taking the **Maximum** of all participants. If Step A needs 1 GPU and Step B needs 2 GPUs, the entire group will provision 2 GPUs.

→ **Deep Dive**: [Step Grouping Guide](advanced/step-grouping.md)

---

## 🕵️ GenAI & LLM Observability

FlowyML provides deep tracing for LLM applications. Unlike generic loggers, we understand the structure of GenAI chains.

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🔍 Waterfall View
See nested calls (Chain → Retrieval → LLM) with per-step token counts and timing.
</div>

<div class="header-card" markdown>
### 💰 Auto-Costing
Automatic cost calculation for OpenAI, Anthropic, Cohere, and LlamaIndex models.
</div>

<div class="header-card" markdown>
### 🔗 Trace-to-Eval
Bridge production traces directly into an [Evaluation Dataset](evaluations.md) for offline scoring.
</div>

</div>

```python linenums="1"
from flowyml import trace_llm

@trace_llm(name="qa_system", model="gpt-4o")
def ask(question: str):
    # This entire execution, including tokens and cost,
    # is tracked and visible in the FlowyML Dashboard.
    return llm.invoke(question)
```

→ **Deep Dive**: [LLM Tracing Guide](advanced/llm-tracing.md) · [Eval Adapters](advanced/eval-adapters.md)

---

## 👤 Human-in-the-Loop

Some actions shouldn't be fully automated. FlowyML provides **Approval Gates** that pause pipeline execution and notify your team.

```python linenums="1"
from flowyml import Pipeline, approval

pipeline = Pipeline("deploy-to-prod")
pipeline.add_step(train_model)

# The pipeline will PAUSE here and notify the team
pipeline.add_step(
    approval(
        name="release_gate",
        approver="senior-ds@company.com",
        timeout_seconds=3600
    )
)

pipeline.add_step(deploy_trigger)
```

!!! warning "⏱️ Timeout Behavior"
    If no approval is received within `timeout_seconds`, the pipeline will fail safely. Set this based on your team's SLA.

→ **Deep Dive**: [Human-in-the-Loop Guide](advanced/human-in-the-loop.md)

---

## 💾 Checkpointing

ML training is expensive and prone to transient failures (preemptible instances, OOM, network). FlowyML **Checkpoints** ensure you never lose progress.

- **🔄 Automatic State Saving**: Every artifact is saved to the `ArtifactStore`
- **⚡ Intelligent Resumption**: Use `pipeline.rerun(run_id="...")` to skip the 10-hour processing and jump straight to the training step that failed
- **🔒 Immutable Snapshots**: Pipeline snapshots guarantee reproducibility

```python linenums="1"
# Resume from failure — skips all completed steps
result = pipeline.rerun(run_id="previous_failed_run")

# Resume from a specific step
result = pipeline.rerun(run_id="abc-123", from_step="train_model")
```

→ **Deep Dive**: [Checkpointing & Experiment Tracking Guide](advanced/checkpointing.md)

---

## 📊 Data Drift Monitoring

FlowyML includes high-performance statistical utilities to monitor your data distribution and detect model degradation before it reaches production.

```python linenums="1"
from flowyml.monitoring import detect_drift

# Compare current production batch vs. historical training baseline
drift = detect_drift(
    reference_data=baseline_df['age'],
    current_data=production_df['age'],
    threshold=0.1
)

if drift['drift_detected']:
    # Automatically triggers a Slack alert via flowyml Notification System
    send_alert(f"Drift detected in 'age' (PSI: {drift['psi']})")
```

→ **Deep Dive**: [Data Drift Guide](advanced/data-drift.md)

---

## 🔔 Notification Hub

Connect your pipelines to the tools your team uses. Configure once — all pipelines inherit the channels.

```python linenums="1"
from flowyml import configure_notifications

configure_notifications(
    slack_webhook="https://hooks.slack.com/...",
    email_config={...},
    console=True
)

# Steps will automatically report start/success/failure to these channels
```

| Channel | Setup | Best For |
|---------|-------|----------|
| 🖥️ Console | Always enabled | Development & debugging |
| 💬 Slack | `slack_webhook` URL | Real-time team alerts |
| 📧 Email | `email_config` dict | Daily summaries & reports |
| 🔧 Custom | Your subclass | Discord, PagerDuty, Teams |

→ **Deep Dive**: [Notifications & Alerts Guide](advanced/notifications.md)

---

## 📅 Scheduling & Automation

Run your pipelines on a schedule without needing a separate cron job or Airflow instance.

```python linenums="1"
from flowyml import PipelineScheduler

scheduler = PipelineScheduler()
scheduler.schedule_daily(
    "model_refresh",
    lambda: my_pipeline.run(),
    hour=3
)
scheduler.start()
```

→ **Deep Dive**: [Scheduling Guide](user-guide/scheduling.md)

---

## 🏆 Model Leaderboard & Comparisons

Keep track of your best experiments with an automatic leaderboard.

```python linenums="1"
from flowyml import ModelLeaderboard

board = ModelLeaderboard(metric="val_accuracy", higher_is_better=True)
board.add_score("res-net-50", run_id="r1", score=0.94)
board.add_score("vit-base", run_id="r2", score=0.96)

# Prints a beautiful CLI table or renders in the Dashboard
board.display()
```

→ **Deep Dive**: [Model Leaderboard Guide](advanced/model-leaderboard.md)

---

## 🧠 Dynamic Sub-Pipelines

For advanced users, FlowyML allows you to generate entire pipelines *at runtime*. This is perfect for Hyperparameter Search or Cross-Validation.

```python linenums="1"
from flowyml import dynamic, Pipeline, step

@dynamic(outputs=["best_model"])
def hp_search(lrs: list):
    sub = Pipeline("sweep")
    for lr in lrs:
        @step(outputs=[f"model_{lr}"])
        def train(): return train_with_lr(lr)
        sub.add_step(train)
    return sub
```

→ **Deep Dive**: [Dynamic Workflows Guide](advanced/dynamic-workflows.md) · [Sub-Pipelines Guide](advanced/subpipelines.md)

---

## 📐 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🚀 Deploy
Learn how to deploy your pipelines as REST APIs in the **[Deployment Lab](user-guide/deployments.md)**.
</div>

<div class="header-card" markdown>
### 🔌 Extend
Explore the **[Plugin API](api/plugins.md)** to build your own custom integrations.
</div>

<div class="header-card" markdown>
### 💻 Examples
Browse the **[Examples Gallery](examples.md)** for production-ready pipeline templates.
</div>

</div>

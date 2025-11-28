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

## 🚀 Feature Showcase

UniFlow is a complete toolkit for building, debugging, and deploying ML applications.

### 1. Zero-Boilerplate Orchestration
Write pipelines as standard Python functions. No YAML, no DSLs.

```python
@step(outputs=["data"])
def load(): return [1, 2, 3]

@step(inputs=["data"], outputs=["model"])
def train(data): return Model.train(data)

# It's just Python!
pipeline = Pipeline("simple").add_step(load).add_step(train)
pipeline.run()
```

### 2. 🧠 Intelligent Caching
Don't waste time re-running successful steps.
- **Code Hash**: Re-runs only when code changes.
- **Input Hash**: Re-runs only when data changes.

```python
# Only re-runs if 'data' changes, ignoring code changes
@step(cache="input_hash", outputs=["processed"])
def expensive_processing(data):
    return process(data)
```

### 3. 🤖 LLM & GenAI Ready
Trace token usage, latency, and costs automatically.

```python
@step
@trace_llm(model="gpt-4", tags=["production"])
def generate_summary(text: str):
    # UniFlow automatically tracks tokens, cost, and latency
    return openai.ChatCompletion.create(...)
```

### 4. ⚡ Efficient Step Grouping
Group related steps to run in the same container - reduce overhead, maintain clarity.

```python
# Run preprocessing steps in same container (shares resources)
@step(outputs=["raw"], execution_group="preprocessing")
def load(): return fetch_data()

@step(inputs=["raw"], outputs=["clean"], execution_group="preprocessing")
def clean(raw): return preprocess(raw)

# UniFlow automatically aggregates resources (max CPU, memory, best GPU)
# and executes consecutively in same environment
```

### 5. 🔀 Dynamic Workflows
Build adaptive workflows with conditional logic.

```python
# Run 'deploy' only if model accuracy > 0.9
pipeline.add_step(
    If(condition=lambda ctx: ctx["accuracy"] > 0.9)
    .then(deploy_model)
    .else_(notify_team)
)
```

### 6. 🧩 Universal Plugin System
Extend UniFlow with any tool - even wrap ZenML components!

```python
from uniflow.stacks.plugins import load_component

# Use any ZenML orchestrator, artifact store, or integration
k8s_orch = load_component("zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator")
mlflow = load_component("zenml:zenml.integrations.mlflow.MLflowExperimentTracker")
```

### 7. 👤 Human-in-the-Loop
Pause pipelines for manual approval or review.

```python
from uniflow import approval

approval_step = approval(
    name="approve_deployment",
    approver="ml-team",
    timeout_seconds=3600
)
```

### 8. 📊 Built-in Experiment Tracking
No external tools needed - tracking is built-in.

```python
from uniflow.tracking import Experiment

exp = Experiment("baseline_training")
exp.log_run(run_id="run_001", metrics={"accuracy": 0.95}, parameters={"lr": 0.01})
best = exp.get_best_run("accuracy", maximize=True)
```

### 9. 🏆 Model Leaderboard & Registry
Track, compare, and version your models.

```python
from uniflow import ModelLeaderboard
from uniflow.core import Model

# Track performance
leaderboard = ModelLeaderboard(metric="accuracy")
leaderboard.add_score(model_name="bert-base", score=0.92)

# Register models with stages
model = Model.create(artifact={...})
model.register(name="text_classifier", stage="production")
```

### 10. 📅 Built-in Scheduling
Schedule recurring jobs without external orchestrators.

```python
from uniflow import PipelineScheduler

scheduler = PipelineScheduler()
scheduler.schedule_daily(
    name="daily_training",
    pipeline_func=lambda: pipeline.run(),
    hour=2, minute=0
)
scheduler.start()
```

### 11. 🔔 Smart Notifications
Slack, Email, and custom alerts built-in.

```python
from uniflow import configure_notifications

configure_notifications(
    slack_webhook="https://hooks.slack.com/...",
    email_config={...}
)
# Automatic notifications on pipeline success/failure
```

### 12. 🎯 Step-Level Debugging
Set breakpoints and inspect state mid-pipeline.

```python
from uniflow import StepDebugger

debugger = StepDebugger()
debugger.set_breakpoint("train_model")
pipeline.run(debug=True)  # Pauses at breakpoint
```

### 13. 📦 First-Class Assets
Specialized types for ML workflows.

```python
from uniflow.core import Dataset, Model, Metrics, FeatureSet

dataset = Dataset.create(data=df, name="training_data")
model = Model.create(artifact=trained_model, score=0.95)
metrics = Metrics.create(values={"accuracy": 0.95})
```

### 14. 🔄 Smart Retries & Circuit Breakers
Handle failures gracefully.

```python
@step(retry=3, timeout=300)
def flaky_api_call():
    return external_api.fetch()

# Circuit breakers prevent cascading failures
```

### 15. 📈 Data Drift Detection
Monitor distribution shifts automatically.

```python
from uniflow import detect_drift

drift = detect_drift(
    reference_data=train_feature,
    current_data=prod_feature,
    threshold=0.1
)
if drift['drift_detected']:
    trigger_retraining()
```

### 16. 🔍 Interactive Debugging
- **StepDebugger**: Set breakpoints in your pipeline.
- **Artifact Inspection**: View intermediate data in the UI.
- **Local Execution**: Run the exact same code locally as in production.

### 17. 🏭 Enterprise Production Features
- **🔄 Automatic Retries**: Handle transient failures.
- **⏰ Scheduling**: Built-in cron scheduler.
- **🔔 Notifications**: Slack/Email alerts.
- **🛡️ Circuit Breakers**: Stop cascading failures.

### 18. 🔌 Universal Integrations
- **ML Frameworks**: PyTorch, TensorFlow, Keras, Scikit-learn, HuggingFace.
- **Cloud Providers**: AWS, GCP, Azure (via plugins).
- **Tools**: MLflow, Weights & Biases, Great Expectations.

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

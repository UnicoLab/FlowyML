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

**FlowyML** is the comprehensive ML pipeline framework that combines the **simplicity of a Python script** with the **power of an enterprise MLOps platform**.

## 🚀 Why FlowyML?

| Feature | FlowyML | Traditional Orchestrators |
|---------|---------|---------------------------|
| **Developer Experience** | 🐍 **Native Python** - No DSLs, no YAML hell. | 📜 Complex YAML or rigid DSLs. |
| **Context Awareness** | 🧠 **Auto-Injection** - Params are just function args. | 🔌 Manual wiring of every parameter. |
| **Caching** | ⚡ **Multi-Level** - Smart content-hashing & memoization. | 🐢 Basic file-timestamp checking. |
| **Asset Management** | 📦 **First-Class Assets** - Models & Datasets with lineage. | 📁 Generic file paths only. |
| **Architecture** | 🏗️ **Modular Stacks** - Local, Cloud, Hybrid. | 🔒 Vendor lock-in or complex setup. |
| **Deployment** | 🏢 **Local or Centralized** - Run locally or deploy as a company-wide hub. | 🧩 Fragmented or cloud-only. |
| **Flexibility** | 🔌 **Extensive Plugin Ecosystem** | Fixed integration with specific orchestrators or custom tools to be developed. |
| **Separation of Concerns** | 🪾 **Steps Grouping, branching and conditions** | Handling only orchestrator logic and task execution oriented. |
| **Features Rich** | 🌟 **Built-in experiment tracking, model leaderboard, human-in-the-loop, notifications, scheduling** | Very limited or none extra features. |

## 🚀 Feature Showcase

FlowyML is a complete toolkit for building, debugging, and deploying ML applications.

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
Trace token usage, latency, and costs automatically with built-in observability.

```python
@step
@trace_llm(model="gpt-4", tags=["production"])
def generate_summary(text: str):
    # flowyml automatically tracks:
    # - Token usage (prompt/completion)
    # - Cost estimation
    # - Latency & Success/Failure rates
    return openai.ChatCompletion.create(...)
```

### 4. ⚡ Efficient Step Grouping & Separation of Concerns
Group related steps to run in the same container - reduce overhead, maintain clarity, and keep logic separate from configuration.

```python
# Run preprocessing steps in same container (shares resources)
@step(outputs=["raw"], execution_group="preprocessing")
def load(): return fetch_data()

@step(inputs=["raw"], outputs=["clean"], execution_group="preprocessing")
def clean(raw): return preprocess(raw)

# flowyml automatically aggregates resources (max CPU, memory, best GPU)
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
Extend flowyml with any tool - even wrap ZenML components!

```python
from flowyml.stacks.plugins import load_component

# Use any ZenML orchestrator, artifact store, or integration
k8s_orch = load_component("zenml:zenml.integrations.kubernetes.orchestrators.KubernetesOrchestrator")
mlflow = load_component("zenml:zenml.integrations.mlflow.MLflowExperimentTracker")
```

### 7. 👤 Human-in-the-Loop
Pause pipelines for manual approval or review.

```python
from flowyml import approval

approval_step = approval(
    name="approve_deployment",
    approver="ml-team",
    timeout_seconds=3600
)
```

### 8. 📊 Built-in Experiment Tracking
No external tools needed - tracking is built-in.

```python
from flowyml.tracking import Experiment

exp = Experiment("baseline_training")
exp.log_run(run_id="run_001", metrics={"accuracy": 0.95}, parameters={"lr": 0.01})
best = exp.get_best_run("accuracy", maximize=True)
```

### 9. 🏆 Model Leaderboard & Registry
Track, compare, and version your models.

```python
from flowyml import ModelLeaderboard
from flowyml.core import Model

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
from flowyml import PipelineScheduler

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
from flowyml import configure_notifications

configure_notifications(
    slack_webhook="https://hooks.slack.com/...",
    email_config={...}
)
# Automatic notifications on pipeline success/failure
```

### 12. 🎯 Step-Level Debugging
Set breakpoints and inspect state mid-pipeline.

```python
from flowyml import StepDebugger

debugger = StepDebugger()
debugger.set_breakpoint("train_model")
pipeline.run(debug=True)  # Pauses at breakpoint
```

### 13. 📦 First-Class Assets
Assets are not just files; they are first-class citizens with lineage, metadata, and versioning.

```python
from flowyml import Dataset, Model, Metrics, FeatureSet

# Assets track their producer, lineage, and metadata automatically
dataset = Dataset.create(data=df, name="training_data", metadata={"source": "s3"})
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
from flowyml import detect_drift

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

### 18. 🏢 Centralized Hub & Docker
Ready for the enterprise. Run locally per project or deploy as a centralized entity for the company.
- **Docker Ready**: Backend and Frontend are fully dockerized with optimized multi-stage builds.
- **Centralized Hub**: Share pipelines, artifacts, and experiments across the team.
- **Remote Execution**: Configure local clients to execute on the remote hub.

## 🐳 Local Stack Setup (Docker)

Get the complete FlowyML stack running locally in minutes with Docker.

### Prerequisites

- Docker v24.0+ and Docker Compose v2.20+
- 4GB RAM minimum (8GB recommended)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/UnicoLab/FlowyML.git
cd FlowyML

# Start the complete stack
make local-deploy

# Check health of all services
make local-health
```

### Access Services

| Service          | URL                          | Credentials     |
|------------------|------------------------------|-----------------|
| **Frontend UI**  | http://localhost:80          | -               |
| **Backend API**  | http://localhost:8080        | -               |
| **API Docs**     | http://localhost:8080/docs   | -               |
| **Prometheus**   | http://localhost:9090        | -               |
| **Grafana**      | http://localhost:3001        | admin / admin   |

### Common Commands

```bash
# Start the stack
make local-deploy

# Stop the stack
make local-stop

# View logs
make docker-logs

# Rebuild images (after code changes)
make docker-build

# Clean rebuild (no cache)
make docker-build-clean

# Check service health
make local-health
```

For detailed setup instructions, troubleshooting, and configuration options, see the [Local Stack Setup Guide](docs/local-stack-setup.md).

### 19. 🔌 Universal Integrations
- **ML Frameworks**: PyTorch, TensorFlow, Keras, Scikit-learn, HuggingFace.
- **Cloud Providers**: AWS, GCP, Azure (via plugins).
- **Tools**: MLflow, Weights & Biases, Great Expectations.

### 20. 📊 Automatic Training History Tracking
FlowyML automatically captures and visualizes your model training progress with zero manual intervention.

```python
from flowyml.integrations.keras import FlowymlKerasCallback

# Just add the callback - that's it!
callback = FlowymlKerasCallback(
    experiment_name="my-experiment",
    project="my-project"
)

model.fit(
    x_train, y_train,
    validation_data=(x_val, y_val),
    epochs=50,
    callbacks=[callback]  # Auto-tracks all metrics!
)
```

**What gets captured automatically:**
- ✅ Loss (train & validation) per epoch
- ✅ Accuracy (train & validation) per epoch
- ✅ All custom metrics (F1, precision, recall, etc.)
- ✅ Model architecture and parameters
- ✅ Interactive charts in the UI

**View beautiful training graphs in the UI:**
1. Navigate to your project's Structure tab
2. Click on any model artifact
3. See interactive loss/accuracy charts over epochs!

No external tools needed - all visualization built into FlowyML.

### 21. 📂 Project-Based Organization
Built-in multi-tenancy for managing multiple teams and initiatives.

```python
from flowyml import Project

project = Project("recommendation_system")
pipeline = project.create_pipeline("training")

# All runs, artifacts, and metadata are automatically scoped to the project
runs = project.list_runs()
stats = project.get_stats()
```

### 22. 📝 Pipeline Templates
Stop reinventing the wheel. Use pre-built templates for common ML patterns.

```python
from flowyml.core.templates import create_from_template

# Create a standard training pipeline in one line
pipeline = create_from_template(
    "ml_training",
    data_loader=my_loader,
    trainer=my_trainer,
    evaluator=my_evaluator
)
```

## 📦 Installation

```bash
# Install core
pip install flowyml

# Install with UI support
pip install "flowyml[ui]"

# Install with all features (recommended for dev)
pip install "flowyml[all]"
```

## ⚡ Quick Start

```python
from flowyml import Pipeline, step, context, Dataset, Model

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

### 23. 🌐 Pipeline Versioning
Git-like versioning for pipelines. Track changes, compare, rollback.

```python
from flowyml import VersionedPipeline

pipeline = VersionedPipeline("training", version="v1.0.0")
pipeline.add_step(load_data)
pipeline.save_version()

# ... make changes ...
pipeline.version = "v1.1.0"
pipeline.save_version()

# Compare versions to see exactly what changed (steps, code, context)
diff = pipeline.compare_with("v1.0.0")
print(diff["modified_steps"])  # ['train_model']
print(diff["context_changes"]) # {'learning_rate': {'old': 0.01, 'new': 0.001}}
```

## 🖥️ The flowyml UI

Visualize your workflows, inspect artifacts, and monitor runs in real-time.

```bash
# Start the UI server
flowyml ui start --open-browser
```

Visit **http://localhost:8080** to access the dashboard.

## 📚 Documentation

- **[Getting Started](docs/getting-started.md)**: Your first 5 minutes with flowyml.
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

---
title: Features Explorer — Everything FlowyML Can Do
description: A comprehensive guide to all FlowyML features including GenAI observability, evaluations, scheduling, drift detection, templates, and more.
---

<div class="hero-section" markdown>

## 🌊 FlowyML Features Explorer

Discover everything FlowyML can do — from GenAI observability and LLM evaluation to pipeline scheduling, data drift detection, and beyond. Each feature is production-ready and batteries-included.

<span class="feature-badge">🤖 GenAI</span>
<span class="feature-badge">📊 Evaluations</span>
<span class="feature-badge">⏰ Scheduling</span>
<span class="feature-badge">📉 Drift Detection</span>
<span class="feature-badge">🔀 Dynamic Workflows</span>
<span class="feature-badge">📦 Artifact Catalog</span>

</div>

## New Features Overview

### 1️⃣ **GenAI & LLM Monitoring**

Track LLM calls, tokens, and costs automatically:

```python
from flowyml import trace_llm

@trace_llm(name="summarize")
def generate_summary(text):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Summarize: {text}"}]
    )
    return response.choices[0].message.content

# Traces are automatically saved
result = generate_summary("Long text here...")
```

**Features:**
- Automatic input/output capture
- Token usage tracking
- Cost calculation
- Parent-child trace relationships
- View traces in UI at `/api/traces`

---

### 1️⃣.5 🔗 **GenAI Observability** ⚡ NEW

Full-stack GenAI observability for **any AI framework** — LangGraph, LangChain, OpenAI SDK, CrewAI, AutoGen, or custom code. Track every LLM call, tool invocation, chain execution, RAG pipeline, tokens, costs, artifacts, and errors with a single import.

**4 Supported Frameworks:**

```python
# LangGraph — @observe() decorator, zero-config
from flowyml import observe
@observe(name="my_agent", project="chatbot")
def handle_query(query, flowyml_session=None):
    return graph.invoke(input, config=flowyml_session.config)

# LangChain — trace_chain() for chains/runnables
from flowyml.integrations.langchain import trace_chain
with trace_chain("qa_chain") as session:
    result = chain.invoke(input, config=session.config)

# OpenAI SDK — drop-in replacement, no LangChain needed
from flowyml import TracedOpenAI
client = TracedOpenAI(project="my_app")
response = client.chat.completions.create(model="gpt-4o-mini", messages=[...])

# Any Framework — universal adapter
from flowyml import log_llm_call
log_llm_call(model="gpt-4o", prompt="Hello", response="Hi!", prompt_tokens=5, completion_tokens=2)
```

**What Gets Tracked Automatically:**
- 🤖 Every LLM call (model, prompts, responses — saved as first-class artifacts)
- 🔧 Every tool invocation (input, output, duration)
- 🔗 Chain/graph node execution with parent-child hierarchy
- 📚 RAG pipeline: retriever queries + retrieved documents as artifacts
- 📊 Token usage (prompt + completion + total per call and session)
- 💰 Cost estimation (OpenAI, Anthropic, Google, Mistral, Cohere models)
- ⏱  Latency per step and total session duration
- 📦 Artifacts: prompts, responses, documents, configs — all first-class citizens
- 🎨 Canvas-ready DAG: full trace tree for FlowyML canvas visualization
- ❌ Error tracking with full context
- 🏷  Model identification, tagging, and multi-model sessions
- 🔍 View everything in FlowyML UI at `/api/traces`

---

### 2️⃣ **Keras Integration**

Automatic experiment tracking for Keras models:

```python
from flowyml import flowymlKerasCallback

model.fit(
    x_train, y_train,
    epochs=10,
    callbacks=[
        flowymlKerasCallback(
            experiment_name="mnist_training",
            run_name="baseline_v1",
            log_model=True
        )
    ]
)
```

**Auto-logs:**
- Training metrics (loss, accuracy, etc.)
- Model architecture & summary
- Optimizer configuration
- Training parameters
- Model checkpoints

---

### 3️⃣ **Data Drift Detection**

Monitor data distribution shifts:

```python
from flowyml import detect_drift, compute_stats

# Detect drift
drift_result = detect_drift(
    reference_data=train_data['feature'],
    current_data=prod_data['feature'],
    threshold=0.1  # PSI threshold
)

if drift_result['drift_detected']:
    print(f"⚠️ Drift detected! PSI: {drift_result['psi']:.4f}")

# Compute stats
stats = compute_stats(data)
print(f"Mean: {stats['mean']}, Std: {stats['std']}")
```

---

### 3️⃣.5 **ZenML Auto-Integration** ⚡NEW

Import the entire ZenML ecosystem with one line:

```python
from flowyml.stacks import import_all_zenml

# Import all ZenML components at once
components = import_all_zenml()
# Done! All ZenML orchestrators, artifact stores, etc. are ready
```

**CLI commands:**

```bash
# Check ZenML status
flowyml zenml status

# List and install integrations
flowyml zenml list
flowyml zenml install mlflow
flowyml zenml install kubernetes

# Import all at once
flowyml zenml import-all
```

**Features:**
- Automatic discovery of ZenML integrations
- Zero configuration wrapping of components
- Full CLI for installation and import
- Works with 50+ ZenML integrations

---

### 4️⃣ **Pipeline Scheduling**

Run pipelines automatically on a schedule:

```python
from flowyml import PipelineScheduler

scheduler = PipelineScheduler()

# Daily at 2am
scheduler.schedule_daily(
    name="daily_training",
    pipeline_func=lambda: my_pipeline.run(),
    hour=2, minute=0
)

# Every 6 hours
scheduler.schedule_interval(
    name="data_refresh",
    pipeline_func=lambda: refresh_pipeline.run(),
    hours=6
)

# Start scheduler
scheduler.start()  # Non-blocking
# scheduler.start(blocking=True)  # Blocking
```

---

### 5️⃣ **Notifications**

Get notified about pipeline events:

```python
from flowyml import configure_notifications, get_notifier

# Configure channels
configure_notifications(
    console=True,
    slack_webhook="https://hooks.slack.com/...",
    email_config={
        'smtp_host': 'smtp.gmail.com',
        'username': 'you@gmail.com',
        'password': 'your-password',
        'from_addr': 'you@gmail.com',
        'to_addrs': ['team@company.com']
    }
)

# Use in your code
notifier = get_notifier()
notifier.notify(
    title="Training Complete",
    message="Model achieved 95% accuracy",
    level="success"
)

# Or use event hooks
notifier.on_pipeline_success(pipeline.name, run_id, duration)
notifier.on_pipeline_failure(pipeline.name, run_id, error)
notifier.on_drift_detected(feature_name, psi_value)
```

---

### 6️⃣ **Model Leaderboard**

Compare and rank models:

```python
from flowyml import ModelLeaderboard

leaderboard = ModelLeaderboard(
    metric="accuracy",
    higher_is_better=True
)

# Add scores
leaderboard.add_score("bert-base", run_id="run_123", score=0.92)
leaderboard.add_score("distilbert", run_id="run_124", score=0.89)

# Display rankings
leaderboard.display(n=10)

# Get top models
top_5 = leaderboard.get_top(n=5)
```

**Compare multiple runs:**

```python
from flowyml import compare_runs

comparison = compare_runs(
    run_ids=["run_123", "run_124", "run_125"],
    metrics=["accuracy", "f1_score", "latency"]
)
```

---

### 7️⃣ **Pipeline Templates**

Create pipelines from pre-built templates:

```python
from flowyml import create_from_template, list_templates

# See available templates
print(list_templates())  # ['ml_training', 'etl', 'ab_test']

# Create from template
pipeline = create_from_template(
    'ml_training',
    name='my_training',
    data_loader=load_data,
    preprocessor=preprocess,
    trainer=train_model,
    evaluator=evaluate,
    model_saver=save_model
)

# Run it
result = pipeline.run()
```

**Available Templates:**
- `ml_training`: Standard ML training workflow
- `etl` / `data_pipeline`: Extract-Transform-Load
- `ab_test`: A/B testing with model comparison

---

### 8️⃣ **Checkpointing**

Resume failed pipelines:

```python
from flowyml import PipelineCheckpoint

checkpoint = PipelineCheckpoint(run_id="run_123")

# In your step
def expensive_computation():
    result = do_work()
    checkpoint.save_step_state("compute", result)
    return result

# Resume later
if checkpoint.exists():
    state = checkpoint.load()
    last_step = state['last_completed_step']
    output = checkpoint.load_step_state(last_step)
```

---

### 9️⃣ **Human-in-the-Loop**

Add approval gates to pipelines:

```python
from flowyml import approval, Pipeline

pipeline = Pipeline("sensitive_operation")

# Add approval step
approval_step = approval(
    name="approve_deployment",
    approver="data-team",
    timeout_seconds=3600,
    auto_approve_if=lambda: os.getenv("AUTO_APPROVE") == "true"
)

pipeline.add_step(approval_step)
```

---

### 🔟 **Evaluations Framework** ⚡NEW

Evaluate ML models and LLM outputs with 17 built-in scorers:

```python
from flowyml.evals import evaluate, EvalDataset, Accuracy, F1Score, EvalSuite

# Quick evaluation
data = EvalDataset.create_classical(
    "model_v2", predictions=[1, 0, 1, 1], targets=[1, 0, 0, 1]
)
result = evaluate(data=data, scorers=[Accuracy(threshold=0.9), F1Score()])

# Reusable suite
suite = EvalSuite("quality_gates", scorers=[Accuracy(), F1Score()])
result = suite.run(data=data, experiment="model_v2")

# GenAI (LLM-as-a-judge)
from flowyml.evals import Relevance, make_judge

judge = make_judge("quality", "Evaluate response accuracy", model="openai:/gpt-4o-mini")
result = evaluate(data=genai_data, scorers=[Relevance(), judge])
```

**Features:**
- 17 built-in scorers (classification, regression, GenAI)
- Custom scorers via `make_judge()` and `make_scorer()`
- Automatic regression detection
- CI/CD quality gates (`EvalAssert`)
- Pipeline-native evaluations (`EvalStep`)
- Judge Arena (A/B test evaluators)
- Continuous evaluation via schedules
- Trace-to-evaluation bridge
- Full CLI: `flowyml eval run/compare/assert/scorers`
- See full guide: [`docs/evaluations.md`](evaluations.md)

---

## 📊 UI Features

Access the web UI at `http://localhost:8080`:

- **Dashboard**: Overview stats
- **Runs**: Pipeline execution history
- **Pipelines**: All registered pipelines
- **Assets**: Browse artifacts
- **Experiments**: Compare experiment runs
- **Traces**: View LLM call traces (NEW!)

---

## 🎯 Quick Start Example

Complete example using multiple features:

```python
from flowyml import (
    Pipeline, step, context,
    configure_notifications,
    PipelineScheduler,
    ModelLeaderboard,
    flowymlKerasCallback
)

# 1. Configure notifications
configure_notifications(console=True)

# 2. Define pipeline
ctx = context(epochs=10, batch_size=32)
pipeline = Pipeline("training", context=ctx)

@step(outputs=["model", "metrics"])
def train(epochs: int, batch_size: int):
    model = create_model()
    history = model.fit(
        x_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[flowymlKerasCallback("mnist_exp")]
    )
    return model, history.history

pipeline.add_step(train)

# 3. Add to leaderboard
leaderboard = ModelLeaderboard("val_accuracy")

@step(inputs=["metrics"])
def log_to_leaderboard(metrics):
    accuracy = metrics['val_accuracy'][-1]
    leaderboard.add_score("my_model", run_id="...", score=accuracy)

pipeline.add_step(log_to_leaderboard)

# 4. Schedule to run daily
scheduler = PipelineScheduler()
scheduler.schedule_daily(
    name="daily_training",
    pipeline_func=lambda: pipeline.run(),
    hour=2
)
scheduler.start()
```

---

## 📚 Additional Resources

- Full documentation: `/docs`
- API Reference: `/api/docs` (when server is running)
- Examples: `/examples`
- Roadmap: `ROADMAP.md`

---

## 🆕 Pipeline Engineering Features

### 1️⃣1️⃣ **Build-Time Type Validation** ⚡NEW

Catch type mismatches between connected steps at `Pipeline.build()` time:

```python
@step(outputs=["model"])
def train() -> Model:
    return Model(clf)

@step(inputs=["model"])
def evaluate(model: Dataset):  # ❌ Type mismatch! Expects Dataset, gets Model
    pass

pipeline.add_step(train).add_step(evaluate)
pipeline.build()  # Raises: Pipeline type validation failed
```

---

### 1️⃣2️⃣ **Map Tasks** ⚡NEW

Distribute work over collections with configurable concurrency and per-item retries:

```python
from flowyml import map_task

@map_task(concurrency=8, retries=2, min_success_ratio=0.95)
def process_document(doc: dict) -> dict:
    return transform(doc)

result = process_document(documents)
print(f"Processed {result.successes}/{result.total}")
```

See full guide: [`docs/advanced/map-tasks.md`](advanced/map-tasks.md)

---

### 1️⃣3️⃣ **Dynamic Workflows** ⚡NEW

Generate sub-pipelines at runtime based on intermediate results:

```python
from flowyml import dynamic, Pipeline, step

@dynamic(outputs=["best_model"])
def hyperparameter_search(config: dict):
    sub = Pipeline("hp_search")
    for lr in config["learning_rates"]:
        @step(outputs=[f"model_lr_{lr}"])
        def train(learning_rate=lr):
            return train_model(learning_rate)
        sub.add_step(train)
    return sub
```

See full guide: [`docs/advanced/dynamic-workflows.md`](advanced/dynamic-workflows.md)

---

### 1️⃣4️⃣ **Sub-Pipeline Composition** ⚡NEW

Nest entire pipelines as steps in other pipelines:

```python
preprocess = Pipeline("preprocessing")
preprocess.add_step(clean_data).add_step(normalize)

parent = Pipeline("training")
parent.add_sub_pipeline(preprocess, inputs=["raw"], outputs=["clean"])
parent.add_step(train_model)
```

See full guide: [`docs/advanced/subpipelines.md`](advanced/subpipelines.md)

---

### 1️⃣5️⃣ **Artifact Catalog with Lineage** ⚡NEW

Centralized artifact discovery, tagging, and lineage tracking:

```python
from flowyml import ArtifactCatalog

catalog = ArtifactCatalog()  # Auto-selects local or remote backend

# Register with lineage
model_id = catalog.register(
    name="classifier", artifact_type="Model",
    parent_ids=[dataset_id],
    tags={"stage": "production"},
)

# Discover and search
models = catalog.search("classifier")
lineage = catalog.get_lineage(model_id)
```

See full guide: [`docs/advanced/artifact-catalog.md`](advanced/artifact-catalog.md)

---

### 1️⃣6️⃣ **Immutable Pipeline Snapshots** ⚡NEW

Capture exact pipeline definitions at execution time for reproducibility:

```python
from flowyml import freeze_pipeline

snapshot = freeze_pipeline(pipeline)
print(snapshot.snapshot_hash)    # SHA-256 seal
print(snapshot.step_hashes)     # Per-step code hashes
assert snapshot.verify()        # Verify integrity
```

---

### 1️⃣7️⃣ **Enhanced DAG Validation** ⚡NEW

`Pipeline.build()` now detects:
- **Dead outputs**: assets produced but never consumed
- **Unreachable nodes**: steps that can't be reached from root nodes
- **Type mismatches**: incompatible types between connected steps

---

### 1️⃣8️⃣ **Prompt Asset** ⚡NEW

First-class prompt management for LLM/GenAI workflows — versioned, templated, and lineage-tracked:

```python
from flowyml import Prompt

# Text prompt with variable substitution
prompt = Prompt(
    name="summarize",
    template="Summarize the following text:\n\n{text}",
    model="gpt-4",
    temperature=0.7,
    max_tokens=500,
)
rendered = prompt.render(text="Long document here...")

# Chat-style prompt (OpenAI format)
chat_prompt = Prompt.create(
    template=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain {topic} in simple terms."},
    ],
    name="explain",
    model="gpt-4",
)
messages = chat_prompt.render(topic="neural networks")

# Lineage: track prompt evolution
v2 = Prompt(name="summarize_v2", template="...", parent=prompt)
# v2.parents → [prompt]
```

**Features:**
- Text and chat-style (multi-message) templates
- `{variable}` substitution with `.render()`
- Model config tracking (model, temperature, max_tokens)
- Automatic variable extraction from templates
- Full lineage tracking (parent → child prompt chains)
- `.create()` factory with auto-generated names

---

### 1️⃣9️⃣ **Checkpoint Asset** ⚡NEW

Training checkpoint management with epoch/step tracking and framework-agnostic persistence:

```python
from flowyml import Checkpoint

# Save training state
checkpoint = Checkpoint.create(
    data=model.state_dict(),
    name="resnet50_epoch_10",
    epoch=10,
    step=5000,
    metrics={"loss": 0.23, "accuracy": 0.91},
    is_best=True,
)

# Inspect checkpoint
print(checkpoint.epoch)              # 10
print(checkpoint.checkpoint_metrics)  # {"loss": 0.23, "accuracy": 0.91}
print(checkpoint.is_best)            # True

# Save to disk (auto-detects PyTorch or falls back to pickle)
path = checkpoint.save("checkpoints/epoch_10.pt")

# Lineage: link to parent model
model_asset = Model(name="resnet50", data=model)
ckpt = Checkpoint.create(data=state, parent=model_asset)
```

**Features:**
- Epoch and global step tracking
- Metrics capture at checkpoint time
- `is_best` flag for best-model tracking
- Automatic state key extraction (for PyTorch state_dicts)
- Framework-agnostic save (PyTorch → pickle fallback)
- Lineage tracking (checkpoint → model relationship)

---

### 2️⃣0️⃣ **Stack Hydration from YAML** ⚡NEW

Define stacks in `flowyml.yaml` and hydrate them into live, fully-wired Stack objects:

```yaml
# flowyml.yaml
stacks:
  local:
    orchestrator: { type: local }
    artifact_store: { type: local, path: "./artifacts" }

  gcp-prod:
    orchestrator: { type: vertex_ai, project: my-gcp-project }
    artifact_store: { type: gcs, bucket: ml-artifacts }
    model_registry: { type: vertex_model_registry }
    experiment_tracker: { type: mlflow }
    artifact_routing:
      Model:   { store: gcs, register: true, deploy: true }
      Dataset: { store: gcs, path: "{run_id}/data/{step_name}" }
      Metrics: { log_to_tracker: true }

active_stack: local
```

```python
from flowyml.plugins.config import PluginConfig
from flowyml.plugins.stack_config import StackManager

config = PluginConfig("flowyml.yaml")
manager = StackManager(config)

# Hydrate into a live stack (resolves components via ComponentRegistry)
live_stack = manager.get_stack("gcp-prod").to_stack()

# Use it directly
pipeline = Pipeline("train", stack=live_stack)
pipeline.run()

# Context-manager switching
with manager.use_stack("gcp-prod"):
    pipeline.run()  # Uses GCP stack
# Reverts to previous active stack
```

**Features:**
- `StackConfig.to_stack()` hydrates YAML → live Stack objects
- Automatic component resolution via `ComponentRegistry`
- Fallback to `LocalOrchestrator` / `LocalArtifactStore` for unknown types
- Artifact routing rules attached to hydrated stack
- `use_stack()` context manager for temporary stack switching
- `FLOWYML_STACK` environment variable override

---

## 📓 Design Pipelines Visually with FlowyML Notebook

!!! tip "🌊 FlowyML Notebook — The Reactive Notebook That Ships to Production"
    **[FlowyML Notebook](flowyml-notebook.md)** is a companion reactive notebook environment that replaces Jupyter for ML workflows. Write Python cells with automatic dependency tracking, then promote directly to FlowyML pipelines with one click.

    ```bash
    pip install flowyml-notebook
    fml-notebook dev  # 🔥 Launch with hot-reload
    ```

    **Key features:** Reactive DAG · Pure .py Storage · SmartPrep Advisor · Algorithm Matchmaker · 43 Recipes · GitHub Integration · AI Assistant · Publish as App

    [:octicons-arrow-right-24: Learn more](flowyml-notebook.md) · [:octicons-mark-github-16: GitHub](https://github.com/UnicoLab/flowyml-notebook) · [:octicons-globe-24: Docs](https://unicolab.github.io/flowyml-notebook/latest/)

---

## 🌐 Explore the Full Ecosystem

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 📓 FlowyML Notebook
Reactive notebook for designing and shipping pipelines visually.

[Explore →](flowyml-notebook.md)
</div>

<div class="header-card" markdown>
### 🔌 Integrations
Keras, PyTorch, MLflow, W&B, GCP, AWS, Azure, and more.

[Browse →](integrations/keras.md)
</div>

<div class="header-card" markdown>
### 🌊 Ecosystem
The complete FlowyML Universe and how it all fits together.

[Discover →](ecosystem.md)
</div>

</div>

---

**Happy MLOps! 🌊**

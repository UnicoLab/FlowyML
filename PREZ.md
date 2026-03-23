# 🌊 FlowyML — 50-Minute Presentation Guide

> **Tagline:** *The Enterprise-Grade ML Pipeline Framework for Humans*
>
> **Format:** Slides only — code snippets + GUI screenshots + architecture diagrams
>
> **Audience:** ML Engineers, Data Scientists, MLOps teams, Tech Leads

---

## 🎯 Presentation Strategy

### Core Narrative

> **"We stopped building around Tasks and started building for the Flow."**

The talk is structured as a **visual product showcase**. Each feature is presented with a brief code snippet on one half of the slide and a **GUI screenshot** on the other. The audience should leave thinking *"I need to try this."*

### Slide Design Rules

| Rule | Detail |
|------|--------|
| **Split-screen layout** | Left = code snippet (≤10 lines). Right = GUI screenshot |
| **Dark theme** | Match the FlowyML UI aesthetic |
| **Max 35 slides** | ~1.5 min/slide average |
| **Code is short** | Never more than 10 lines on a slide. Tease, don't teach |
| **Screenshots are the hero** | Every feature gets a GUI screenshot or architecture diagram |
| **Use `docs/logo.png`** | Title slide, section dividers, closing slide |

### Screenshot Preparation

Before the presentation, **capture screenshots** of everything listed in the [Screenshot Checklist](#-screenshot-checklist) section at the bottom. Run pipelines, evals, and traces beforehand so the GUI is populated.

---

## ⏱️ Timing Breakdown (50 min)

| # | Section | Slides | Time | Type |
|---|---------|--------|------|------|
| 1 | **Opening** — The MLOps Pain | 2 | 3 min | Story |
| 2 | **What is FlowyML?** — Vision & Philosophy | 3 | 4 min | Comparison tables |
| 3 | **Core Engine** — Pipeline + Steps + Context | 3 | 5 min | Code + GUI screenshot |
| 4 | **GUI Showcase** — Dashboard, DAG, Artifacts, Experiments | 4 | 5 min | Screenshots only |
| 5 | **Asset System** — Model / Dataset / Metrics + Lineage | 3 | 4 min | Code + GUI screenshot |
| 6 | **Intelligent Caching** | 2 | 3 min | Code + diagram |
| 7 | **Type Routing & Multi-Stack** — Killer Feature | 4 | 5 min | Code + YAML + diagram |
| 8 | **Classical AI Showcase** — Training, Eval, Leaderboard | 4 | 5 min | Code + GUI screenshots |
| 9 | **GenAI Showcase** — Observability, Traces, Cost | 4 | 5 min | Code + GUI screenshots |
| 10 | **Advanced Orchestration** | 2 | 3 min | Code snippets |
| 11 | **Production Story** — 11 features rapid-fire | 2 | 3 min | Feature table |
| 12 | **Architecture & Extensibility** | 2 | 3 min | Diagram + table |
| 13 | **Closing** — CTA | 1 | 2 min | Logo + pip install |
| | **Total** | **~36** | **50 min** | |

---

## 📑 Slide-by-Slide Script

---

### SECTION 1 — Opening: The MLOps Pain (3 min)

#### Slide 1: Title

```
🌊 FlowyML
The Enterprise-Grade ML Pipeline Framework for Humans

[logo.png]

Built with ❤️ by UnicoLab
```

#### Slide 2: The Problem

**Visual:** Icon grid showing 5-6 tool logos (MLflow, Airflow, ZenML, Keras, W&B, cloud providers)

**Talking points:**
- *"Raise your hand if your ML stack involves 5+ separate tools"*
- MLflow for tracking, Airflow for orchestration, ZenML for stacks, Keras callbacks, separate cloud storage…
- Config duplication, YAML hell, context-switching, vendor lock-in
- *"What if the infrastructure was invisible?"*

---

### SECTION 2 — What is FlowyML? (4 min)

#### Slide 3: The "Distilled Fusion"

| Inspiration | What FlowyML Took |
|-------------|-------------------|
| **Airflow** | DAG logic, scheduling, conditional execution |
| **ZenML** | Stack architecture, cloud-swap with config |
| **MLflow** | Experiment tracking, metrics, model registry |
| **Keras** | Native callbacks, real-time training streaming |
| **Metaflow** | Pure Python DX, no DSLs |

#### Slide 4: The Paradigm Shift

| Traditional (Task-Centric) | FlowyML (Artifact-Centric) |
|---------------------------|---------------------------|
| "Run step A, then step B" | "Produce a **Model** and a **Dataset**" |
| Steps are generic functions | Steps produce/consume **typed assets** |
| File paths, manual wiring | **Automatic lineage** — every asset knows its parents |
| Infrastructure in code | Infrastructure in `flowyml.yaml` |

#### Slide 5: Feature Comparison

| | FlowyML | Traditional |
|---|---------|-------------|
| DX | 🐍 Pure Python | 📜 YAML / DSL |
| Routing | 🧠 Auto by type | 🔌 Manual wiring |
| Caching | ⚡ Content-hash | 🐢 Timestamp |
| Assets | 📦 First-class | 📁 File paths |
| Multi-Stack | 🌍 One env var | 🔒 Vendor lock-in |
| GenAI | 🤖 Built-in tracing | 🧩 External tools |
| Build Validation | ✅ Type-safe at build time | 💥 Runtime errors |

---

### SECTION 3 — Core Engine (5 min)

#### Slide 6: Quick Start Code

```python
from flowyml import Pipeline, step, context

@step(outputs=["dataset"])
def load_data(batch_size: int = 32):
    return [i for i in range(batch_size)]

@step(inputs=["dataset"], outputs=["model"])
def train_model(dataset, learning_rate: float = 0.01):
    print(f"Training on {len(dataset)} items with lr={learning_rate}")
    return "model_v1"

ctx = context(learning_rate=0.05, batch_size=64)
pipeline = Pipeline("quickstart", context=ctx)
pipeline.add_step(load_data).add_step(train_model)
pipeline.run()
```

**Key points to call out:**
1. `@step` — inputs/outputs define DAG edges
2. Context injection — `learning_rate` auto-injected from `context()`
3. Method chaining — `.add_step().add_step()` fluent API
4. Zero YAML, zero config files

#### Slide 7: Rich CLI Output

**📸 Screenshot:** Terminal showing the Rich CLI output with colored step groups, execution times, cached/executed status, and pipeline summary

#### Slide 8: Pipeline Configuration Options

```python
pipeline = Pipeline(
    name="training_pipeline",
    context=ctx,                     # Parameter injection
    enable_cache=True,               # Smart caching
    stack=my_stack,                  # Local / GCP / AWS
    project_name="ml_project",      # Multi-tenant isolation
    version="v1.0.0",               # Pipeline versioning
    enable_checkpointing=True,      # Resume on failure
    enable_experiment_tracking=True  # Auto-log to tracker
)
```

---

### SECTION 4 — GUI Showcase (5 min)

> **Talking point:** *"Everything you see here is automatic. No special code to log anything — just run your pipeline."*

#### Slide 9: Dashboard

**📸 Screenshot:** FlowyML Dashboard showing:
- Recent runs with status indicators (success/failure/running)
- Pipeline statistics (success rate, avg duration, total runs)
- System health cards

#### Slide 10: DAG View — Pipeline Visualization

**📸 Screenshot:** A pipeline's DAG (React Flow graph) with:
- Step nodes colored by status (green=success, blue=running)
- Arrows showing data flow
- Click on a step → inset showing step detail panel (inputs, outputs, logs, duration)

#### Slide 11: Experiments — Run Comparison

**📸 Screenshot:** Experiments page with:
- 2-3 runs selected for side-by-side comparison
- Metric columns (accuracy, f1, loss) across runs
- Metric trend charts (loss curves, accuracy over time)

#### Slide 12: Assets — Artifact Browser + Lineage

**📸 Screenshot (split):**
- Left: Artifact browser listing Models, Datasets, Metrics with types and timestamps
- Right: Lineage graph showing `raw_data → processed_data → model → metrics` chain

---

### SECTION 5 — Asset System (4 min)

#### Slide 13: Asset Hierarchy & Auto-Extraction

```
Asset (base)
├── Dataset   → auto: num_samples, num_features, column_stats
├── Model     → auto: framework, parameters, layers, optimizer
├── Metrics   → key-value pairs, step tracking
├── FeatureSet→ engineered features
└── Parameters→ hyperparameters
```

**Supported frameworks:** Keras, PyTorch, sklearn, XGBoost, LightGBM, Hugging Face

#### Slide 14: Code — Creating Typed Assets

```python
from flowyml import Model, Dataset

# Model — auto-detects framework, extracts metadata
model = Model.create(data=trained_keras_model, name="resnet50")
# .framework → "keras" | .num_layers → 50 | .optimizer → "adam"

# Dataset — auto-extracts statistics
dataset = Dataset.create(data=df, name="training_data")
# .num_samples → 10000 | .column_stats → {mean, std, min, max}

# Framework-specific shortcuts
Model.from_sklearn(clf, name="classifier")
Model.from_pytorch(net, name="resnet")
Model.from_keras(model, name="cnn", callback=keras_callback)
```

#### Slide 15: GUI — Asset Detail + Lineage Graph

**📸 Screenshot (split):**
- Left: Model detail view showing auto-extracted metadata (framework, num_layers, optimizer, parameters)
- Right: Dataset detail view showing auto-extracted stats (num_samples, num_features, column statistics)
- Bottom: Lineage graph visualization

> **Key message:** *"Reproducibility requires lineage. FlowyML tracks not just what you trained, but what data created it."*

---

### SECTION 6 — Intelligent Caching (3 min)

#### Slide 16: How Caching Works

**Visual: Flow diagram**
```
Cache Key = hash(source_code) + hash(inputs) + hash(config)
  ↓
Key exists? → Load from disk (ms) ⚡
Key missing? → Execute → Save to disk
```

| Strategy | Invalidates When | Best For |
|----------|-----------------|----------|
| `code_hash` (default) | Code OR inputs change | Development |
| `input_hash` | Only inputs change | Production — stable logic |
| `cache=False` | Always runs | Side effects (email, DB) |

#### Slide 17: Impact — Before vs After

```
First run:   load_data (2.3s) → preprocess (4.1s) → train (180s)  = 186s
Second run:  CACHED (0.01s) → CACHED (0.01s) → CACHED (0.02s)    = 0.04s ⚡
```

**📸 Screenshot:** Run detail showing steps with CACHED badges and ~0s execution times

> **Key message:** *"Typical savings: 40-60% on cloud compute bills."*

---

### SECTION 7 — Type Routing & Multi-Stack (5 min) ← MIC DROP

#### Slide 18: Type-Based Routing

```python
@step
def train_model(...) -> Model:
    return Model(obj, name="classifier", version="1.0.0")
    # → Auto-saved to GCS/S3
    # → Auto-registered to Vertex AI / SageMaker Model Registry
    # → Auto-deployed to endpoint (if configured)
```

You define **WHAT** (Model, Dataset, Metrics) → FlowyML handles **WHERE**

| Asset Type | Auto-Storage | Auto-Registry | Auto-Deploy |
|------------|-------------|--------------|-------------|
| `Model` | GCS / S3 | Vertex AI / SageMaker | Vertex Endpoints |
| `Dataset` | GCS / S3 | — | — |
| `Metrics` | Metadata Store | MLflow / W&B | — |

#### Slide 19: The flowyml.yaml — Full Stack Config

```yaml
stacks:
  local:
    orchestrator: { type: local }
    artifact_store: { type: local, path: "./artifacts" }

  gcp-prod:
    orchestrator: { type: vertex_ai, project: ${GCP_PROJECT} }
    artifact_store: { type: gcs, bucket: ml-artifacts }
    model_registry: { type: vertex_model_registry }
    model_deployer: { type: vertex_endpoint }
    experiment_tracker: { type: mlflow }
    artifact_routing:
      Model:   { store: gcs, register: true, deploy: true }
      Dataset: { store: gcs, path: "{run_id}/data/{step_name}" }
      Metrics: { log_to_tracker: true }

  aws-staging:
    orchestrator: { type: sagemaker, region: us-east-1 }
    artifact_store: { type: s3, bucket: staging-ml }
    model_registry: { type: sagemaker_model_registry }

active_stack: local
```

#### Slide 20: Switching Stacks — 3 Ways

```bash
# 1. Environment variable
FLOWYML_STACK=gcp-prod python pipeline.py

# 2. CLI
flowyml stack set gcp-prod
flowyml stack list
flowyml stack show

# 3. Python context manager
with use_stack("gcp-prod"):
    pipeline.run()
```

#### Slide 21: Stack Architecture Diagram

```
    Your Code (Pure Python)
         ↓
    ┌──────────────────────────┐
    │       FlowyML Core       │
    │   Steps → DAG → Run      │
    └──────────┬───────────────┘
               ↓
    ┌──────────────────────────┐
    │   Stack (flowyml.yaml)   │
    ├──────────────────────────┤
    │ Orchestrator  → Vertex/K8s│
    │ Artifact Store → GCS/S3   │
    │ Metadata Store → SQL/PG   │
    │ Model Registry → Vertex   │
    │ Experiment Tracker → MLflow│
    │ Container Registry → GCR  │
    └──────────────────────────┘
```

---

### SECTION 8 — Classical AI Showcase (5 min)

#### Slide 22: Training Pipeline

```python
from flowyml import Pipeline, step, context, Model, Dataset

@step(outputs=["dataset"])
def load_data():
    return Dataset.from_csv("data.csv", name="training_data")

@step(inputs=["dataset"], outputs=["model"])
def train(dataset, n_estimators: int = 100) -> Model:
    clf = RandomForestClassifier(n_estimators=n_estimators)
    clf.fit(dataset.data.drop("target", axis=1), dataset.data["target"])
    return Model.from_sklearn(clf, name="fraud_detector")

pipeline = Pipeline("fraud_detection", context=context(n_estimators=200),
                     project_name="ml_platform")
pipeline.add_step(load_data).add_step(train).run()
```

**📸 Screenshot:** GUI showing the training run's DAG + model artifact with auto-extracted sklearn metadata

#### Slide 23: Evaluations Framework

```python
from flowyml.evals import evaluate, EvalDataset, Accuracy, F1Score, EvalSuite

data = EvalDataset.create_classical("fraud_test",
    predictions=[1, 0, 1, 1, 0], targets=[1, 0, 0, 1, 0])

suite = EvalSuite("quality_gates",
    scorers=[Accuracy(threshold=0.9), F1Score(threshold=0.85)])
result = suite.run(data=data, experiment="model_v2")
result.notify_if_regression(previous_result, channel="slack")
```

| Capability | Description |
|-----------|-------------|
| **29+ Scorers** | Classification (7), Regression (6), GenAI LLM-as-Judge (4), DeepEval, RAGAS, Phoenix |
| **EvalSuite** | Reusable scorer collections |
| **EvalAssert** | CI/CD quality gates |
| **JudgeArena** | A/B test evaluators vs human labels |
| **EvalSchedule** | Continuous eval on cron |
| **TraceBridge** | Evaluate LLM traces directly |

#### Slide 24: Model Leaderboard + Experiment Comparison

**Left half: Code**
```python
from flowyml import ModelLeaderboard
lb = ModelLeaderboard("accuracy")
lb.add_score("random_forest", run_id="run_1", score=0.92)
lb.add_score("xgboost", run_id="run_2", score=0.95)
lb.display()
```

**Right half: 📸 Screenshot** of the Experiments comparison page with 2-3 models side-by-side

#### Slide 25: Keras Integration + Data Drift

**Top half:**
```python
from flowyml import flowymlKerasCallback
model.fit(x_train, y_train, callbacks=[
    flowymlKerasCallback(experiment_name="mnist", log_model=True)
])
# Auto-logs: metrics, architecture, optimizer, checkpoints
```

**📸 Screenshot:** Keras training history curves in the GUI (loss/accuracy over epochs)

**Bottom half:**
```python
from flowyml import detect_drift
drift = detect_drift(reference_data=train_feat, current_data=prod_feat, threshold=0.1)
if drift['drift_detected']:
    notifier.on_drift_detected('age', drift['psi'])
```

---

### SECTION 9 — GenAI Showcase (5 min)

#### Slide 26: 4 Supported Frameworks

| Framework | Integration | Code Change |
|-----------|------------|-------------|
| **LangGraph** | `@observe()` / `trace_graph()` / `instrument()` | 1-2 lines |
| **LangChain** | `@observe_chain()` / `trace_chain()` | 1-2 lines |
| **OpenAI SDK** | `TracedOpenAI()` / `patch_openai()` | 1 line |
| **Any Framework** | `@observe()` / `trace()` / `log_llm_call()` | 1-3 lines |

#### Slide 27: OpenAI — Drop-in Tracing

**Left: Code**
```python
from flowyml import TracedOpenAI

client = TracedOpenAI(project="demo")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is FlowyML?"}],
)
client.finalize()
```

**Right: 📸 Screenshot** of terminal showing the trace summary:
```
═════════════════════════════════════════
  🔗 FlowyML Trace — demo (openai)
═════════════════════════════════════════
  🤖 LLM Calls  : 1
  📊 Tokens     : 234 (prompt: 12 / completion: 222)
  💰 Est. Cost  : $0.0004
  🏷  Models     : gpt-4o-mini
  ⏱  Duration   : 1.2s
═════════════════════════════════════════
```

#### Slide 28: LangGraph Agent Tracing

```python
from flowyml import observe

@observe(name="customer_agent", project="support")
def handle_ticket(ticket_id: str, flowyml_session=None):
    return graph.invoke(
        {"messages": [HumanMessage(content=f"Handle ticket {ticket_id}")]},
        config=flowyml_session.config,  # Auto-injected callbacks
    )
```

**📸 Screenshot:** Trace Viewer in GUI showing multi-step LangGraph agent — LLM calls, tool invocations, parent-child trace tree, token counts, costs

#### Slide 29: What Gets Tracked + Cost Estimation

| Metric | Auto-Tracked |
|--------|-------------|
| 🤖 LLM Calls | Count, model, prompts, responses (saved as artifacts) |
| 🔧 Tool Calls | Name, input, output, duration |
| 🔗 Chain Steps | Parent-child hierarchy |
| 📊 Tokens | Prompt + completion + total |
| 💰 Cost | Per-call and session USD |
| ⏱ Latency | Per-step and total |
| 📐 Trace Tree | Full span hierarchy, canvas-ready DAG |
| ❌ Errors | Full context + stack traces |

**Cost models for:** OpenAI, Anthropic, Google, Mistral, Cohere

**Bridge to Evals:**
```python
from flowyml.evals import evaluate_traces, Relevance, Toxicity
results = evaluate_traces(trace_ids=["t-001"], scorers=[Relevance(), Toxicity()])
```

> *"Free. Open-source. Framework-agnostic. No LangSmith. No vendor lock-in."*

---

### SECTION 10 — Advanced Orchestration (3 min)

#### Slide 30: Map Tasks + Dynamic Workflows + Sub-Pipelines

**Map Tasks:**
```python
@map_task(concurrency=8, retries=2, min_success_ratio=0.95)
def process_document(doc: dict) -> dict:
    return transform(doc)
```

**Dynamic Workflows:**
```python
@dynamic(outputs=["best_model"])
def hyperparameter_search(config: dict):
    sub = Pipeline("hp_search")
    for lr in config["learning_rates"]:
        sub.add_step(train_with_lr(lr))
    return sub
```

**Sub-Pipelines:**
```python
preprocess = Pipeline("preprocessing")
preprocess.add_step(clean_data).add_step(normalize)

parent = Pipeline("full_training")
parent.add_sub_pipeline(preprocess, inputs=["raw"], outputs=["clean"])
parent.add_step(train_model)
```

#### Slide 31: Build-Time Validation

```python
@step(outputs=["model"])
def train() -> Model: ...

@step(inputs=["model"])
def evaluate(model: Dataset):  # ❌ Type mismatch caught at BUILD time!
    ...

pipeline.build()  # → Raises before any code runs!
```

`pipeline.build()` also detects:
- **Dead outputs** — assets produced but never consumed
- **Unreachable nodes** — steps that can't be reached

---

### SECTION 11 — Production Story (3 min)

#### Slide 32: Production Features (rapid-fire table)

| Feature | What It Does | Code |
|---------|-------------|------|
| 📅 **Scheduling** | Built-in cron | `scheduler.schedule_daily("retrain", ..., hour=2)` |
| 💾 **Checkpointing** | Resume from last success | `PipelineCheckpoint(run_id="run_123")` |
| 🔔 **Notifications** | Slack / email / console | `notifier.on_pipeline_failure(name, run_id, error)` |
| 👤 **Human-in-the-Loop** | Approval gates | `approval(name="deploy", approver="ml-team")` |
| 📊 **Data Drift** | PSI-based with alerts | `detect_drift(reference, current, threshold=0.1)` |
| 🏗️ **Step Grouping** | Same container, aggregated resources | `@step(execution_group="preprocessing")` |
| 📋 **Templates** | Instant pipelines | `create_from_template('ml_training', ...)` |
| 🔄 **Versioning** | Hash-based change detection | `pipeline.compare_with("v1.0.0")` |
| 🏢 **Projects** | Multi-tenant isolation | `Pipeline("train", project_name="client_a")` |
| 📦 **Artifact Catalog** | Discovery, tagging, lineage | `catalog.register(name="clf", parent_ids=[ds_id])` |
| 🔒 **Immutable Snapshots** | SHA-256 sealed definitions | `freeze_pipeline(pipeline)` |

#### Slide 33: Performance Toolkit

| Tool | What It Does |
|------|-------------|
| **Lazy Evaluation** | Defer computations until needed |
| **Parallel Execution** | `ParallelExecutor(max_workers=4)` |
| **Incremental Computation** | Recompute only what changed |
| **GPU Management** | Auto-select best GPU, memory monitoring |
| **DataFrame Optimization** | 50-80% memory savings via downcasting |

---

### SECTION 12 — Architecture & Extensibility (3 min)

#### Slide 34: Module Map + Integration Ecosystem

```
flowyml/
├── core/         → Pipeline, Step, Context, DAG, Versioning
├── assets/       → Model, Dataset, Metrics, FeatureSet
├── evals/        → 29+ scorers, JudgeArena, TraceBridge
├── stacks/       → Local, GCP, AWS, Azure, K8s
├── plugins/      → Orchestrators, Stores, Registries, Deployers
├── integrations/ → Keras, PyTorch, sklearn, MLflow, W&B, LangGraph, OpenAI
├── monitoring/   → GenAI observability, System/Pipeline monitors
├── storage/      → Artifact + Metadata stores
├── cli/          → flowyml CLI
└── ui/           → FastAPI + React dark-mode dashboard
```

| Category | Integrations |
|----------|-------------|
| **Cloud** | GCP (Vertex AI, GCS, GCR), AWS (SageMaker, S3, ECR), Azure |
| **Tracking** | MLflow, W&B, TensorBoard |
| **ML** | Keras, PyTorch, sklearn, HuggingFace |
| **GenAI** | LangGraph, LangChain, OpenAI SDK, any framework |
| **Ops** | Docker, Kubernetes, Slack |
| **Compat** | ZenML auto-import — 50+ integrations |

#### Slide 35: Plugin System

```python
# 4 ways to extend FlowyML:
@register_component                     # 1. Decorator
registry.register(MyClass, "name")      # 2. Manual
# pyproject.toml entry-points           # 3. Pip-installable
load_component("my_package.components") # 4. Dynamic
```

---

### SECTION 13 — Closing (2 min)

#### Slide 36: Call to Action

```
🌊 flowyml

pip install flowyml

github.com/UnicoLab/FlowyML
unicolab.github.io/FlowyML/latest/

Apache 2.0 · Open Source
v1.0 → v1.8 in 3 months · Active Development

Built with ❤️ by UnicoLab
```

> **Closing line:** *"Tasks are the past. Artifacts are the future. Come build with us."*

---

## 📸 Screenshot Checklist

Capture these **before** building the slide deck. Run the necessary commands to populate the GUI.

### Setup Commands

```bash
pip install "flowyml[all]"
flowyml ui start
# Then run example pipelines to populate UI with data
```

### Screenshots to Capture

| # | What | Where | For Slide |
|---|------|-------|-----------|
| 1 | **Rich CLI output** — pipeline run with colored steps | Terminal | §3, Slide 7 |
| 2 | **Dashboard** — recent runs, stats, health | `localhost:8765` | §4, Slide 9 |
| 3 | **DAG View** — pipeline graph (React Flow) | Click a pipeline | §4, Slide 10 |
| 4 | **Step Detail Panel** — inputs, outputs, logs | Click a step in DAG | §4, Slide 10 |
| 5 | **Experiment Comparison** — 2-3 runs side-by-side | Experiments page | §4, Slide 11 |
| 6 | **Metric Charts** — loss curves, accuracy trends | Experiments page | §4, Slide 11 |
| 7 | **Artifact Browser** — list of Models, Datasets | Assets page | §4, Slide 12 |
| 8 | **Lineage Graph** — raw→processed→model→metrics | Assets → Lineage tab | §4, Slide 12 |
| 9 | **Model Detail** — auto-extracted metadata | Click a Model | §5, Slide 15 |
| 10 | **Dataset Detail** — auto-extracted stats | Click a Dataset | §5, Slide 15 |
| 11 | **Cached Run** — steps showing CACHED badges | Run with cache hits | §6, Slide 17 |
| 12 | **Training Run + Model Artifact** — sklearn metadata | Classical pipeline run | §8, Slide 22 |
| 13 | **Experiment Comparison** — multiple model runs | Experiments page | §8, Slide 24 |
| 14 | **Keras Training History** — live metric curves | After Keras callback run | §8, Slide 25 |
| 15 | **Trace Summary** — terminal output with tokens/cost | After TracedOpenAI call | §9, Slide 27 |
| 16 | **Trace Viewer** — LLM trace tree in GUI | Traces page | §9, Slide 28 |
| 17 | **Trace Detail** — token usage, cost, spans | Click a trace | §9, Slide 29 |

---

## ❓ Anticipated Q&A

| Question | Answer |
|----------|--------|
| *"How does this compare to ZenML?"* | Lighter — no server needed locally. We added GenAI observability, 29+ evals, and a built-in UI. Plus a ZenML compat layer: `import_all_zenml()`. |
| *"Can I use existing MLflow?"* | Yes — first-class plugin. Set `experiment_tracker: { type: mlflow }` in `flowyml.yaml`. |
| *"Is the UI required?"* | No — everything is Python/CLI-first. UI is optional via `flowyml ui start`. |
| *"Production-ready?"* | GCP Stack (Vertex AI + GCS) is prod-ready. AWS + K8s stacks in progress. |
| *"GenAI observability vs LangSmith?"* | Free, open-source, framework-agnostic. No vendor lock-in. |
| *"Team isolation?"* | Projects system — separate metadata, artifacts, and runs per team/client. |

---

## 🎯 5 Key Messages

1. **"Pure Python, Zero DSLs"** — write a function, get a pipeline
2. **"One Env Var to Production"** — `FLOWYML_STACK=production` swaps your entire infrastructure
3. **"Artifacts, Not Tasks"** — Models, Datasets, Metrics are first-class with automatic lineage
4. **"GenAI-Native"** — built-in LLM tracing, cost tracking, evaluation — any framework
5. **"Batteries Included"** — UI, scheduling, evals, notifications, drift, caching — all built in

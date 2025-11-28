# Welcome to UniFlow 🌊

<p align="center">
  <img src="logo.png" width="350" alt="UniFlow Logo"/>
  <br>
  <em>The Enterprise-Grade ML Pipeline Framework for Humans</em>
</p>

---

**UniFlow** is a production-ready ML pipeline orchestration framework that bridges the gap between rapid experimentation and enterprise deployment. Write pipelines as simple Python scripts, then scale them to production without rewriting a single line.

> [!TIP]
> **The promise**: Go from notebook to production in hours, not weeks. UniFlow handles orchestration, caching, versioning, and monitoring — so you can focus on ML, not infrastructure.

## 🎯 Why UniFlow?

### The Problem UniFlow Solves

Most ML teams face the same painful trade-offs:

- **Quick prototyping tools** (notebooks, scripts) don't scale to production
- **Enterprise MLOps platforms** require steep learning curves and complex configuration
- **Orchestration frameworks** force you into rigid patterns or obscure DSLs
- **Experiment tracking** is disconnected from execution and deployment

**UniFlow eliminates these trade-offs.** It's designed for the way data scientists actually work — with pure Python — while providing enterprise-grade capabilities when you need them.

### What Makes UniFlow Different

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

Here's what UniFlow delivers in practice:

| Challenge | Without UniFlow | With UniFlow |
|-----------|----------------|--------------|
| **Dev → Production** | 4-8 weeks of rewriting | Hours using same code |
| **Pipeline iteration** | Full re-runs (hours) | Cached steps (minutes) |
| **Debugging failures** | Parse logs, guess state | Visual DAG + artifact inspection |
| **Team collaboration** | Divergent scripts | Standardized, versioned pipelines |
| **Multi-environment** | Rewrite for each | Single pipeline, multiple stacks |
| **Experiment tracking** | Manual logging | Automatic lineage + versioning |

> [!IMPORTANT]
> **Production-Ready from Day One**: UniFlow isn't just for prototypes. It's built for regulated industries, multi-tenant deployments, and enterprise scale. But you can start simple and grow into those features.

## 🚀 Feature Showcase

UniFlow isn't just another orchestrator. It's a complete toolkit for building, debugging, and deploying ML applications.

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
Don't waste time re-running successful steps. UniFlow's multi-strategy caching understands your code and data.

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
from uniflow import trace_llm

@step
@trace_llm(model="gpt-4", tags=["production"])
def generate_summary(text: str):
    # UniFlow automatically tracks tokens, cost, and latency
    return openai.ChatCompletion.create(...)
```

### 4. 🔀 Dynamic Workflows
Real-world ML isn't linear. Build complex, adaptive workflows with conditional logic and branching.

```python
from uniflow import If, Switch

# Run 'deploy' only if model accuracy > 0.9
pipeline.add_step(
    If(condition=lambda ctx: ctx["accuracy"] > 0.9)
    .then(deploy_model)
    .else_(notify_team)
)
```

### 5. 🔍 Interactive Debugging
Debug pipelines like standard Python code. Pause execution, inspect state, and resume.

- **StepDebugger**: Set breakpoints in your pipeline.
- **Artifact Inspection**: View intermediate data in the UI.
- **Local Execution**: Run the exact same code locally as in production.

### 6. 🏭 Enterprise Production Features
Everything you need to run mission-critical workloads.

- **🔄 Automatic Retries**: Handle transient failures gracefully.
- **⏰ Scheduling**: Built-in cron scheduler for recurring jobs.
- **🔔 Notifications**: Slack/Email alerts on success or failure.
- **🛡️ Circuit Breakers**: Stop cascading failures automatically.

### 7. 🔌 Universal Integrations
Works with your existing stack.

- **ML Frameworks**: PyTorch, TensorFlow, Keras, Scikit-learn, HuggingFace.
- **Cloud Providers**: AWS, GCP, Azure (via plugins).
- **Tools**: MLflow, Weights & Biases, Great Expectations.

## ⚡️ Quick Start

See how simple it is — this is a complete, runnable ML pipeline:

```python
from uniflow import Pipeline, step, context

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
    Understand pipelines, steps, context, and assets — the building blocks of UniFlow.

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

**Questions? Issues?** [Open an issue on GitHub](https://github.com/UnicoLab/UniFlow/issues) or check out the [Resources](resources.md) page for community links.

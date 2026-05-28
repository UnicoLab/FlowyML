# 🚀 Getting Started with FlowyML

Welcome to FlowyML! In the next 5-10 minutes, you'll go from zero to running your first production-ready pipeline. No prior MLOps experience required.

<div class="hero-section" markdown>

## 🎯 What You'll Build

A complete ML pipeline with data loading, processing, context injection, and real-time monitoring. These patterns scale from quick prototypes to enterprise deployments.

</div>

---

## 📦 Installation

FlowyML requires Python 3.9 or higher.

### 🔧 Basic Installation

```bash
pip install flowyml
```

!!! tip "💡 Pro Tip"
    Use a virtual environment (`venv` or `conda`) to avoid dependency conflicts with other projects.

### 🌟 Full Installation (Recommended)

Includes UI support and common ML dependencies:

```bash
pip install "flowyml[ui]"
pip install "flowyml[all]"
```

**What this gets you**: The web dashboard, Keras integration, cloud storage backends, and everything you need for production deployments. Start with this unless you have size constraints.

### ✅ Verify Installation

```bash
flowyml --version
```

You should see the version number. If not, check that your Python PATH is configured correctly.

---

## 📁 Your First Project

Let's create a new project using the CLI.

```bash
flowyml init my-first-project
cd my-first-project
```

This creates a directory structure like this:

```
my-first-project/
├── flowyml.yaml         # Project configuration
├── README.md            # Project documentation
├── requirements.txt     # Python dependencies
└── src/
    └── pipeline.py      # Your pipeline code lives here
```

!!! tip "🏗️ Why this structure?"
    It separates code (`src/`), configuration (`flowyml.yaml`), and dependencies (`requirements.txt`) — exactly what you need for clean version control and team collaboration.

---

## 🧪 Creating a Pipeline

Open `src/pipeline.py` and replace its content with this simple example:

```python linenums="1"
from flowyml import Pipeline, step, context

# 1. Define Steps
@step(outputs=["data"])
def fetch_data():
    print("Fetching data...")
    return [1, 2, 3, 4, 5]

# 2. Define another Step with inputs
@step(inputs=["data"], outputs=["processed"])
def process_data(data):
    print(f"Processing {len(data)} items...")
    return [x * 2 for x in data]

# 3. Create and configure the Pipeline
if __name__ == "__main__":
    # Create pipeline
    pipeline = Pipeline("my_first_pipeline")

    # Add steps in order
    pipeline.add_step(fetch_data)
    pipeline.add_step(process_data)

    # 4. Run it!
    result = pipeline.run()

    if result.success:
        print(f"✓ Pipeline finished successfully!")
        print(f"Result: {result.outputs}")
    else:
        print(f"✗ Pipeline failed")
```

### 🔬 Understanding What Just Happened

Let's break down the key concepts:

1. **`@step` decorator**: Turns any Python function into a pipeline step. The `outputs=["data"]` tells FlowyML what this step produces.

2. **Data flow**: The `@step(inputs=["data"], ...)` on `process_data` automatically connects it to `fetch_data`'s output. No manual wiring needed.

3. **Pipeline assembly**: `pipeline.add_step()` builds your DAG. FlowyML figures out the execution order based on data dependencies.

4. **Execution**: `pipeline.run()` executes all steps in the right order and returns a result object with status and outputs.

!!! important "🎯 Why this matters"
    This same pattern works whether you have 3 steps or 300. The complexity doesn't grow with your pipeline.

---

## ▶️ Running the Pipeline

Execute the script:

```bash
python src/pipeline.py
```

You should see output indicating the steps are executing:

```
Fetching data...
Processing 5 items...
✓ Pipeline finished successfully!
Result: {'processed': [2, 4, 6, 8, 10]}
```

!!! tip "⚡ Caching in Action"
    Pipelines are idempotent by default. Run it again and watch how caching kicks in — steps that haven't changed won't re-execute.

---

## 🖥️ Visualizing with the UI

Now, let's see your pipeline in the FlowyML UI — this is where the magic happens for debugging and monitoring.

**Step 1: Start the UI server**

```bash
flowyml ui start
```

You'll see:
```
🌊 FlowyML UI server started
📊 Dashboard: http://localhost:8080
🔌 API: http://localhost:8080/api
```

!!! note "🔧 What's running"
    A lightweight FastAPI server that displays your pipeline runs, DAG visualizations, and artifact inspection — all in real-time.

**Step 2: Run your pipeline** (in a separate terminal)

```bash
python src/pipeline.py
```

**Step 3: Watch it live!**

Open your browser to `http://localhost:8080`. You'll see:

- **📊 Pipeline DAG**: Visual graph showing step dependencies
- **⚡ Real-time execution**: Steps highlight as they run
- **🔍 Artifact inspection**: Click any step to see its inputs/outputs
- **📜 Run history**: Compare different runs side-by-side

!!! success "🎉 Why the UI matters"
    Imagine debugging a failed step at 3 AM in production. Instead of grep'ing through logs, you see exactly: which step failed, what its inputs were, the full error traceback, and what downstream steps were skipped.

---

## 🎛️ Adding Context & Parameters

Let's make the pipeline configurable using **context** — one of FlowyML's killer features.

Update your pipeline:

```python linenums="1"
from flowyml import Pipeline, step, context

@step(outputs=["data"])
def fetch_data(dataset_size: int = 5):  # ← Parameter with default
    print(f"Fetching {dataset_size} items...")
    return list(range(dataset_size))

@step(inputs=["data"], outputs=["processed"])
def process_data(data, multiplier: int = 2):  # ← Another parameter
    print(f"Processing with multiplier={multiplier}...")
    return [x * multiplier for x in data]

if __name__ == "__main__":
    # Create context with your config
    ctx = context(
        dataset_size=10,
        multiplier=3
    )

    # Pass context to pipeline
    pipeline = Pipeline("configurable_pipeline", context=ctx)
    pipeline.add_step(fetch_data)
    pipeline.add_step(process_data)

    result = pipeline.run()
    print(f"Result: {result.outputs}")
```

Run it again:

```bash
python src/pipeline.py
```

Output:
```
Fetching 10 items...
Processing with multiplier=3...
Result: {'processed': [0, 3, 6, 9, 12, ...]}
```

### 💡 The Power of Context Injection

!!! tip "🔑 Why this is revolutionary"
    You just separated configuration from code. The same pipeline can run with different configs for **Dev** (small dataset), **Staging** (medium dataset), and **Production** (full dataset). Change the context, not the code.

---

## 📚 Next Steps

Congratulations! You've built a complete pipeline with monitoring. Here's where to go next based on your goals:

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🎯 Production Pipelines

- **[Projects & Multi-Tenancy](user-guide/projects.md)** — Organize teams & environments
- **[Scheduling](user-guide/scheduling.md)** — Cron-style automation
- **[Versioning](user-guide/versioning.md)** — Track & rollback changes
</div>

<div class="header-card" markdown>
### 🚀 Performance & Scale

- **[Caching Strategies](advanced/caching.md)** — Save compute costs
- **[Parallel Execution](advanced/parallel.md)** — Run steps concurrently
- **[Performance Guide](user-guide/performance.md)** — Benchmarks & tuning
</div>

<div class="header-card" markdown>
### 🔬 Advanced ML Features

- **[Assets & Lineage](core/assets.md)** — Typed artifacts
- **[Model Registry](user-guide/model-registry.md)** — Version models
- **[LLM Tracing](advanced/llm-tracing.md)** — GenAI costs & tracing
</div>

</div>

### 🧠 Deep Dive into Concepts

→ **[Core Concepts: Pipelines](core/pipelines.md)** — Master pipeline design patterns

→ **[Core Concepts: Steps](core/steps.md)** — Learn step best practices

→ **[Core Concepts: Context](core/context.md)** — Advanced context injection techniques

### 🎨 Integrate with Your Stack

→ **[Keras Integration](integrations/keras.md)** — Automatic experiment tracking

→ **[GCP Integration](integrations/gcp.md)** — Deploy to Google Cloud

→ **[Custom Components](guides/custom-components.md)** — Extend FlowyML

---

!!! tip "📓 Prefer a Visual Environment? Try FlowyML Notebook"
    **[FlowyML Notebook](flowyml-notebook.md)** is a reactive notebook that replaces Jupyter. Write Python cells with automatic dependency tracking, then promote directly to FlowyML pipelines with one click.

    ```bash
    pip install flowyml-notebook && fml-notebook dev
    ```

    [Learn more about FlowyML Notebook →](flowyml-notebook.md)

---

**Questions or stuck?** Check out the [Resources](resources.md) page for community links, tutorials, and support channels.

**Ready to dive deeper?** The [User Guide](user-guide/projects.md) is your next stop for production-grade patterns.

**Explore the ecosystem →** See the full [FlowyML Universe](ecosystem.md) including Notebook, Keras tools, and cloud integrations.

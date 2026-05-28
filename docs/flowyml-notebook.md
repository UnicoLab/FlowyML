<div class="hero-section" markdown>

## 📓 FlowyML Notebook

**The Reactive Notebook That Ships to Production** — Design, experiment, and deploy FlowyML pipelines in an interactive visual environment.

<span class="feature-badge">🔄 Reactive DAG</span>
<span class="feature-badge">📝 Pure Python</span>
<span class="feature-badge">🚀 One-Click Deploy</span>
<span class="feature-badge">🤖 AI Assistant</span>

</div>

---

## 🧪 What is FlowyML Notebook?

FlowyML Notebook is a **reactive, DAG-powered** notebook environment designed to replace Jupyter for production ML workflows. Every cell is a node in a live dependency graph — change a variable, and only the cells that depend on it re-execute automatically. No stale state. No hidden bugs. No "restart and run all."

<div class="pitch-grid" markdown>

<div class="pitch-card" markdown>
### 📝 Pure Python Cells
Write standard Python in `.py` files — no JSON blobs, no `.ipynb` lock-in. Every notebook is a clean, diffable, version-controllable script with **automatic dependency tracking** between cells.
</div>

<div class="pitch-card" markdown>
### 🚀 Ship to Production
Promote any notebook directly to a **FlowyML pipeline** with one click. Cells are extracted in topological order, wrapped with `@step` decorators, and ready for production — zero code changes required.
</div>

<div class="pitch-card" markdown>
### 🤝 GitHub-Native Collaboration
Full **GitHub integration** as the collaboration backend. Branch, commit, push, snapshot diffs — all from the notebook sidebar. No proprietary cloud platform needed.
</div>

</div>

!!! info "🔗 Part of the FlowyML Ecosystem"
    FlowyML Notebook is the **interactive companion** to the [FlowyML pipeline framework](index.md). Use the notebook for exploration and prototyping, then promote to FlowyML pipelines for production orchestration — same code, same artifacts, seamless transition.

---

## 🌟 Key Features

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🔄 Reactive DAG Engine <span class="feature-pill new">CORE</span>

Cells form a **live dependency graph**. Change a variable and only dependent cells re-execute — automatically. Visualize the full pipeline topology with the built-in DAG viewer. No manual re-runs, no stale state.
</div>

<div class="header-card" markdown>
### 🏭 Pipeline Promotion <span class="feature-pill pro">PRO</span>

Promote notebooks directly to **production FlowyML pipelines** with one click. Cells are extracted in topological order, decorated with `@step`, and wired into a full pipeline. Your experiment becomes your deployment.
</div>

<div class="header-card" markdown>
### 📊 Rich Data Exploration <span class="feature-pill new">CORE</span>

Every DataFrame gets **automatic 10-tab profiling**: statistics, distributions, correlations, quality checks, memory analysis, type detection, outlier flags, and ML-ready insights. Zero extra code needed.
</div>

<div class="header-card" markdown>
### 🧠 SmartPrep Advisor <span class="feature-pill pro">PRO</span>

Auto-detects **missing values, skew, outliers, and high cardinality** in your data. Generates ready-to-run fix code — one click to insert scaling, encoding, imputation, and transformation cells.
</div>

<div class="header-card" markdown>
### 🎯 Algorithm Matchmaker <span class="feature-pill pro">PRO</span>

Auto-detects task type (classification, regression, clustering), **ranks ML algorithms 0–100** based on your data profile, and generates complete `sklearn` pipelines. Supports KDP + KerasFactory + MLPotion ecosystem.
</div>

<div class="header-card" markdown>
### 📦 43 Built-in Recipes <span class="feature-pill new">CORE</span>

Reusable code templates across **9 categories**: Core, Assets, Parallel, Observability, Evals, Data, ML, Visualization, and Ecosystem. Stop rewriting boilerplate — drag, click, and insert.
</div>

<div class="header-card" markdown>
### 🌐 Publish as App <span class="feature-pill beta">BETA</span>

Turn any notebook into an **interactive web application** with one click. Choose from 5 layouts: Linear, Grid, Tabs, Sidebar, or Dashboard. Configure theme, cell visibility, and source code display.
</div>

<div class="header-card" markdown>
### 🤖 AI Assistant <span class="feature-pill new">CORE</span>

Context-aware **code generation** that understands your notebook's variables, imports, and data shapes. Supports OpenAI, Google AI, Ollama, and Anthropic backends. Ask in natural language, get production-ready cells.
</div>

<div class="header-card" markdown>
### 🗄️ SQL First-Class <span class="feature-pill new">CORE</span>

Mixed **Python + SQL cells** in the same notebook. Use DuckDB for in-process analytics or SQLAlchemy for external databases. Query results flow into the reactive DAG as DataFrames.
</div>

<div class="header-card" markdown>
### 🐙 GitHub Native <span class="feature-pill new">CORE</span>

Branch, commit, push, and browse **snapshot diffs** — all from the notebook sidebar. Link a repository, review cell-level changes, and collaborate with your team using standard Git workflows.
</div>

</div>

---

## ⚡ Quick Start

### Installation

```bash
# Install the core package
pip install flowyml-notebook

# Or install with all ML & AI extensions
pip install "flowyml-notebook[all]"

# Or install with the UnicoLab Keras ecosystem (KDP + KerasFactory + MLPotion)
pip install "flowyml-notebook[keras]"
```

### Launch

```bash
# 🔥 Hot-reload development mode — auto-refreshes on code changes
fml-notebook dev

# 🚀 Production build — optimized for performance
fml-notebook start
```

The browser opens automatically. You're ready to build.

!!! tip "💡 Choose Your Install"
    | Extra | What You Get |
    |-------|-------------|
    | `flowyml-notebook` | Core notebook with reactive DAG, recipes, SQL, Git |
    | `flowyml-notebook[all]` | Everything above + AI assistant, SmartPrep, Algorithm Matchmaker |
    | `flowyml-notebook[keras]` | Everything above + KDP, KerasFactory, MLPotion integrations |

---

## 🔄 From Notebook to Pipeline

The killer feature of FlowyML Notebook: **your experiments become your production pipelines** — with zero code changes.

### Step 1 — Experiment in the Notebook

Write cells as you normally would. The reactive DAG tracks dependencies automatically:

```python
# Cell 1: Load data
import pandas as pd
dataset = pd.read_csv("data.csv")

# Cell 2: Train model (depends on Cell 1 via 'dataset')
from sklearn.ensemble import RandomForestClassifier
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(dataset.drop('target', axis=1), dataset['target'])
```

### Step 2 — Promote to Pipeline

Click **Promote to Pipeline** in the sidebar. FlowyML Notebook automatically:

1. Analyzes cell dependencies via the reactive DAG
2. Wraps each cell in a `@step` decorator
3. Maps variables to `inputs` and `outputs`
4. Extracts cells in **topological order**

The result is a production FlowyML pipeline:

```python
from flowyml import Pipeline, step, context

@step(outputs=["dataset"])
def load_data():
    """Produces the dataset artifact."""
    import pandas as pd
    return pd.read_csv("data.csv")

@step(inputs=["dataset"], outputs=["model"], cache=True)
def train_model(dataset):
    """Consumes 'dataset', produces 'model'. Cached for reproducibility."""
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(dataset.drop('target', axis=1), dataset['target'])
    return clf

# Auto-generated pipeline
pipeline = Pipeline("my_notebook")
pipeline.add_step(load_data).add_step(train_model)
pipeline.run()
```

### The Flow

```mermaid
graph LR
    A["📓 Notebook Cells"] -->|"Reactive DAG"| B["🔍 Dependency Analysis"]
    B -->|"Topological Sort"| C["⚙️ @step Wrapping"]
    C -->|"One Click"| D["🚀 FlowyML Pipeline"]
    D -->|"Deploy"| E["☁️ Production"]

    style A fill:#e1f5fe,stroke:#01579b
    style D fill:#e8f5e9,stroke:#2e7d32
    style E fill:#f3e5f5,stroke:#6a1b9a
```

!!! success "🎉 Same Code, Two Worlds"
    Your notebook cells **are** your pipeline steps. No rewriting, no copy-paste, no "translation layer." The reactive DAG in the notebook maps directly to the artifact DAG in FlowyML.

---

## 📊 Data Exploration — Zero Config

Every time you display a DataFrame, FlowyML Notebook generates **automatic multi-tab profiling**:

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 📈 Statistics
Column-level stats: mean, median, std, min/max, unique counts, null percentages, memory footprint, and dtype detection.
</div>

<div class="header-card" markdown>
### 📊 Distributions
Auto-generated histograms, bar charts, and density plots for every column. Numeric and categorical columns handled automatically.
</div>

<div class="header-card" markdown>
### 🔗 Correlations
Pearson correlation matrix with color-coded heatmap. Instantly spot multicollinearity and feature relationships.
</div>

<div class="header-card" markdown>
### 🧹 Quality Checks
Missing value analysis, duplicate detection, constant columns, high-cardinality flags, and data type consistency checks.
</div>

<div class="header-card" markdown>
### 🧠 ML Insights
Outlier detection, scaling recommendations, encoding suggestions, target variable identification, and feature importance hints.
</div>

<div class="header-card" markdown>
### 💾 Memory Profile
Per-column memory usage, dtype optimization suggestions, and total DataFrame footprint — know your data cost.
</div>

</div>

!!! note "🔍 Just Display It"
    No imports, no function calls, no configuration. Simply evaluate a DataFrame in a cell — the profiling appears automatically in the output panel.

---

## 🧾 43 Built-in Recipes

Stop rewriting boilerplate. Recipes are **searchable, categorized code templates** that insert production-ready cells:

| Category | Count | Examples |
|----------|:-----:|---------|
| **Core** | 8 | FlowyML Step, Pipeline, Context, Conditional Branching |
| **Assets** | 5 | Model Registration, Dataset Versioning, Artifact Catalog |
| **Parallel** | 4 | Map Tasks, Thread Pool, Async Steps, Distributed Execution |
| **Observability** | 5 | LLM Tracing, Experiment Tracking, Drift Detection, Alerts |
| **Evals** | 4 | Eval Suite, LLM-as-Judge, Quality Gates, Regression Detection |
| **Data** | 5 | DataFrame Profiling, SQL Queries, Data Validation, Sampling |
| **ML** | 5 | Sklearn Pipeline, Keras Training, Hyperparameter Search, Cross-Validation |
| **Visualization** | 3 | Plotly Dashboard, Matplotlib Grid, Correlation Heatmap |
| **Ecosystem** | 4 | KDP Smart Preprocessing, KerasFactory Quick Model, MLPotion Training, UnicoLab E2E |

!!! tip "🦄 Keras Ecosystem Recipes"
    Install `flowyml-notebook[keras]` to unlock 4 additional recipes for the UnicoLab ecosystem: **KDP** preprocessing layers, **KerasFactory** model architectures, **MLPotion** training pipelines, and the full **end-to-end pipeline**.

---

## 🤖 AI Assistant

The built-in AI assistant understands your notebook's **full context** — variables, imports, data shapes, and cell history — to generate production-ready code:

```python
# Ask in natural language:
# "Create a Random Forest pipeline with cross-validation for the 'dataset' DataFrame"

# The AI generates:
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
import numpy as np

X = dataset.drop('target', axis=1)
y = dataset['target']

clf = RandomForestClassifier(n_estimators=100, random_state=42)
scores = cross_val_score(clf, X, y, cv=5, scoring='accuracy')

print(f"Accuracy: {np.mean(scores):.4f} ± {np.std(scores):.4f}")
```

<div class="pitch-grid" markdown>

<div class="pitch-card" markdown>
### 🔌 Multi-Provider Support
**OpenAI**, **Google AI**, **Anthropic**, and **Ollama** (local). Bring your own API key or run fully offline with local models.
</div>

<div class="pitch-card" markdown>
### 🧠 Context-Aware Generation
The assistant sees your variables, DataFrames, imports, and execution history. Generated code uses **your actual data** — not generic placeholders.
</div>

<div class="pitch-card" markdown>
### ⚡ One-Click Insert
Generated cells are inserted directly into the notebook as reactive DAG nodes. Dependencies are tracked automatically — no manual wiring.
</div>

</div>

---

## 🗄️ SQL First-Class

Write SQL alongside Python in the same notebook. Results flow into the reactive DAG as DataFrames:

=== "DuckDB (In-Process)"

    ```sql
    -- SQL cell: query local files or DataFrames directly
    SELECT
        category,
        COUNT(*) as total,
        AVG(price) as avg_price
    FROM dataset
    WHERE price > 10
    GROUP BY category
    ORDER BY total DESC
    ```

=== "SQLAlchemy (External DBs)"

    ```python
    # Connect to PostgreSQL, MySQL, SQLite, etc.
    from sqlalchemy import create_engine
    engine = create_engine("postgresql://user:pass@localhost/mydb")

    # SQL cell with external connection
    results = engine.execute("""
        SELECT * FROM orders
        WHERE created_at > '2024-01-01'
        LIMIT 1000
    """)
    ```

!!! info "🦆 DuckDB — Zero Setup Analytics"
    DuckDB runs **in-process** with zero configuration. Query CSV files, Parquet files, and in-memory DataFrames directly with SQL — no database server needed.

---

## 🛠️ CLI Reference

| Command | Description |
|---------|-------------|
| `fml-notebook dev` | 🔥 Launch with Vite hot reload for development |
| `fml-notebook start` | 🚀 Launch with optimized production build |
| `fml-notebook run <file>` | ▶️ Execute a notebook headlessly (CI/CD, scripting) |
| `fml-notebook export <file>` | 📦 Export as FlowyML pipeline, HTML, PDF, or Docker |
| `fml-notebook app <file>` | 🌐 Deploy as interactive web application |
| `fml-notebook list --server <URL>` | 📚 List notebooks on a remote FlowyML server |

!!! tip "🐳 Export to Docker"
    Use `fml-notebook export my_notebook.py --format docker` to generate a self-contained Docker image with your notebook, dependencies, and data — ready for deployment to any container runtime.

---

## 🌐 Publish as App

Turn any notebook into a **production web application** with a single click:

<div class="step-timeline" markdown>

<div class="timeline-step" markdown>
#### 1. Choose Layout
Select from **5 layouts**: Linear (scrolling page), Grid (responsive cards), Tabs (section navigation), Sidebar (documentation-style), or Dashboard (data viz panels).
</div>

<div class="timeline-step" markdown>
#### 2. Configure Visibility
Toggle which cells are visible to end users. Hide data loading and preprocessing — show only results, visualizations, and interactive widgets.
</div>

<div class="timeline-step" markdown>
#### 3. Set Theme & Branding
Choose Light, Dark, or Auto theme. Add custom titles, descriptions, and branding for a polished user experience.
</div>

<div class="timeline-step" markdown>
#### 4. Deploy
One click to publish. Your notebook becomes a live web app with reactive updates — users interact with widgets and see results in real time.
</div>

</div>

---

## 🔗 How Notebook Connects to FlowyML

```mermaid
graph TB
    subgraph "FlowyML Notebook"
        N1["📓 Interactive Cells"] --> N2["🔄 Reactive DAG"]
        N2 --> N3["📊 Data Explorer"]
        N2 --> N4["🧠 SmartPrep Advisor"]
        N2 --> N5["🎯 Algorithm Matchmaker"]
    end

    subgraph "Promotion"
        N2 -->|"One Click"| P1["⚙️ Pipeline Export"]
        P1 --> P2["@step Decorators"]
        P2 --> P3["Artifact Mapping"]
    end

    subgraph "FlowyML Production"
        P3 --> F1["🏭 Pipeline Orchestrator"]
        F1 --> F2["☁️ Multi-Cloud Deploy"]
        F1 --> F3["📈 Experiment Tracker"]
        F1 --> F4["🔬 Eval Framework"]
    end

    style N1 fill:#e1f5fe,stroke:#01579b
    style P1 fill:#fff3e0,stroke:#e65100
    style F1 fill:#e8f5e9,stroke:#2e7d32
```

---

## 📚 Learn More

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🐙 GitHub Repository
Source code, issues, and discussions.

[:octicons-mark-github-16: **UnicoLab/flowyml-notebook**](https://github.com/UnicoLab/flowyml-notebook)
</div>

<div class="header-card" markdown>
### 📖 Full Documentation
Complete guides, API reference, and tutorials.

[:material-book-open-variant: **Notebook Docs**](https://unicolab.github.io/flowyml-notebook/latest/)
</div>

<div class="header-card" markdown>
### 📦 PyPI Package
Install, version history, and changelog.

[:material-package-variant: **flowyml-notebook**](https://pypi.org/project/flowyml-notebook/)
</div>

</div>

---

<p align="center">
  <b>Stop restarting kernels. Start shipping pipelines.</b><br>
  <i>FlowyML Notebook — from experiment to production in one click.</i>
</p>

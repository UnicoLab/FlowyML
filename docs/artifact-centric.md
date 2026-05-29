---
title: "Artifact-Centric Philosophy — FlowyML"
description: "Understand FlowyML's artifact-centric approach: how data dependencies replace manual DAG wiring, enabling automatic lineage tracking and type-safe pipelines."
---

<div class="hero-section" markdown>

## 💎 Artifact-Centric Architecture

The philosophical core of FlowyML. While traditional orchestrators focus on **Verbs** (tasks), FlowyML focuses on **Nouns** (data assets). This isn't just a naming choice — it's a paradigm shift that makes pipelines self-documenting, self-wiring, and production-ready from day one.

<span class="feature-badge">📦 Nouns > Verbs</span>
<span class="feature-badge">🔗 Auto-Lineage</span>
<span class="feature-badge">🎯 Type-Safe DAG</span>
<span class="feature-badge">☁️ Auto-Routing</span>

</div>

---

## 🏗️ Task-Centric vs. Artifact-Centric

### 1. The Death of the "Manual Arrow"
In a **Task-Centric** system, you define the order of execution. You tell the system: "Run Task A, then Task B."
```python
# Task-Centric (Airflow style)
task_a >> task_b
```
The movement of data between them is usually an afterthought—you manually pass S3 paths or local file locations between functions.

In **Artifact-Centric FlowyML**, you never define arrows. You define what data you *need* and what data you *produce*. The system builds the Directed Acyclic Graph (DAG) for you by matching these assets.

```python linenums="1"
# Artifact-Centric (FlowyML style)
@step(outputs=["clean_data"])
def preprocess(): ...

@step(inputs=["clean_data"], outputs=["model"])
def train(clean_data): ...
```
**Technical Benefit**: If you add a third step that also needs `clean_data`, FlowyML automatically forks the graph. If you remove an output that is needed downstream, the pipeline fails at **build-time**, not at 3 AM when the file isn't found.

### 2. The Global Artifact Catalog
The biggest technical hurdle in task-centric pipelines is the **"Handoff"**. You often see code like:
`pd.read_csv(f"s3://my-bucket/{run_id}/data.csv")`

This hardcodes your infrastructure directly into your machine learning code.

In FlowyML, steps don't know *where* data lives. They only know what it's called.
1. **Discovery**: A downstream step asks the **Catalog** for the artifact by name and version.
2. **Resolution**: The `ArtifactStore` (S3, GCS, Azure, or Local) resolves the physical location and handles the fetching/deserialization.
3. **Immutability**: Every artifact is uniquely identified by a `content_hash`. If the input artifact hasn't changed, the step is skipped entirely (Intelligent Caching).

### 3. Automatic Lineage (The "Data DNA")
In task-centric systems, if you find a bad model in production, tracing it back to the exact SQL query or raw CSV that created it is a forensic exercise.

In FlowyML, every Artifact carries its **Lineage**:
- **Parents**: Which assets were used to create this?
- **Step**: Which function version created this?
- **Run**: Which specific execution cycle produced it?

You can call `get_lineage(artifact_id)` to get a full recursive tree of every transformation that touched that specific piece of data.

---

## 📊 Technical Comparison

| Feature | Task-Centric (ZenML / Airflow) | Artifact-Centric (FlowyML) |
|---------|-------------------------------|----------------------------|
| **Core focus** | "What do I run?" (**Verbs**) | "What do I produce?" (**Nouns**) |
| **DAG Construction** | Imperative (Manual arrows) | **Declarative (Auto-Inferred)** |
| **Data Flow** | Manual "handoffs" (XCom/Paths) | **Seamless** (Managed by Registry) |
| **Validation** | Runtime failure (late detection) | **Compile-time** (Static validation) |
| **Portability** | Hardcoded file paths/infra | **Stack-based** (Abstracted URIs) |
| **Debugging** | "Why did Task X fail?" | "How was Artifact Y created?" |

---

## 🛠️ Performance Benefits

Because FlowyML understands the *data* and not just the *steps*, it can optimize execution in ways task-based systems cannot:

1. **Lazy Loading**: If an artifact is 50GB, FlowyML only fetches it from cloud storage if a downstream step actually requests it.
2. **Intelligent Caching**: Since we hash the *content* of artifacts, we can skip expensive training runs even if the code changed slightly (like a comment), as long as the inputs and effective logic remain the same.
3. **Parallelism without Overhead**: Multiple steps requiring the same artifact can run in parallel without the artifact being downloaded multiple times (using shared memory materializers).

---

## 💡 Summary Comparison

> "Artifact-Centricity means your pipeline is a **database of transformations**, rather than a script of events."

By focusing on the **Artifact**, FlowyML treats data as a first-class citizen. Every result is mathematically linked to its origin, enabling truly reproducible machine learning.

---

## 📍 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 🎢 Pipelines
See the artifact-centric approach in action.

[Pipelines →](core/pipelines.md)
</div>

<div class="header-card" markdown>
### 📦 Assets & Lineage
Deep dive into Model, Dataset, Metrics types.

[Assets →](core/assets.md)
</div>

<div class="header-card" markdown>
### 📎 Type-Based Routing
How artifacts flow to cloud storage automatically.

[Routing →](plugins/type_routing.md)
</div>

</div>

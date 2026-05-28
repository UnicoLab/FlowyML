---
title: FlowyML Glossary — Key Terms & Concepts
description: A comprehensive glossary of FlowyML-specific terms, concepts, and architectural patterns.
---

<div class="hero-section" markdown>

## 📖 Glossary

A comprehensive reference of FlowyML terminology. Whether you're new to the framework or need a quick refresher, this glossary covers every key concept.

<span class="feature-badge">📦 Artifacts</span>
<span class="feature-badge">🎢 Pipelines</span>
<span class="feature-badge">☊ Steps</span>
<span class="feature-badge">🔌 Plugins</span>

</div>

---

### Artifact
A typed, versioned data object that flows through a pipeline. Artifacts are the "nouns" in FlowyML's [artifact-centric architecture](artifact-centric.md). Common artifact types include `Model`, `Dataset`, `Metrics`, and `FeatureSet`. Each artifact is automatically tracked with full lineage.

### Artifact Catalog
A centralized registry of all artifacts produced across pipeline runs. Enables discovery, tagging, and lineage tracing. See [Assets & Lineage](core/assets.md).

### Artifact Store
The storage backend where artifacts are persisted. Can be local filesystem, S3, GCS, or Azure Blob — automatically selected based on the active [Stack](#stack).

### Auto-DAG
FlowyML's ability to automatically construct the execution graph (DAG) from step input/output declarations. You declare **what** each step produces and consumes; FlowyML infers **how** they connect. No manual wiring needed.

### Context
An immutable configuration object that provides parameters to pipeline steps via automatic injection. Eliminates the need for global variables or manual parameter passing. See [Context & Parameters](core/context.md).

### DAG (Directed Acyclic Graph)
The execution graph of a pipeline. Nodes are steps, edges are data dependencies. FlowyML auto-constructs the DAG from artifact types declared in step decorators.

### Evaluation Scorer
A callable that measures model quality. FlowyML includes 29+ built-in scorers for classification, regression, and GenAI tasks. See [Evaluations](evaluations.md).

### FlowyML Notebook
A companion reactive notebook environment. Write Python cells with automatic dependency tracking, then promote directly to FlowyML pipelines. See [FlowyML Notebook](flowyml-notebook.md).

### Judge Arena
An A/B testing framework for evaluation scorers. Run multiple evaluators on the same data and compare their outputs against human labels to find the most reliable judge.

### LLM-as-a-Judge
Using a Large Language Model to evaluate outputs of another model. FlowyML supports this pattern natively with built-in GenAI scorers and custom prompt templates.

### Map Task
A pattern for executing a step in parallel across a collection of inputs. Similar to `map()` in functional programming but distributed across workers. See [Advanced Features](advanced_features.md).

### Materializer
A serializer/deserializer responsible for converting artifacts between in-memory Python objects and persistent storage formats. Custom materializers can be created for any data type.

### Metadata Store
The database (SQLite or PostgreSQL) that stores pipeline run history, step execution records, artifact metadata, and evaluation results. Powers the FlowyML Dashboard.

### Pipeline
The top-level orchestration unit in FlowyML. A pipeline is composed of steps that process and produce artifacts. Pipelines auto-construct their DAG, manage execution ordering, and provide full observability. See [Pipelines](core/pipelines.md).

### Plugin
An extension module that adds functionality to FlowyML — storage backends, experiment trackers, cloud integrations, notification channels, and more. Plugins are the primary extensibility mechanism. See [Plugin System](plugins/overview.md).

### Quality Gate
An automated pass/fail check in a CI/CD pipeline based on evaluation metrics. If model quality drops below a threshold, the deployment is blocked.

### Recipe
A reusable code template available in [FlowyML Notebook](flowyml-notebook.md). 43 built-in recipes across 9 categories (Core, Assets, Parallel, Observability, Evals, Data, ML, Viz, Ecosystem).

### SmartPrep Advisor
A feature in FlowyML Notebook that auto-detects data quality issues (missing values, skew, outliers, high cardinality) and generates ready-to-run fix code.

### Stack
A named infrastructure configuration that bundles all backend choices (artifact store, metadata store, experiment tracker, orchestrator) into a single switchable profile. Change from local to cloud with `FLOWYML_STACK=production`. See [Architecture](architecture.md).

### Step
The atomic unit of work in a FlowyML pipeline. A Python function decorated with `@step` that declares its inputs and outputs. Steps are automatically cached, retriable, and tracked. See [Steps](core/steps.md).

### Step Group
A collection of steps that share a common configuration or execution context. Used for organizing complex pipelines into logical sections.

### Sub-Pipeline
A pipeline nested within another pipeline. Enables modular composition of complex workflows from reusable pipeline components.

### Type-Based Routing
The mechanism by which FlowyML automatically routes artifacts to appropriate storage backends based on their type. For example, `Model` artifacts may go to a model registry while `Dataset` artifacts go to a data lake.

---

## 📍 What's Next?

<div class="header-grid" markdown>

<div class="header-card" markdown>
### 💎 Artifact-Centric Design
Understand the philosophy behind FlowyML.

[Philosophy →](artifact-centric.md)
</div>

<div class="header-card" markdown>
### 🚀 Getting Started
Build your first pipeline in 5 minutes.

[Quick Start →](getting-started.md)
</div>

<div class="header-card" markdown>
### ✨ Features Explorer
Explore all FlowyML capabilities.

[Features →](FEATURES.md)
</div>

</div>

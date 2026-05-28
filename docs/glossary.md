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

<div class="glossary-nav" markdown>
<a href="#a">A</a> <a href="#c">C</a> <a href="#d">D</a> <a href="#e">E</a> <a href="#h">H</a> <a href="#l">L</a> <a href="#m">M</a> <a href="#o">O</a> <a href="#p">P</a> <a href="#s">S</a> <a href="#t">T</a>
</div>

---

### Artifact {#a}
A typed, versioned data object that flows through a pipeline. Artifacts are the "nouns" in FlowyML's [artifact-centric architecture](artifact-centric.md). Common artifact types include `Model`, `Dataset`, `Metrics`, and `FeatureSet`. Each artifact is automatically tracked with full lineage.

### Artifact Catalog
A centralized registry of all artifacts produced across pipeline runs. Enables discovery, tagging, and lineage tracing. See [Assets & Lineage](core/assets.md).

### Artifact Store
The storage backend where FlowyML saves pipeline artifacts (models, datasets, metrics). Can be local filesystem, GCS, S3, or Azure Blob Storage. See [Plugins Overview](plugins/overview.md).

### Auto-DAG
FlowyML's ability to automatically construct the execution graph (DAG) from step input/output declarations. You declare **what** each step produces and consumes; FlowyML infers **how** they connect. No manual wiring needed.

### Cache / Cache Key {#c}
FlowyML's content-based hashing system that skips re-execution of steps whose code and inputs haven't changed. See [Caching Guide](advanced/caching.md).

### Content Hash
A deterministic hash computed from a step's source code, input artifacts, and configuration. Used for cache invalidation. See [Caching Guide](advanced/caching.md).

### Context
An immutable configuration object that provides parameters to pipeline steps via automatic injection. Eliminates the need for global variables or manual parameter passing. See [Context & Parameters](core/context.md).

### DAG (Directed Acyclic Graph) {#d}
The execution graph of a pipeline. Nodes are steps, edges are data dependencies. FlowyML auto-constructs the DAG from artifact types declared in step decorators.

### Decorator
Python decorators (`@step`, `@dynamic`, `@map_task`) that transform regular functions into FlowyML pipeline components. See [Steps](core/steps.md).

### Evaluation Scorer {#e}
A callable that measures model quality. FlowyML includes 29+ built-in scorers for classification, regression, and GenAI tasks. See [Evaluations](evaluations.md).

### ExecutionStatus
An enum representing the current state of a pipeline run (PENDING, RUNNING, COMPLETED, FAILED). See [Migration Guide](migration_guide.md).

### FlowyML Notebook
A companion reactive notebook environment. Write Python cells with automatic dependency tracking, then promote directly to FlowyML pipelines. See [FlowyML Notebook](flowyml-notebook.md).

### Hook {#h}
A callback function registered to fire on specific pipeline lifecycle events (on_start, on_success, on_failure). See [Migration Guide](migration_guide.md).

### Judge Arena
An A/B testing framework for evaluation scorers. Run multiple evaluators on the same data and compare their outputs against human labels to find the most reliable judge.

### Lineage {#l}
The tracking of parent-child relationships between artifacts across pipeline runs. See [Artifact Catalog](advanced/artifact-catalog.md).

### LLM-as-a-Judge
Using a Large Language Model to evaluate outputs of another model. FlowyML supports this pattern natively with built-in GenAI scorers and custom prompt templates.

### Map Task {#m}
A pattern for executing a step in parallel across a collection of inputs. Similar to `map()` in functional programming but distributed across workers. See [Advanced Features](advanced_features.md).

### Materializer
A serializer/deserializer that converts Python objects to/from storage format. Supports custom types. See [Materializers](advanced/materializers.md).

### Metadata Store
The database backend that stores pipeline run history, step metadata, and artifact references. See [Plugins Overview](plugins/overview.md).

### Model Registry
A versioned catalog of trained models with deployment status tracking. See [Model Registry](user-guide/model-registry.md).

### Orchestrator {#o}
The execution backend that runs pipeline steps (local, Docker, Vertex AI, SageMaker). See [Plugins Overview](plugins/overview.md).

### Pipeline {#p}
The top-level orchestration unit in FlowyML. A pipeline is composed of steps that process and produce artifacts. Pipelines auto-construct their DAG, manage execution ordering, and provide full observability. See [Pipelines](core/pipelines.md).

### Plugin
An extension module that adds functionality to FlowyML — storage backends, experiment trackers, cloud integrations, notification channels, and more. Plugins are the primary extensibility mechanism. See [Plugin System](plugins/overview.md).

### Plugin Registry
FlowyML's discovery system that finds and loads plugins via Python entry points. See [Plugins Overview](plugins/overview.md).

### Quality Gate
An automated pass/fail check in a CI/CD pipeline based on evaluation metrics. If model quality drops below a threshold, the deployment is blocked.

### Recipe
A reusable code template available in [FlowyML Notebook](flowyml-notebook.md). 43 built-in recipes across 9 categories (Core, Assets, Parallel, Observability, Evals, Data, ML, Viz, Ecosystem).

### SmartPrep Advisor {#s}
A feature in FlowyML Notebook that auto-detects data quality issues (missing values, skew, outliers, high cardinality) and generates ready-to-run fix code.

### Stack
A named collection of plugins (artifact store + metadata store + orchestrator + optional extras) that defines a deployment target. Change from local to cloud with `FLOWYML_STACK=production`. See [Stack Architecture](architecture/stacks.md).

### Step
The atomic unit of work in a FlowyML pipeline. A Python function decorated with `@step` that declares its inputs and outputs. Steps are automatically cached, retriable, and tracked. See [Steps](core/steps.md).

### Step Group
A set of steps that share resources or execution configuration. See [Step Grouping](advanced/step-grouping.md).

### Sub-Pipeline
A pipeline nested within another pipeline. Enables modular composition of complex workflows from reusable pipeline components.

### SubmissionResult
The return type from non-blocking pipeline execution, containing run ID and methods to check status. See [Async Execution](async_execution.md).

### Type-Based Routing {#t}
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

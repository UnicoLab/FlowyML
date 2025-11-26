# Welcome to UniFlow 🌊

**UniFlow** is a modern, lightweight framework for building, running, and monitoring machine learning pipelines. It combines the simplicity of a library with the power of a full-fledged MLOps platform.

[![PyPI version](https://badge.fury.io/py/uniflow.svg)](https://badge.fury.io/py/uniflow)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Why UniFlow? 🚀

Machine learning workflows are complex. You need to manage data, code, configuration, and infrastructure. Existing tools are often either too simple (just scripts) or too complex (heavy K8s-based platforms).

**UniFlow hits the sweet spot:**

*   **Simple**: Just Python decorators. No YAML hell.
*   **Powerful**: Automatic caching, lineage tracking, and context injection.
*   **Beautiful**: A stunning, real-time UI included out of the box.
*   **Production-Ready**: Built for reliability and scalability.

## Key Features ✨

### 🌊 Unified Pipelines
Define pipelines using standard Python functions. UniFlow handles the execution graph, dependencies, and data flow automatically.

### 🧠 Intelligent Context
Forget about passing arguments manually through 10 layers of functions. UniFlow's **Context Injection** automatically delivers parameters to the steps that need them.

### ⚡ Smart Caching
Don't re-run expensive training jobs if nothing changed. UniFlow hashes your code and inputs to intelligently cache and reuse results.

### 👁️ Real-Time UI
Monitor your pipelines as they run. Visualize the DAG, inspect artifacts, and track metrics in a modern, dark-mode dashboard.

### 📦 Asset Management
Treat Datasets, Models, and Metrics as first-class citizens. UniFlow tracks their lineage, versioning, and metadata automatically.

###  🏛️ Model Registry
Manage your model lifecycle from development to production with a built-in registry.

### 🔄 Pipeline Versioning
Track, compare, and manage different versions of your pipelines with full change detection.

### 📁 Project Management
Organize pipelines into isolated projects for multi-tenant deployments and resource tracking.

### ⏰ Automated Scheduling
Schedule pipelines for daily, hourly, or interval-based execution with flexible control.

### 🔧 Advanced Debugging
Comprehensive debugging tools including breakpoints, tracing, profiling, and error analysis.

### ⚡ Performance Optimization
Lazy evaluation, parallel execution, incremental computation, and GPU management for optimal performance.

## Quick Example ⚡

```python
from uniflow import Pipeline, step, context

# Define steps using decorators
@step(outputs=["data"])
def load_data():
    return [1, 2, 3]

@step(inputs=["data"], outputs=["model"])
def train(data, learning_rate: float):
    # learning_rate injected from context!
    print(f"Training with lr={learning_rate}")
    return "model_v1"

# Create pipeline and add steps
ctx = context(learning_rate=0.05)
pipeline = Pipeline("training_pipeline", context=ctx)
pipeline.add_step(load_data)
pipeline.add_step(train)

# Run the pipeline
result = pipeline.run()
print(f"Success: {result.success}")
```

## Getting Started 📚

Ready to dive in?

[Get Started](getting-started.md){ .md-button .md-button--primary }
[View Examples](examples.md){ .md-button }

## Community 🤝

Join the UniFlow community!
- [GitHub Repository](https://github.com/uniflow-ai/uniflow)
- [Issue Tracker](https://github.com/uniflow-ai/uniflow/issues)

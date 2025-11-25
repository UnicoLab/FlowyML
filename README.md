# 🌊 UniFlow - Next-Generation ML Pipeline Framework

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

**UniFlow** is a developer-first ML pipeline orchestration framework that combines the simplicity of Metaflow with the power of ZenML and the elegance of asset-centric design.

## ✨ Features

- **🚀 5-Minute Onboarding** - From installation to first pipeline in minutes
- **🎯 Zero Boilerplate** - Automatic context injection, no manual wiring
- **💾 Intelligent Caching** - Multi-level caching with code and input hashing
- **📊 Asset-Centric** - First-class support for datasets, models, and metrics
- **🔄 Lineage Tracking** - Full provenance tracking for all assets
- **🏗️ Production Ready** - Built-in retries, versioning, and multi-cloud support
- **🎨 Framework Agnostic** - Works with PyTorch, TensorFlow, scikit-learn, and more

## 📦 Installation

```bash
pip install uniflow

# Or with extras
pip install "uniflow[pytorch]"     # PyTorch support
pip install "uniflow[tensorflow]"   # TensorFlow support
pip install "uniflow[ui]"            # UI for real-time monitoring
pip install "uniflow[all]"           # Everything
```

## 🖥️ Real-Time UI

Monitor your pipelines in real-time with the UniFlow UI:

```bash
# Install with UI support
pip install "uniflow[ui]"

# Build the frontend (first time only)
cd uniflow/ui/frontend
npm install && npm run build
cd ../../..

# Start the UI server
uniflow ui start

# Or start and open browser automatically
uniflow ui start --open-browser

# Check UI status
uniflow ui status
```

Then visit **http://localhost:8080** to see:
- 📊 Live pipeline execution status
- 📈 Real-time metrics and visualizations
- 🌳 Interactive DAG visualization
- 📦 Asset and artifact explorer
- 🔍 Experiment comparison tools

**See the full [UI Guide](UI_GUIDE.md) for detailed instructions.**


## 🚀 Quick Start

```python
from uniflow import Pipeline, step, context

# Define context once - parameters auto-injected!
ctx = context(
    learning_rate=0.001,
    epochs=10,
    batch_size=32
)

# Parameters automatically injected based on function signature
@step(outputs=["model/trained"])
def train_model(learning_rate: float, epochs: int, batch_size: int):
    print(f"Training with lr={learning_rate}, epochs={epochs}, batch={batch_size}")
    # Your training logic here
    model = {"weights": "trained", "accuracy": 0.95}
    return model

@step(inputs=["model/trained"], outputs=["metrics/evaluation"])
def evaluate_model(trained_model):
    print(f"Evaluating model: {trained_model}")
    metrics = {"accuracy": 0.95, "loss": 0.05}
    return metrics

# Create and run pipeline
pipeline = Pipeline("training_pipeline", context=ctx)
pipeline.add_step(train_model)
pipeline.add_step(evaluate_model)

result = pipeline.run(debug=True)
print(result.summary())
```

## 🎯 Core Concepts

### 1. Automatic Context Injection

No more passing parameters manually! UniFlow analyzes function signatures and automatically injects parameters from context.

```python
ctx = context(
    learning_rate=0.001,
    epochs=10,
    device="cuda"
)

@step(outputs=["model"])
def train(learning_rate: float, epochs: int, device: str):
    # All parameters auto-injected from context!
    return train_model(learning_rate, epochs, device)
```

### 2. Asset-Centric Design

Track datasets, models, and metrics as first-class objects with full lineage.

```python
from uniflow import Dataset, Model, Metrics

@step(outputs=["processed_data"])
def preprocess():
    return Dataset.create(
        data=processed_data,
        name="processed_train",
        properties={"samples": 10000}
    )

@step(inputs=["processed_data"], outputs=["trained_model", "training_metrics"])
def train(processed_data: Dataset):
    model = train_neural_network(processed_data)
    metrics = {"accuracy": 0.95, "loss": 0.05}
    
    return (
        Model.create(model, trained_on=processed_data),
        Metrics.create(**metrics)
    )
```

### 3. Intelligent Caching

Multi-level caching speeds up iterations dramatically:

```python
@step(cache="code_hash")  # Cache until code changes
def preprocess_data(data):
    return expensive_preprocessing(data)

@step(cache="input_hash")  # Cache based on inputs
def feature_engineering(data, config):
    return compute_features(data, config)
```

## 📊 Pipeline Visualization

```python
pipeline = Pipeline("my_pipeline", context=ctx)
pipeline.add_step(load_data)
pipeline.add_step(preprocess)
pipeline.add_step(train)

# Visualize the DAG
print(pipeline.visualize())
```

## 🔍 Experiment Tracking

```python
from uniflow import Experiment

exp = Experiment(
    name="baseline_training",
    description="Baseline model experiments"
)

result = pipeline.run()
exp.log_run(
    result.run_id,
    metrics={"accuracy": 0.95, "loss": 0.05}
)

# Compare runs
best_run = exp.get_best_run(metric="accuracy", maximize=True)
comparison = exp.compare_runs()
```

## 🏗️ Architecture

UniFlow uses a three-layer architecture:

1. **Developer Interface** - Decorator-based API with automatic context injection
2. **Execution Engine** - Graph-based DAG with intelligent caching
3. **Storage & Visualization** - SQLite/PostgreSQL + optional web UI

## 🎯 Why UniFlow?

| Feature | UniFlow | ZenML | Metaflow | Prefect |
|---------|-------|-------|----------|---------|
| Setup Time | < 5 min | ~1 hour | ~15 min | ~30 min |
| Auto Context | ✅ | ❌ | ❌ | ❌ |
| Asset-Centric | ✅ | ⚠️ | ❌ | ❌ |
| Caching | Multi-level | Basic | Basic | Basic |
| Lineage | Full | Partial | No | No |
| ML-Specific | ✅ | ✅ | ⚠️ | ❌ |

## 📚 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get started in 5 minutes
- **[UI Guide](UI_GUIDE.md)** - Complete guide for the real-time UI
- **[CLI Reference](CLI_REFERENCE.md)** - All CLI commands
- **[Development Guide](DEVELOPMENT.md)** - Contributing and development setup
- **[Architecture](UI_ARCHITECTURE.md)** - System architecture diagrams
- **[Design Document](DESIGN.md)** - Detailed design philosophy

## ❓ Troubleshooting

### `uniflow: command not found`

If you're developing from source:

```bash
# Install in editable mode
pip install -e ".[ui]"

# Or run without installing
python -m uniflow.cli.main ui start
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for details.

### UI shows "Frontend not built"

```bash
cd uniflow/ui/frontend
npm install
npm run build
```

### More Help

For more troubleshooting, see:
- [UI Guide - Troubleshooting](UI_GUIDE.md#troubleshooting)
- [Development Guide](DEVELOPMENT.md)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

UniFlow is released under the Apache 2.0 License. See [LICENSE](LICENSE) for details.

## 🌟 Star History

If you find UniFlow useful, please star the repository!

---

Built with ❤️ for the ML community

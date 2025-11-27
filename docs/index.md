# Welcome to UniFlow 🌊

<p align="center">
  <img src="logo.png" width="350" alt="UniFlow Logo"/>
  <br>
  <em> Next-Generation ML Pipeline Framework </em>
  <br>
  <br>
  <p align="center"><strong>Provided and maintained by <a href="https://unicolab.ai">🦄 UnicoLab</a></strong></p>
</p>

<p align="center">
  <a href="https://badge.fury.io/py/uniflow"><img src="https://badge.fury.io/py/uniflow.svg" alt="PyPI version"></a>
  <a href="https://github.com/UnicoLab/UniFlow/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://unicolab.ai"><img src="https://img.shields.io/badge/UnicoLab-ai-red.svg" alt="UnicoLab"></a>
</p>

---

## 🚀 Stop Wrestling with Infrastructure. Start Building Models.

**UniFlow** is the ML pipeline framework you've been waiting for. It combines the **simplicity of a Python script** with the **power of an enterprise MLOps platform**.

No more YAML hell. No more complex Kubernetes configurations just to run a script. Just pure Python.

<div class="grid cards" markdown>

-   :rocket: **5-Minute Setup**
    ---
    Go from `pip install` to a running pipeline in minutes. No complex infrastructure required.

-   :brain: **Intelligent Context**
    ---
    Forget passing arguments through 10 layers of functions. Parameters are automatically injected where they are needed.

-   :zap: **Smart Caching**
    ---
    Never re-run the same work twice. UniFlow intelligently caches results based on code and data hashes.

-   :eye: **Real-Time UI**
    ---
    Watch your pipelines execute in real-time with a stunning, dark-mode dashboard included out of the box.

</div>

## ⚡️ See It in Action

Define your pipeline with simple decorators. UniFlow handles the rest.

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

## 🌟 Why Developers Love UniFlow

| Feature | UniFlow | The Others |
| :--- | :---: | :---: |
| **Setup Time** | **< 5 min** | Hours |
| **Configuration** | **Python** | YAML / DSL |
| **Learning Curve** | **Low** | Steep |
| **UI** | **Included** | Separate / Paid |
| **Caching** | **Automatic** | Manual |

## 🛠️ Powerful Features

*   **🌊 Unified Pipelines**: Define DAGs using standard Python functions.
*   **📦 Asset Management**: First-class support for Datasets, Models, and Metrics.
*   **🏛️ Model Registry**: Manage your model lifecycle from dev to prod.
*   **🔄 Versioning**: Track every change in code, data, and configuration.
*   **⏰ Scheduling**: Built-in scheduler for recurring jobs.
*   **🔧 Debugging**: Breakpoints, tracing, and profiling tools.

## 🏁 Ready to Dive In?

<div class="grid cards" markdown>

-   :rocket: **Getting Started**
    ---
    Build your first pipeline in 5 minutes.
    [:arrow_right: Go to Guide](getting-started.md)

-   :books: **User Guide**
    ---
    Master all the features of UniFlow.
    [:arrow_right: Read Docs](user-guide/pipelines.md)

-   :computer: **Examples**
    ---
    See real-world usage patterns.
    [:arrow_right: View Examples](examples.md)

</div>

---

<p align="center">
  <strong>Making ML Pipelines Effortless 🧪✨</strong><br>
  <em>Built with ❤️ for the ML community by <a href="https://unicolab.ai">🦄 UnicoLab</a></em>
</p>

---
title: "Visualization — FlowyML"
description: "API reference for FlowyML visualization tools: DAG rendering, metric charts, and dashboard components."
---

# Visualization API 📊

FlowyML includes built-in visualization helpers for **inspecting, comparing, and presenting** pipeline results. You can render a pipeline's DAG directly in a Jupyter notebook, compare metrics across multiple runs side-by-side, or embed charts into dashboards. These utilities are designed to work out-of-the-box with any orchestrator and metadata store backend.

Tools for visualizing pipelines and artifacts.

## `flowyml.visualize`

### `show(pipeline)`

Display the DAG of a pipeline in a Jupyter notebook.

```python
from flowyml.visualize import show
show(pipeline)
```

### `compare_runs(runs)`

Display a comparison table of multiple runs.

```python
from flowyml.visualize import compare_runs
compare_runs([run1, run2])
```

---

## See Also

- [GUI Overview](../gui-overview.md) — the FlowyML web dashboard and interactive exploration tools

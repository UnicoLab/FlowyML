# Visualization API 📊

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

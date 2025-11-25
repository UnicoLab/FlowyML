# UniFlow UI Guide 🖥️

The UniFlow UI provides a real-time, interactive dashboard for monitoring and managing your ML pipelines. It offers a beautiful, modern interface to visualize execution graphs, inspect artifacts, and track metrics.

## Overview

The UI consists of two main components:
1.  **Backend Server**: A FastAPI-based service that manages state and serves the API.
2.  **Frontend Dashboard**: A React/Vite application that provides the visual interface.

## Getting Started 🚀

### Prerequisites

Ensure you have installed UniFlow with UI support:

```bash
pip install "uniflow[ui]"
```

### Starting the UI

To start the UI server, run:

```bash
uniflow ui start
```

This will:
1.  Start the backend API server (default port: 8000).
2.  Serve the frontend dashboard (default port: 8080).
3.  Open your browser to `http://localhost:8080`.

### Stopping the UI

To stop the UI server:

```bash
uniflow ui stop
```

## Features ✨

### 📊 Dashboard
The main dashboard provides a high-level view of your system:
- **Recent Runs**: See the status of the latest pipeline executions.
- **Pipeline Statistics**: Success rates, average duration, and total runs.
- **System Health**: Status of the backend and connected workers.

### 🔗 Pipeline Visualization
- **DAG View**: Visualize your pipeline steps as a Directed Acyclic Graph.
- **Step Details**: Click on any step to view its inputs, outputs, logs, and execution time.
- **Real-time Updates**: Watch the graph animate as steps execute in real-time.

### 📦 Artifact Inspection
- **Asset Browser**: Browse all generated datasets, models, and metrics.
- **Lineage Tracking**: See exactly which run produced an artifact and which steps consumed it.
- **Preview**: View snippets of dataframes, model summaries, and metric plots directly in the browser.

### 📈 Experiment Tracking
- **Compare Runs**: Select multiple runs to compare their metrics and parameters side-by-side.
- **Metric Plots**: Visualize loss curves, accuracy trends, and other metrics over time.

## Integration with Pipelines 🔌

UniFlow pipelines automatically integrate with the UI when it is running. No special code is required!

### Automatic Registration

When you run a pipeline in your Python script:

```python
from uniflow import Pipeline, step

@step
def my_step():
    return "Hello UniFlow"

pipeline = Pipeline("my_pipeline")
pipeline.add_step(my_step)
pipeline.run()
```

If the UI server is running, the pipeline will automatically:
1.  Register itself with the backend.
2.  Report execution status for each step.
3.  Log artifacts and metrics to the UI.

### Logging Metrics

You can log custom metrics from your steps to appear in the UI:

```python
from uniflow import step, context

@step
def train_model(epochs: int):
    for epoch in range(epochs):
        loss = calculate_loss()
        # Metrics are automatically captured if returned or logged
        # (Future: context.log_metric("loss", loss))
    return {"final_loss": loss}
```

## Troubleshooting 🔧

### UI Not Showing Runs
1.  Ensure the UI server is running: `uniflow ui status`
2.  Check if your pipeline script has access to the `.uniflow` directory.
3.  Verify that `enable_cache` is not preventing re-execution if you expect new runs.

### Port Conflicts
If port 8080 is in use, you can specify a different port:

```bash
uniflow ui start --port 8081
```

## Configuration ⚙️

You can configure UI settings in your `uniflow.yaml` or `pyproject.toml`:

```yaml
# uniflow.yaml
ui:
  host: "0.0.0.0"
  port: 8080
  backend_port: 8000
```

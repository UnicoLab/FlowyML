# Checkpointing & Experiment Tracking 💾

flowyml ensures you never lose progress. Save pipeline state automatically and track every experiment detail.

> [!NOTE]
> **What you'll learn**: How to resume failed pipelines and track model performance over time
>
> **Key insight**: Long-running pipelines *will* fail eventually. Checkpointing turns a catastrophe into a minor annoyance.

## Why Checkpointing Matters

**Without checkpointing**:
- **Lost time**: A crash at hour 9 of a 10-hour job means restarting from hour 0
- **Wasted compute**: Re-computing expensive intermediate steps
- **Frustration**: "It worked on my machine, why did it fail now?"

**With flowyml checkpointing**:
- **Resume instantly**: Restart exactly where it failed
- **Inspect state**: Load the checkpoint to debug what went wrong
- **Skip redundant work**: Re-use successful steps

## 💾 Checkpointing

Checkpointing allows you to save the intermediate results of your pipeline steps. This is crucial for long-running pipelines, as it enables you to resume execution from the point of failure or to skip expensive steps that have already been computed.

### Automatic Checkpointing (Default)

**Checkpointing is enabled by default!** FlowyML automatically saves pipeline state after each step, allowing you to resume from failures without any additional setup.

```python
from flowyml import Pipeline

# Checkpointing is enabled by default
pipeline = Pipeline("heavy_processing")
pipeline.add_step(load_data)
pipeline.add_step(train_model)
pipeline.add_step(evaluate_model)

# 1. Try to run
try:
    result = pipeline.run()
except Exception:
    print("Pipeline crashed! Fix the bug and re-run.")

# 2. Resume automatically on next run
# FlowyML detects the previous run state and resumes from the last successful step
result = pipeline.run()  # Automatically resumes from checkpoint
```

> [!TIP]
> **Pro Tip**: Checkpointing is enabled by default. If you want to disable it for a specific pipeline, use `Pipeline("name", enable_checkpointing=False)`.

> [!TIP]
> **Pro Tip**: Always enable checkpointing for pipelines that take longer than 10 minutes. The storage cost is negligible compared to the compute time saved.

### Manual Checkpointing

For finer control, you can use the `PipelineCheckpoint` object within your steps.

```python
from flowyml import PipelineCheckpoint, step

@step
def train_large_model(data):
    checkpoint = PipelineCheckpoint()

    # Check if we have a saved state
    if checkpoint.exists("model_epoch_5"):
        model = checkpoint.load("model_epoch_5")
        start_epoch = 5
    else:
        model = init_model()
        start_epoch = 0

    for epoch in range(start_epoch, 10):
        train_one_epoch(model, data)
        # Save state
        checkpoint.save(f"model_epoch_{epoch+1}", model)

    return model
```

## 🧪 Experiment Tracking

flowyml **automatically tracks every pipeline run** when you use `Metrics` objects, capturing parameters, metrics, and artifacts. This allows you to compare experiments and reproduce results without any additional setup.

### Automatic Experiment Tracking

**Experiment tracking is enabled by default!** Simply use `Metrics` objects in your pipeline, and flowyml will automatically:

- Extract all metrics from `Metrics` objects
- Capture context parameters (learning_rate, epochs, etc.)
- Log everything to the experiment tracking system
- Create an experiment named after your pipeline

**Example:**
```python
from flowyml import Pipeline, step, context, Metrics

# Define context with parameters
ctx = context(
    learning_rate=0.001,
    batch_size=32,
    epochs=10
)

@step(outputs=["metrics/evaluation"])
def evaluate_model(model):
    """Evaluate the trained model."""
    metrics = {"test_accuracy": 0.93, "test_loss": 0.07}

    # Return Metrics object - automatically logged to experiments!
    return Metrics.create(
        name="example_metrics",
        metrics=metrics,
        metadata={"source": "example"},
    )

pipeline = Pipeline("training_pipeline", context=ctx)
pipeline.add_step(evaluate_model)
result = pipeline.run()

# Metrics are automatically logged! No additional code needed.
```

### Manual Experiment Tracking

If you want more control, you can manually create and manage experiments:

```python
from flowyml import Experiment

# Create experiment
exp = Experiment(
    name="learning_rate_tuning",
    description="Testing different learning rates"
)

# Log a run manually
exp.log_run(
    run_id=result.run_id,
    metrics={"accuracy": 0.95, "loss": 0.05},
    parameters={"learning_rate": 0.001}
)
```

### Comparing Experiments

You can compare runs using the CLI or the Python API.

**CLI:**
```bash
# Compare two specific runs
flowyml experiment compare <run_id_1> <run_id_2>

# List all experiments
flowyml experiment list

# View experiment details
flowyml experiment show <experiment_name>
```

**Python:**
```python
from flowyml import compare_runs, Experiment

# Compare runs using the utility function
diff = compare_runs(["run_1", "run_2"])
print(diff)

# Or use Experiment object
exp = Experiment("training_pipeline")
comparison = exp.compare_runs()
best_run = exp.get_best_run(metric="accuracy", maximize=True)
```

### Disabling Automatic Tracking

If you want to disable automatic experiment tracking:

```python
from flowyml.utils.config import update_config

# Disable auto-logging globally
update_config(auto_log_metrics=False)

# Or disable for a specific pipeline
pipeline = Pipeline("my_pipeline", enable_experiment_tracking=False)
```

### Visualizing Experiments

The flowyml UI provides a dedicated **Experiments** view where you can:
- View a table of all runs
- Filter by parameters or metrics
- Plot metric trends over time
- Compare side-by-side details of selected runs

Access it at `http://localhost:8080/experiments` when the UI is running.

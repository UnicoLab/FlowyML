# Checkpointing & Experiment Tracking 💾

UniFlow provides robust mechanisms to save the state of your pipelines and track your machine learning experiments.

## 💾 Checkpointing

Checkpointing allows you to save the intermediate results of your pipeline steps. This is crucial for long-running pipelines, as it enables you to resume execution from the point of failure or to skip expensive steps that have already been computed.

### Automatic Checkpointing

You can enable automatic checkpointing for a pipeline run. UniFlow will serialize the outputs of each step to the configured artifact store.

```python
from uniflow import Pipeline, checkpoint_enabled_pipeline

pipeline = Pipeline("data_processing")

# Enable checkpointing with a specific run ID
# If a run with this ID exists, it will attempt to resume
pipeline = checkpoint_enabled_pipeline(pipeline, run_id="run_2023_10_27")

pipeline.run()
```

### Manual Checkpointing

For finer control, you can use the `PipelineCheckpoint` object within your steps.

```python
from uniflow import PipelineCheckpoint, step

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

UniFlow automatically tracks every pipeline run, capturing parameters, metrics, and artifacts. This allows you to compare experiments and reproduce results.

### Tracking Metrics

Use the `Metrics` asset to log performance indicators.

```python
from uniflow import step, Metrics

@step(outputs=["metrics"])
def evaluate(model, test_data):
    accuracy = model.score(test_data)
    f1 = f1_score(model, test_data)

    # Create a Metrics object
    return Metrics.create(
        accuracy=accuracy,
        f1_score=f1,
        epoch=10
    )
```

### Comparing Experiments

You can compare runs using the CLI or the Python API.

**CLI:**
```bash
uniflow experiment compare <run_id_1> <run_id_2>
```

**Python:**
```python
from uniflow import compare_runs

diff = compare_runs(["run_1", "run_2"])
print(diff)
```

### Visualizing Experiments

The UniFlow UI provides a dedicated **Experiments** view where you can:
- View a table of all runs.
- Filter by parameters or metrics.
- Plot metric trends over time.
- Compare side-by-side details of selected runs.

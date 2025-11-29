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

### Real-World Pattern: The "Resume" Workflow

Crash-proof your long-running pipelines.

```python
from flowyml import Pipeline, checkpoint_enabled_pipeline

pipeline = Pipeline("heavy_processing")

# 1. Try to run
try:
    pipeline.run()
except Exception:
    print("Pipeline crashed! Fix the bug and re-run.")

# 2. Resume later (e.g., in a new script or after fix)
# flowyml detects the previous run state and resumes
pipeline = checkpoint_enabled_pipeline(pipeline, run_id="run_2023_10_27")
pipeline.run()
```

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

flowyml automatically tracks every pipeline run, capturing parameters, metrics, and artifacts. This allows you to compare experiments and reproduce results.

### Tracking Metrics

Use the `Metrics` asset to log performance indicators.

```python
from flowyml import step, Metrics

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
flowyml experiment compare <run_id_1> <run_id_2>
```

**Python:**
```python
from flowyml import compare_runs

diff = compare_runs(["run_1", "run_2"])
print(diff)
```

### Visualizing Experiments

The flowyml UI provides a dedicated **Experiments** view where you can:
- View a table of all runs.
- Filter by parameters or metrics.
- Plot metric trends over time.
- Compare side-by-side details of selected runs.

# Model Leaderboard 🏆

Track and compare the performance of your models across different runs and experiments.

## 🏆 Using the Leaderboard

The `ModelLeaderboard` class allows you to rank models based on specific metrics.

```python
from uniflow.tracking import ModelLeaderboard

# Initialize leaderboard for 'accuracy'
leaderboard = ModelLeaderboard(metric="accuracy", higher_is_better=True)

# Add a score from a run
leaderboard.add_score(
    model_name="resnet50",
    run_id="run_123",
    score=0.95,
    metadata={"epochs": 10}
)

# Display top models
leaderboard.display(n=5)
```

## 📊 Comparison

You can also compare specific runs side-by-side.

```python
from uniflow.tracking import compare_runs

diff = compare_runs(["run_1", "run_2"])
print(diff)
```

## 🖥️ UI View

The UniFlow Dashboard provides a rich interactive leaderboard where you can:
- Sort by any metric.
- Filter by tags or date.
- Click to see detailed run configuration.

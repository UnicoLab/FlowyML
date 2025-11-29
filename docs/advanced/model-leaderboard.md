# Model Leaderboard 🏆

flowyml automatically tracks and ranks your models, so you always know which one performs best.

> [!NOTE]
> **What you'll learn**: How to compare models across experiments and automatically pick the winner
>
> **Key insight**: Don't track model performance in spreadsheets. Let the framework do it.

## Why Leaderboards Matter

**Without a leaderboard**:
- **Manual tracking**: "Was run_42 better than run_38?"
- **Lost history**: "What hyperparameters did we use for the best model last month?"
- **Subjective choices**: Picking models based on gut feeling rather than metrics

**With flowyml leaderboard**:
- **Automated ranking**: Always know the SOTA model for your task
- **Metric-driven**: Compare on accuracy, F1, latency, or custom metrics
- **Full lineage**: Click any score to see the exact code and data that produced it

## 🏆 Using the Leaderboard

The `ModelLeaderboard` class allows you to rank models based on specific metrics.

```python
from flowyml.tracking import ModelLeaderboard

# Initialize leaderboard for 'accuracy'
leaderboard = ModelLeaderboard(metric="accuracy", higher_is_better=True)

# Add a score from a run
leaderboard.add_score(
    model_name="resnet50",
    run_id="run_123",
    score=0.95,
    metadata={"epochs": 10}
)

## Real-World Pattern: Auto-Promotion

Automatically fetch the best model from history to use as a baseline or for deployment.

```python
from flowyml.tracking import ModelLeaderboard

# 1. Get the current champion
leaderboard = ModelLeaderboard(metric="accuracy")
best_run = leaderboard.get_best_run()

print(f"Current Champion: {best_run.run_id} (Acc: {best_run.score:.4f})")

# 2. Compare with new candidate
if new_model_score > best_run.score:
    print("🚀 New Champion! Promoting to production...")
    deploy(new_model)
else:
    print("❌ Failed to beat baseline.")
```

## 📊 Comparison

You can also compare specific runs side-by-side.

```python
from flowyml.tracking import compare_runs

diff = compare_runs(["run_1", "run_2"])
print(diff)
```

## 🖥️ UI View

The flowyml Dashboard provides a rich interactive leaderboard where you can:
- Sort by any metric.
- Filter by tags or date.
- Click to see detailed run configuration.

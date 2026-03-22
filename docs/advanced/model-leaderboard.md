# 🏆 Model Leaderboard

!!! info "What you'll learn"
    How to compare models across experiments and automatically pick the winner. Don't track model performance in spreadsheets — let the framework do it.

FlowyML automatically tracks and ranks your models, so you always know which one performs best — across experiments, teams, and time.

---

## Why Leaderboards Matter 🤔

| Without a Leaderboard | With Model Leaderboard |
|---|---|
| "Was run_42 better than run_38?" | Automated rankings by any metric |
| "What hyperparameters did we use?" | Full lineage: click any score to see the run |
| Picking models on gut feeling | Metric-driven, reproducible decisions |
| Spreadsheets and notebooks | Centralized, always up-to-date |

---

## 🏆 Basic Usage

```python
from flowyml.tracking import ModelLeaderboard

# Initialize leaderboard for a specific metric
leaderboard = ModelLeaderboard(metric="accuracy", higher_is_better=True)

# Add scores from training runs
leaderboard.add_score(
    model_name="resnet50",
    run_id="run_123",
    score=0.95,
    metadata={"epochs": 10, "lr": 0.001},
)

leaderboard.add_score(
    model_name="efficientnet",
    run_id="run_124",
    score=0.97,
    metadata={"epochs": 20, "lr": 0.0005},
)

leaderboard.add_score(
    model_name="vit_base",
    run_id="run_125",
    score=0.93,
    metadata={"epochs": 15, "lr": 0.001},
)
```

---

## 📊 Querying the Leaderboard

```python
# Get the current champion
best = leaderboard.get_best_run()
print(f"🏆 Champion: {best.model_name} (Acc: {best.score:.4f}, Run: {best.run_id})")

# Get top N models
top_3 = leaderboard.get_top(n=3)
for rank, entry in enumerate(top_3, 1):
    print(f"  #{rank} {entry.model_name}: {entry.score:.4f}")

# Get full rankings
rankings = leaderboard.rankings
```

---

## 🚀 Auto-Promotion Pattern

Automatically promote the best model to production:

```python
from flowyml.tracking import ModelLeaderboard

leaderboard = ModelLeaderboard(metric="accuracy")

# After training a new model
new_score = evaluate_model(new_model)
leaderboard.add_score("new_model", run_id="run_200", score=new_score)

# Compare against current champion
best = leaderboard.get_best_run()

if new_score > best.score:
    print(f"🚀 New Champion! {new_score:.4f} > {best.score:.4f}")
    deploy_to_production(new_model)
else:
    print(f"❌ Failed to beat baseline ({best.score:.4f})")
```

---

## Run Comparison 🔍

Compare specific runs side-by-side:

```python
from flowyml.tracking import compare_runs

diff = compare_runs(["run_123", "run_124"])
print(diff)
# Shows metric differences, config changes, and delta analysis
```

### What `compare_runs` Shows

| Field | Description |
|---|---|
| Metric deltas | Difference in each tracked metric |
| Config diff | Hyperparameter changes between runs |
| Timing | Training duration comparison |
| Data version | Dataset versions used |

---

## 🖥️ Dashboard View

The FlowyML Dashboard provides an interactive leaderboard where you can:

- **Sort by any metric** — accuracy, F1, loss, latency, cost
- **Filter by tags** — model type, team, date range
- **Click to inspect** — see full run config, training curves, and artifacts
- **Compare side-by-side** — select runs and view metric deltas

---

## Real-World Example: Multi-Metric Leaderboard 🌍

```python
from flowyml.tracking import ModelLeaderboard

# Track multiple metrics
accuracy_board = ModelLeaderboard(metric="accuracy", higher_is_better=True)
latency_board = ModelLeaderboard(metric="latency_ms", higher_is_better=False)

# After each training run
accuracy_board.add_score("model_v3", run_id="run_300", score=0.96)
latency_board.add_score("model_v3", run_id="run_300", score=45.2)

# Find best accuracy
best_accuracy = accuracy_board.get_best_run()

# Find fastest model
fastest = latency_board.get_best_run()

# Find best trade-off (manual Pareto analysis)
print(f"Best accuracy: {best_accuracy.model_name} ({best_accuracy.score:.4f})")
print(f"Fastest: {fastest.model_name} ({fastest.score:.1f}ms)")
```

---

## Best Practices 💡

!!! tip "One leaderboard per metric"
    Create separate leaderboards for different metrics — what's "best" depends on the metric you're optimizing.

!!! tip "Always record metadata"
    Pass `metadata={"epochs": 10, "lr": 0.001}` when adding scores. This makes it easy to reproduce the winning configuration.

!!! warning "Beware overfitting to the leaderboard"
    If you keep comparing against the same test set, you risk overfitting. Rotate your golden set periodically.

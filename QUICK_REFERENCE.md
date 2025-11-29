# 🌊 flowyml - Quick Reference Guide

## New Features Overview

### 1️⃣ **GenAI & LLM Monitoring**

Track LLM calls, tokens, and costs automatically:

```python
from flowyml import trace_llm

@trace_llm(name="summarize")
def generate_summary(text):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Summarize: {text}"}]
    )
    return response.choices[0].message.content

# Traces are automatically saved
result = generate_summary("Long text here...")
```

**Features:**
- Automatic input/output capture
- Token usage tracking
- Cost calculation
- Parent-child trace relationships
- View traces in UI at `/api/traces`

---

### 2️⃣ **Keras Integration**

Automatic experiment tracking for Keras models:

```python
from flowyml import flowymlKerasCallback

model.fit(
    x_train, y_train,
    epochs=10,
    callbacks=[
        flowymlKerasCallback(
            experiment_name="mnist_training",
            run_name="baseline_v1",
            log_model=True
        )
    ]
)
```

**Auto-logs:**
- Training metrics (loss, accuracy, etc.)
- Model architecture & summary
- Optimizer configuration
- Training parameters
- Model checkpoints

---

### 3️⃣ **Data Drift Detection**

Monitor data distribution shifts:

```python
from flowyml import detect_drift, compute_stats

# Detect drift
drift_result = detect_drift(
    reference_data=train_data['feature'],
    current_data=prod_data['feature'],
    threshold=0.1  # PSI threshold
)

if drift_result['drift_detected']:
    print(f"⚠️ Drift detected! PSI: {drift_result['psi']:.4f}")

# Compute stats
stats = compute_stats(data)
print(f"Mean: {stats['mean']}, Std: {stats['std']}")
```

---

### 4️⃣ **Pipeline Scheduling**

Run pipelines automatically on a schedule:

```python
from flowyml import PipelineScheduler

scheduler = PipelineScheduler()

# Daily at 2am
scheduler.schedule_daily(
    name="daily_training",
    pipeline_func=lambda: my_pipeline.run(),
    hour=2, minute=0
)

# Every 6 hours
scheduler.schedule_interval(
    name="data_refresh",
    pipeline_func=lambda: refresh_pipeline.run(),
    hours=6
)

# Start scheduler
scheduler.start()  # Non-blocking
# scheduler.start(blocking=True)  # Blocking
```

---

### 5️⃣ **Notifications**

Get notified about pipeline events:

```python
from flowyml import configure_notifications, get_notifier

# Configure channels
configure_notifications(
    console=True,
    slack_webhook="https://hooks.slack.com/...",
    email_config={
        'smtp_host': 'smtp.gmail.com',
        'username': 'you@gmail.com',
        'password': 'your-password',
        'from_addr': 'you@gmail.com',
        'to_addrs': ['team@company.com']
    }
)

# Use in your code
notifier = get_notifier()
notifier.notify(
    title="Training Complete",
    message="Model achieved 95% accuracy",
    level="success"
)

# Or use event hooks
notifier.on_pipeline_success(pipeline.name, run_id, duration)
notifier.on_pipeline_failure(pipeline.name, run_id, error)
notifier.on_drift_detected(feature_name, psi_value)
```

---

### 6️⃣ **Model Leaderboard**

Compare and rank models:

```python
from flowyml import ModelLeaderboard

leaderboard = ModelLeaderboard(
    metric="accuracy",
    higher_is_better=True
)

# Add scores
leaderboard.add_score("bert-base", run_id="run_123", score=0.92)
leaderboard.add_score("distilbert", run_id="run_124", score=0.89)

# Display rankings
leaderboard.display(n=10)

# Get top models
top_5 = leaderboard.get_top(n=5)
```

**Compare multiple runs:**

```python
from flowyml import compare_runs

comparison = compare_runs(
    run_ids=["run_123", "run_124", "run_125"],
    metrics=["accuracy", "f1_score", "latency"]
)
```

---

### 7️⃣ **Pipeline Templates**

Create pipelines from pre-built templates:

```python
from flowyml import create_from_template, list_templates

# See available templates
print(list_templates())  # ['ml_training', 'etl', 'ab_test']

# Create from template
pipeline = create_from_template(
    'ml_training',
    name='my_training',
    data_loader=load_data,
    preprocessor=preprocess,
    trainer=train_model,
    evaluator=evaluate,
    model_saver=save_model
)

# Run it
result = pipeline.run()
```

**Available Templates:**
- `ml_training`: Standard ML training workflow
- `etl` / `data_pipeline`: Extract-Transform-Load
- `ab_test`: A/B testing with model comparison

---

### 8️⃣ **Checkpointing**

Resume failed pipelines:

```python
from flowyml import PipelineCheckpoint

checkpoint = PipelineCheckpoint(run_id="run_123")

# In your step
def expensive_computation():
    result = do_work()
    checkpoint.save_step_state("compute", result)
    return result

# Resume later
if checkpoint.exists():
    state = checkpoint.load()
    last_step = state['last_completed_step']
    output = checkpoint.load_step_state(last_step)
```

---

### 9️⃣ **Human-in-the-Loop**

Add approval gates to pipelines:

```python
from flowyml import approval, Pipeline

pipeline = Pipeline("sensitive_operation")

# Add approval step
approval_step = approval(
    name="approve_deployment",
    approver="data-team",
    timeout_seconds=3600,
    auto_approve_if=lambda: os.getenv("AUTO_APPROVE") == "true"
)

pipeline.add_step(approval_step)
```

---

## 📊 UI Features

Access the web UI at `http://localhost:8080`:

- **Dashboard**: Overview stats
- **Runs**: Pipeline execution history
- **Pipelines**: All registered pipelines
- **Assets**: Browse artifacts
- **Experiments**: Compare experiment runs
- **Traces**: View LLM call traces (NEW!)

---

## 🎯 Quick Start Example

Complete example using multiple features:

```python
from flowyml import (
    Pipeline, step, context,
    configure_notifications,
    PipelineScheduler,
    ModelLeaderboard,
    flowymlKerasCallback
)

# 1. Configure notifications
configure_notifications(console=True)

# 2. Define pipeline
ctx = context(epochs=10, batch_size=32)
pipeline = Pipeline("training", context=ctx)

@step(outputs=["model", "metrics"])
def train(epochs: int, batch_size: int):
    model = create_model()
    history = model.fit(
        x_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[flowymlKerasCallback("mnist_exp")]
    )
    return model, history.history

pipeline.add_step(train)

# 3. Add to leaderboard
leaderboard = ModelLeaderboard("val_accuracy")

@step(inputs=["metrics"])
def log_to_leaderboard(metrics):
    accuracy = metrics['val_accuracy'][-1]
    leaderboard.add_score("my_model", run_id="...", score=accuracy)

pipeline.add_step(log_to_leaderboard)

# 4. Schedule to run daily
scheduler = PipelineScheduler()
scheduler.schedule_daily(
    name="daily_training",
    pipeline_func=lambda: pipeline.run(),
    hour=2
)
scheduler.start()
```

---

## 📚 Additional Resources

- Full documentation: `/docs`
- API Reference: `/api/docs` (when server is running)
- Examples: `/examples`
- Roadmap: `ROADMAP.md`

---

**Happy MLOps! 🌊**

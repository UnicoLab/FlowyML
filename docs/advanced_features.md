# Advanced Features Guide

## ⚡ Step Grouping

Group consecutive pipeline steps to execute in the same container/environment, reducing overhead while maintaining clear step boundaries.

### Basic Usage

```python
from flowyml import Pipeline, step
from flowyml.core.resources import ResourceRequirements, GPUConfig

# Group preprocessing steps
@step(outputs=["raw_data"], execution_group="preprocessing")
def load_data():
    return fetch_from_source()

@step(inputs=["raw_data"], outputs=["clean_data"], execution_group="preprocessing")
def clean_data(raw_data):
    return preprocess(raw_data)

@step(inputs=["clean_data"], outputs=["features"], execution_group="preprocessing")
def extract_features(clean_data):
    return transform(clean_data)

pipeline = Pipeline("data_pipeline")
pipeline.add_step(load_data)
pipeline.add_step(clean_data)
pipeline.add_step(extract_features)

result = pipeline.run()
# All three steps run in the same container
```

### Resource Aggregation

When steps are grouped, flowyml automatically aggregates their resource requirements:

```python
@step(
    outputs=["data"],
    execution_group="training",
    resources=ResourceRequirements(cpu="2", memory="4Gi")
)
def prepare_data():
    return "data"

@step(
    inputs=["data"],
    outputs=["model"],
    execution_group="training",
    resources=ResourceRequirements(
        cpu="8",
        memory="16Gi",
        gpu=GPUConfig(gpu_type="nvidia-a100", count=2)
    )
)
def train_model(data):
    return "model"

# Group executes with: cpu="8", memory="16Gi", gpu=2x A100 (max of all)
```

**Aggregation Strategy:**
- **CPU/Memory**: Maximum across all steps
- **GPU**: Maximum count, best GPU type (A100 > V100 > T4)
- **Storage**: Maximum across all steps

### Smart Sequential Analysis

flowyml only groups steps that can execute consecutively in the DAG:

```python
# Consecutive: A → B → C (all in "group1")
# Result: Single group with all three steps ✅

# Non-consecutive: A ("group1") → X (no group) → B ("group1")
# Result: A and B run separately (not consecutive) ✅
```

### Inspection

After building, inspect created groups:

```python
pipeline.build()

for group in pipeline.step_groups:
    print(f"Group: {group.group_name}")
    print(f"  Steps: {[s.name for s in group.steps]}")
    print(f"  Resources: CPU={group.aggregated_resources.cpu}")
```

See [Step Grouping Guide](step-grouping.md) for complete documentation.

---

## 🤖 GenAI & LLM Monitoring

### LLM Call Tracing

flowyml provides built-in tracing for LLM calls, allowing you to monitor token usage, costs, and execution traces.

#### Basic Usage

```python
from flowyml import trace_llm

@trace_llm(name="text_generation")
def generate_text(prompt: str):
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Automatically traced
result = generate_text("Write a haiku about ML")
```

#### Nested Traces

```python
from flowyml import trace_llm, tracer

@trace_llm(name="rag_pipeline", event_type="chain")
def rag_pipeline(query: str):
    # Child trace 1
    context = retrieve_context(query)
    # Child trace 2
    answer = generate_answer(query, context)
    return answer

@trace_llm(name="retrieval", event_type="tool")
def retrieve_context(query: str):
    # Your retrieval logic
    return context

@trace_llm(name="generation", event_type="llm")
def generate_answer(query: str, context: str):
    # Your generation logic
    return answer
```

#### Viewing Traces

Traces are automatically saved to the metadata store and can be viewed via:

1. **Python API:**
```python
from flowyml.storage.metadata import SQLiteMetadataStore

store = SQLiteMetadataStore()
trace_events = store.get_trace(trace_id="...")
```

2. **Web UI:**
Navigate to `http://localhost:8080/api/traces` to see all traces.

---

## 🔔 Notification System

### Setup Notifications

```python
from flowyml import configure_notifications

configure_notifications(
    console=True,
    slack_webhook="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    email_config={
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': 'your-email@gmail.com',
        'password': 'your-app-password',
        'from_addr': 'your-email@gmail.com',
        'to_addrs': ['team@company.com']
    }
)
```

### Using Notifications

```python
from flowyml import get_notifier

notifier = get_notifier()

# Manual notifications
notifier.notify(
    title="Model Training Complete",
    message="Accuracy: 95.2%",
    level="success"  # 'info', 'warning', 'error', 'success'
)

# Event-based notifications
notifier.on_pipeline_start("training_pipeline", run_id)
notifier.on_pipeline_success("training_pipeline", run_id, duration=120.5)
notifier.on_pipeline_failure("training_pipeline", run_id, error="Out of memory")
notifier.on_drift_detected("user_age", psi=0.25)
```

### Custom Notification Channels

```python
from flowyml import NotificationManager, NotificationChannel, Notification

class CustomNotifier(NotificationChannel):
    def send(self, notification: Notification) -> bool:
        # Your custom logic (e.g., Discord, Teams, PagerDuty)
        return True

manager = NotificationManager()
manager.add_channel(CustomNotifier())
```

---

## 📅 Pipeline Scheduling

### Schedule Pipelines

```python
from flowyml import PipelineScheduler, Pipeline

scheduler = PipelineScheduler()

# Create your pipeline
pipeline = Pipeline("daily_training")
# ... add steps ...

# Schedule daily at 2:00 AM
scheduler.schedule_daily(
    name="daily_training",
    pipeline_func=lambda: pipeline.run(),
    hour=2,
    minute=0
)

# Schedule every 6 hours
scheduler.schedule_interval(
    name="data_refresh",
    pipeline_func=lambda: refresh_pipeline.run(),
    hours=6
)

# Schedule hourly at :15
scheduler.schedule_hourly(
    name="hourly_check",
    pipeline_func=lambda: check_pipeline.run(),
    minute=15
)

# Start the scheduler
scheduler.start()  # Non-blocking (daemon thread)

# Or run blocking
# scheduler.start(blocking=True)
```

### Managing Schedules

```python
# List all schedules
scheduler.list_schedules()

# Disable a schedule
scheduler.disable("daily_training")

# Enable a schedule
scheduler.enable("daily_training")

# Remove a schedule
scheduler.unschedule("daily_training")

# Stop the scheduler
scheduler.stop()
```

---

## 🏆 Model Leaderboard

### Track Model Performance

```python
from flowyml import ModelLeaderboard

# Create leaderboard for a metric
leaderboard = ModelLeaderboard(
    metric="accuracy",
    higher_is_better=True
)

# Add model scores
leaderboard.add_score(
    model_name="bert-base-uncased",
    run_id="run_123",
    score=0.92,
    metadata={"epochs": 10, "learning_rate": 0.001}
)

leaderboard.add_score(
    model_name="distilbert-base",
    run_id="run_124",
    score=0.89
)

# Display rankings
leaderboard.display(n=10)
```

**Output:**
```
🏆 Model Leaderboard - accuracy
================================================================================
Rank   Model Name                     Score           Run ID
--------------------------------------------------------------------------------
1      bert-base-uncased              0.9200          run_123
2      distilbert-base                0.8900          run_124
================================================================================
```

### Compare Runs

```python
from flowyml import compare_runs

comparison = compare_runs(
    run_ids=["run_123", "run_124", "run_125"],
    metrics=["accuracy", "f1_score", "precision", "recall"]
)

print(comparison)
```

---

## 📦 Pipeline Templates

### Using Templates

```python
from flowyml import create_from_template, list_templates

# See available templates
templates = list_templates()
print(templates)  # ['ml_training', 'etl', 'data_pipeline', 'ab_test']

# Create ML training pipeline
pipeline = create_from_template(
    'ml_training',
    name='my_training_pipeline',
    data_loader=load_data,
    preprocessor=preprocess_data,
    trainer=train_model,
    evaluator=evaluate_model,
    model_saver=save_model
)

result = pipeline.run()
```

### Available Templates

#### 1. ML Training Template
```python
pipeline = create_from_template(
    'ml_training',
    data_loader=lambda: load_dataset(),
    preprocessor=lambda dataset: preprocess(dataset),
    trainer=lambda processed_data: train(processed_data),
    evaluator=lambda model, data: evaluate(model, data),
    model_saver=lambda model: save(model)
)
```

#### 2. ETL Template
```python
pipeline = create_from_template(
    'etl',
    extractor=lambda: extract_from_db(),
    transformer=lambda raw_data: transform(raw_data),
    loader=lambda transformed_data: load_to_warehouse(transformed_data)
)
```

#### 3. A/B Test Template
```python
pipeline = create_from_template(
    'ab_test',
    data_loader=lambda: load_test_data(),
    model_a_trainer=lambda data: train_variant_a(data),
    model_b_trainer=lambda data: train_variant_b(data),
    comparator=lambda metrics_a, metrics_b: compare(metrics_a, metrics_b)
)
```

---

## 💾 Checkpointing

### Enable Checkpointing

```python
from flowyml import PipelineCheckpoint

checkpoint = PipelineCheckpoint(run_id="my_run_123")

# Save state after expensive computation
@step(outputs=["processed_data"])
def expensive_preprocessing():
    data = do_expensive_work()
    checkpoint.save_step_state("preprocessing", data)
    return data

# Check if checkpoint exists
if checkpoint.exists():
    resume_point = checkpoint.resume_point()
    print(f"Can resume from: {resume_point}")

    # Load previous state
    state = checkpoint.load_step_state("preprocessing")
```

### Wrapper for Automatic Checkpointing

```python
from flowyml import checkpoint_enabled_pipeline

pipeline = Pipeline("training")
# ... add steps ...

# Enable checkpointing
pipeline = checkpoint_enabled_pipeline(pipeline, run_id="run_123")

# Run will now prompt to resume if checkpoint exists
result = pipeline.run()
```

---

## 👤 Human-in-the-Loop

### Approval Steps

```python
from flowyml import Pipeline, step, approval

pipeline = Pipeline("deployment")

@step(outputs=["model"])
def train_model():
    # Training logic
    return model

# Add approval gate
approval_step = approval(
    name="approve_deployment",
    approver="ml-team",
    timeout_seconds=3600,
    auto_approve_if=lambda: os.getenv("CI") == "true"
)

pipeline.add_step(train_model)
pipeline.add_step(approval_step)

@step(inputs=["model"])
def deploy_model(model):
    # Deployment logic
    pass

pipeline.add_step(deploy_model)
```

When run interactively:
```
✋ Step 'approve_deployment' requires approval.
   Waiting for approval from: ml-team
   Timeout: 3600s
   Approve execution? [y/N]: y
✅ Approved.
```

---

## 🧪 Keras Integration

### Automatic Experiment Tracking

```python
from flowyml import flowymlKerasCallback
import tensorflow as tf

model = tf.keras.Sequential([...])
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy')

# Add flowyml callback
model.fit(
    x_train, y_train,
    epochs=10,
    validation_data=(x_val, y_val),
    callbacks=[
        flowymlKerasCallback(
            experiment_name="mnist_classification",
            run_name="baseline_v1",
            log_model=True,
            log_every_epoch=True
        )
    ]
)
```

**Automatically logs:**
- Training and validation metrics
- Model architecture
- Optimizer configuration
- Training parameters (epochs, batch size)
- Model checkpoints (if `log_model=True`)

---

## 📊 Data Drift Detection

### Monitor Distribution Shifts

```python
from flowyml import detect_drift, compute_stats

# Training data (reference)
train_feature = train_df['age'].values

# Production data (current)
prod_feature = prod_df['age'].values

# Detect drift
drift_result = detect_drift(
    reference_data=train_feature,
    current_data=prod_feature,
    threshold=0.1  # PSI threshold
)

if drift_result['drift_detected']:
    print(f"⚠️ Drift detected!")
    print(f"PSI: {drift_result['psi']:.4f}")
    print(f"Reference stats: {drift_result['reference_stats']}")
    print(f"Current stats: {drift_result['current_stats']}")

    # Send notification
    from flowyml import get_notifier
    notifier = get_notifier()
    notifier.on_drift_detected('age', drift_result['psi'])
```

### Compute Statistics

```python
from flowyml import compute_stats

stats = compute_stats(data_array)
print(stats)
```

**Output:**
```python
{
    'count': 10000,
    'mean': 35.2,
    'std': 12.5,
    'min': 18.0,
    'max': 85.0,
    'median': 34.0,
    'q25': 26.0,
    'q75': 45.0
}
```

---

## 🔗 Integration Examples

### Complete Example

```python
from flowyml import (
    Pipeline, step, context,
    configure_notifications,
    PipelineScheduler,
    ModelLeaderboard,
    detect_drift,
    get_notifier
)

# 1. Setup notifications
configure_notifications(console=True, slack_webhook="...")

# 2. Create pipeline
ctx = context(model_type="random_forest", n_estimators=100)
pipeline = Pipeline("production_training", context=ctx)

@step(outputs=["train_data", "val_data"])
def load_and_validate():
    train = load_training_data()
    val = load_validation_data()

    # Check for drift
    drift = detect_drift(historical_data, train)
    if drift['drift_detected']:
        get_notifier().on_drift_detected('features', drift['psi'])

    return train, val

@step(inputs=["train_data"], outputs=["model"])
def train_model(train_data, model_type: str, n_estimators: int):
    model = RandomForestClassifier(n_estimators=n_estimators)
    model.fit(train_data.X, train_data.y)
    return model

@step(inputs=["model", "val_data"], outputs=["metrics"])
def evaluate(model, val_data):
    predictions = model.predict(val_data.X)
    accuracy = accuracy_score(val_data.y, predictions)
    return {"accuracy": accuracy}

pipeline.add_step(load_and_validate)
pipeline.add_step(train_model)
pipeline.add_step(evaluate)

# 3. Schedule daily training
scheduler = PipelineScheduler()
scheduler.schedule_daily(
    name="daily_retrain",
    pipeline_func=lambda: pipeline.run(),
    hour=2
)
scheduler.start()

# 4. Track on leaderboard
leaderboard = ModelLeaderboard("accuracy")
# After each run, add to leaderboard
```

---

For more examples, see the `/examples` directory in the repository.

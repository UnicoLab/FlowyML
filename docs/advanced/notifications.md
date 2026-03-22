# 🔔 Notifications & Alerts

!!! info "What you'll learn"
    How to set up proactive alerts so you don't have to watch dashboards all day. The faster you know about a failure, the faster you can fix it.

Know immediately when pipelines succeed, fail, or detect issues — via Slack, email, or custom channels.

---

## Why Alerts Matter ⚠️

| Without Alerts | With FlowyML Alerts |
|---|---|
| Silent failures go unnoticed for hours | Instant Slack ping on exception |
| Constantly refreshing dashboards | Proactive notifications |
| Generic "something failed" messages | Contextual: "Pipeline X failed at step Y with error Z" |

---

## 🔔 Configuration

Configure notification channels globally — all pipelines will use them:

```python
from flowyml import configure_notifications

configure_notifications(
    console=True,                  # Always log to console
    slack_webhook="https://hooks.slack.com/services/...",
    email_config={
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "alerts@example.com",
        "password": "app-password",
        "to_addrs": ["team@example.com"],
    },
)
```

### Available Channels

| Channel | Class | Setup |
|---|---|---|
| Console | `ConsoleNotifier` | Always enabled |
| Slack | `SlackNotifier` | `slack_webhook` URL |
| Email | `EmailNotifier` | `email_config` dict |
| Custom | Your subclass | See below |

---

## 📨 Sending Notifications

Send notifications from any step using `get_notifier()`:

```python
from flowyml import step, get_notifier

@step
def notify_success(metrics):
    notifier = get_notifier()
    notifier.notify(
        title="🚀 Model Training Complete",
        message=f"New model ready!\nAccuracy: {metrics['acc']:.2%}\nF1: {metrics['f1']:.2f}",
        level="success",
        channels=["slack"],
    )
```

### Notification Levels

| Level | Use Case | Slack Color |
|---|---|---|
| `"info"` | Informational updates | Blue |
| `"success"` | Pipeline completed successfully | Green |
| `"warning"` | Non-fatal issues (drift, degradation) | Yellow |
| `"error"` | Step or pipeline failure | Red |

---

## 🚨 Event Hooks

Automatically trigger notifications on specific pipeline events:

```python
from flowyml import get_notifier

notifier = get_notifier()

# Pipeline failure alert
notifier.on_pipeline_failure("training_pipeline", run_id="run-123", error="OOM")

# Drift detection alert
notifier.on_drift_detected("feature_age", psi=0.45)

# Model promotion alert
notifier.on_model_promoted("fraud_detector_v3", stage="production")
```

---

## 🛠 Custom Channels

Implement `NotificationChannel` to support any service (Discord, PagerDuty, Teams, etc.):

```python
from flowyml.monitoring.notifications import NotificationChannel, Notification
import requests

class DiscordChannel(NotificationChannel):
    """Send notifications to a Discord webhook."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, notification: Notification) -> bool:
        payload = {
            "content": f"**{notification.title}**\n{notification.message}",
        }
        resp = requests.post(self.webhook_url, json=payload)
        return resp.status_code == 204

class PagerDutyChannel(NotificationChannel):
    """Trigger PagerDuty incidents for critical alerts."""

    def __init__(self, routing_key: str):
        self.routing_key = routing_key

    def send(self, notification: Notification) -> bool:
        if notification.level != "error":
            return True  # Only page for errors
        # Create PagerDuty event...
        return True
```

---

## Real-World Example: Full Alert Pipeline 🌍

```python
from flowyml import Pipeline, step, get_notifier, configure_notifications

# Configure channels
configure_notifications(
    slack_webhook="https://hooks.slack.com/services/...",
)

pipeline = Pipeline("monitored_training")

@step
def train_model():
    return {"accuracy": 0.95, "f1": 0.92}

@step
def send_results(metrics):
    notifier = get_notifier()

    if metrics["accuracy"] > 0.9:
        notifier.notify(
            title="✅ Training Passed",
            message=f"Accuracy: {metrics['accuracy']:.2%}",
            level="success",
            channels=["slack"],
        )
    else:
        notifier.notify(
            title="❌ Training Failed Quality Gate",
            message=f"Accuracy: {metrics['accuracy']:.2%} (min: 90%)",
            level="error",
            channels=["slack", "email"],
        )

pipeline.add_step(train_model)
pipeline.add_step(send_results)
```

---

## Best Practices 💡

!!! tip "Channel selection"
    Use Slack for real-time alerts, email for daily summaries, and PagerDuty only for production-critical failures.

!!! tip "Don't over-alert"
    Send `"success"` notifications only for long-running jobs. Alert fatigue is worse than no alerts.

!!! warning "Webhook security"
    Store Slack webhook URLs in environment variables, not in code. Use `os.getenv("SLACK_WEBHOOK")`.

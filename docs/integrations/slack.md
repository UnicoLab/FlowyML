# 💬 Slack Integration

!!! info "What you'll learn"
    How to send pipeline alerts to Slack channels — don't watch the terminal, let the bot tell you when it's done.

Get notified where you work. Receive alerts for pipeline successes, failures, and approval requests directly in Slack.

---

## Why Slack Alerts?

| Feature | Benefit |
|---|---|
| **Real-time** | Know immediately when a production job fails |
| **Visibility** | Keep the whole team in the loop |
| **Actionable** | Links to logs and dashboards in the message |
| **Low friction** | No context switching — alerts come to you |

---

## 💬 Setup

### 1. Create a Slack Webhook

1. Go to [Slack API: Incoming Webhooks](https://api.slack.com/messaging/webhooks)
2. Create a new app or use an existing one
3. Enable **Incoming Webhooks** and generate a webhook URL
4. Copy the URL (format: `https://hooks.slack.com/services/T.../B.../...`)

### 2. Configure FlowyML

```python
from flowyml import configure_notifications

configure_notifications(
    slack_webhook="https://hooks.slack.com/services/T000/B000/XXXX",
)
```

Or via environment variable:

```bash
export FLOWYML_SLACK_WEBHOOK=https://hooks.slack.com/services/T000/B000/XXXX
```

---

## 🔔 Sending Alerts

### From Steps

```python
from flowyml import get_notifier, step

@step
def notify_team(metrics):
    get_notifier().notify(
        title="🚀 Training Finished",
        message=f"Accuracy: {metrics['acc']:.2%}\nF1: {metrics['f1']:.2f}",
        level="success",
        channels=["slack"],
    )
```

### On Failure (Automatic)

```python
from flowyml import step, on_failure

@step(
    on_failure=on_failure(
        action="slack",
        recipients=["#ml-ops"],
        include_logs=True,
    )
)
def critical_step():
    """Automatically sends a Slack alert with logs if this step fails."""
    return train_model()
```

---

## Alert Levels

| Level | Slack Color | Use Case |
|---|---|---|
| `"info"` | Blue | Pipeline started, progress updates |
| `"success"` | Green | Training complete, deployment successful |
| `"warning"` | Yellow | Drift detected, degraded performance |
| `"error"` | Red | Step failure, pipeline crash |

---

## Best Practices

!!! tip "Channel strategy"
    Use `#ml-ops` for all alerts, `#ml-alerts-critical` for errors only. Avoid sending success messages to high-traffic channels.

!!! warning "Webhook security"
    Store webhook URLs in environment variables or secrets — never hardcode them in source code.

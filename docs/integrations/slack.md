# Slack Integration 💬

Get notified where you work. Receive alerts for pipeline successes, failures, and approvals.

> [!NOTE]
> **What you'll learn**: How to send pipeline alerts to Slack channels
>
> **Key insight**: Don't watch the terminal. Let the bot tell you when it's done.

## Why Slack Alerts?

- **Real-time**: Know immediately when a production job fails.
- **Visibility**: Keep the whole team in the loop.
- **Actionable**: Links to logs and dashboards directly in the message.

## 💬 Configuration

1. Create a Slack App and get a Webhook URL.
2. Configure flowyml to use it.

```python
from flowyml import configure_notifications

configure_notifications(
    slack_webhook="https://hooks.slack.com/services/T000/B000/XXXX"
)
```

## 🔔 Sending Alerts

Send alerts from any step.

```python
from flowyml import get_notifier, step

@step
def notify_team(metrics):
    get_notifier().notify(
        title="Training Finished",
        message=f"Accuracy: {metrics['acc']}",
        level="success",
        channels=["slack"]
    )
```

## 🚨 Failure Alerts

Automatically notify on pipeline failure.

```python
@step(
    on_failure=on_failure(
        action="slack",
        recipients=["#ml-ops"]
    )
)
def critical_step():
    # ...
```

# Notifications & Alerts 🔔

UniFlow includes a flexible notification system to keep you informed about pipeline events, failures, and drift detection.

## 🔔 Configuration

Configure notifications globally or per-pipeline.

```python
from uniflow import configure_notifications

configure_notifications(
    console=True,
    slack_webhook="https://hooks.slack.com/services/...",
    email_config={
        'smtp_host': 'smtp.gmail.com',
        'username': 'user@example.com',
        'password': 'app-password',
        'to_addrs': ['team@example.com']
    }
)
```

## 📨 Sending Notifications

You can send manual notifications from any step.

```python
from uniflow import get_notifier

@step
def notify_team():
    notifier = get_notifier()
    notifier.notify(
        title="Training Complete",
        message="Model accuracy: 98%",
        level="success"
    )
```

## 🚨 Event Hooks

Automatically trigger notifications on specific events.

```python
notifier.on_pipeline_failure("training_pipeline", run_id, error="OOM")
notifier.on_drift_detected("feature_x", psi=0.45)
```

## 🛠 Custom Channels

Implement `NotificationChannel` to support other services (Discord, PagerDuty, etc.).

```python
from uniflow.monitoring.notifications import NotificationChannel, Notification

class DiscordChannel(NotificationChannel):
    def send(self, notification: Notification) -> bool:
        # Send to Discord webhook
        return True
```

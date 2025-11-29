# Notifications & Alerts 🔔

Know immediately when pipelines succeed, fail, or detect issues.

> [!NOTE]
> **What you'll learn**: How to set up proactive alerts so you don't have to watch dashboards all day
>
> **Key insight**: The faster you know about a failure, the faster you can fix it.

## Why Alerts Matter

**Without alerts**:
- **Silent failures**: A nightly job fails, and no one notices until the dashboard is empty in the morning
- **Dashboard fatigue**: Constantly refreshing the UI to check status
- **Delayed response**: Critical production issues persist for hours

**With flowyml alerts**:
- **Instant notification**: Slack ping the moment an exception is thrown
- **Contextual info**: "Pipeline X failed at step Y with error Z"
- **Multi-channel**: Email for summaries, Slack for urgent issues

## 🔔 Configuration

Configure notifications globally or per-pipeline.

```python
from flowyml import configure_notifications

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

## Real-World Pattern: The "Success" Ping

Notify the team when a long training run finishes successfully.

```python
from flowyml import step, get_notifier

@step
def notify_success(metrics):
    notifier = get_notifier()

    # Send a rich message to Slack
    notifier.notify(
        title="🚀 Model Training Complete",
        message=f"New model ready!\nAccuracy: {metrics['acc']:.2%}\nF1: {metrics['f1']:.2f}",
        level="success",
        channels=["slack"]
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
from flowyml.monitoring.notifications import NotificationChannel, Notification

class DiscordChannel(NotificationChannel):
    def send(self, notification: Notification) -> bool:
        # Send to Discord webhook
        return True
```

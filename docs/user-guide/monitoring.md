# Monitoring & Alerts 🚨

Know when pipelines fail before your users do.

> [!NOTE]
> **What you'll learn**: How to monitor system health and get instant alerts
>
> **Key insight**: Silent failures are the worst kind. Alerts turn invisible problems into actionable notifications.

## Why Monitoring Matters

**Without monitoring**:
- **Silent failures**: A nightly job fails, and you find out at the next standup
- **Resource waste**: Pipelines consume 100% CPU and you don't know why
- **Slow debugging**: "When did this start failing?"

**With UniFlow monitoring**:
- **Instant alerts**: Slack notification the moment a pipeline fails
- **Resource visibility**: See CPU/memory usage in real-time
- **Historical data**: Track success rates and failure patterns

## System Monitor 🖥️

The `SystemMonitor` tracks CPU and memory usage.

```python
from uniflow.monitoring.monitor import SystemMonitor

monitor = SystemMonitor("sys_mon")

# Check system health
is_healthy = monitor.check()

if not is_healthy:
    print("System is under high load!")
```

## Pipeline Monitor ⚡

The `PipelineMonitor` tracks the health of your pipelines, such as consecutive failures.

```python
from uniflow.monitoring.monitor import PipelineMonitor

monitor = PipelineMonitor("training_pipeline")
monitor.check()
```

## Alerting 🔔

UniFlow uses an `AlertManager` to dispatch alerts to configured handlers. By default, alerts are printed to the console, but you can add custom handlers (e.g., Slack, Email).

### Sending Alerts

```python
from uniflow.monitoring.alerts import alert_manager, AlertLevel

alert_manager.send_alert(
    title="Model Drift Detected",
    message="Accuracy dropped below 90%",
    level=AlertLevel.WARNING
)
```

### Real-World Pattern: Production Alert Setup

Send critical alerts to Slack, warnings to email.

```python
from uniflow.monitoring.alerts import AlertHandler, Alert, AlertLevel
import requests

class SlackAlertHandler(AlertHandler):
    def handle(self, alert: Alert):
        # Only send CRITICAL/ERROR to Slack (avoid noise)
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.ERROR]:
            requests.post(
                "https://hooks.slack.com/services/...",
                json={"text": f"🚨 {alert.title}: {alert.message}"}
            )

# Register the handler
alert_manager.add_handler(SlackAlertHandler())

# Now all pipeline failures will ping Slack
```

> [!TIP]
> **Pro Tip**: Use different alert levels to avoid alert fatigue. Reserve CRITICAL for production outages only.

## CLI Monitoring 💻

You can check system status via the CLI:

```bash
uniflow monitor status
```

!!! note "Beta Feature"
    CLI monitoring commands are currently in beta and may change in future releases.

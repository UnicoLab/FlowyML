# Monitoring & Alerts 🚨

UniFlow provides a built-in monitoring system to track system health and pipeline execution status. It can detect issues like high resource usage or pipeline failures and send alerts.

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

### Custom Alert Handlers 🛠️

You can implement your own alert handlers to integrate with external systems.

```python
from uniflow.monitoring.alerts import AlertHandler, Alert

class SlackAlertHandler(AlertHandler):
    def handle(self, alert: Alert):
        # Send to Slack API
        print(f"Sending to Slack: {alert.title}")

# Register the handler
alert_manager.add_handler(SlackAlertHandler())
```

## CLI Monitoring 💻

You can check system status via the CLI:

```bash
uniflow monitor status
```

!!! note "Beta Feature"
    CLI monitoring commands are currently in beta and may change in future releases.

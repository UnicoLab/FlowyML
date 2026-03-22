# 🚨 Monitoring & Alerts

!!! info "What you'll learn"
    How to monitor system health and get instant alerts for pipeline failures, resource issues, and drift detection. Silent failures are the worst kind — alerts turn invisible problems into actionable notifications.

Know when pipelines fail before your users do with real-time system and pipeline monitoring.

---

## Why Monitoring Matters

| Without Monitoring | With Monitoring |
|---|---|
| Silent failures go unnoticed for hours | Instant Slack notification on failure |
| Resource waste (100% CPU unknown) | Real-time CPU/memory visibility |
| "When did this start failing?" | Historical success rates and patterns |

---

## 🖥️ System Monitor

The `SystemMonitor` tracks CPU and memory usage to detect resource issues:

```python
from flowyml.monitoring.monitor import SystemMonitor

monitor = SystemMonitor("sys_mon")

# Check system health
is_healthy = monitor.check()

if not is_healthy:
    print("⚠️ System is under high load!")
```

### What It Checks

| Metric | Threshold | Action |
|---|---|---|
| CPU usage | > 90% sustained | Warning alert |
| Memory usage | > 85% | Warning alert |
| Disk space | < 10% free | Critical alert |

---

## ⚡ Pipeline Monitor

The `PipelineMonitor` tracks pipeline health — consecutive failures, success rates, and execution trends:

```python
from flowyml.monitoring.monitor import PipelineMonitor

monitor = PipelineMonitor("training_pipeline")

# Check pipeline health
health = monitor.check()
print(f"Status: {'Healthy' if health else 'Degraded'}")
```

---

## 🔔 AlertManager

FlowyML uses an `AlertManager` to dispatch alerts to configured handlers. By default, alerts go to the console, but you can add Slack, email, or custom handlers.

### Sending Alerts

```python
from flowyml.monitoring.alerts import alert_manager, AlertLevel

alert_manager.send_alert(
    title="Model Drift Detected",
    message="Accuracy dropped below 90%",
    level=AlertLevel.WARNING,
)
```

### Alert Levels

| Level | Use Case | Default Behavior |
|---|---|---|
| `INFO` | Informational updates | Console only |
| `WARNING` | Non-critical issues | Console + configured handlers |
| `ERROR` | Step or pipeline failure | All handlers |
| `CRITICAL` | Production outage | All handlers + escalation |

---

## Real-World Example: Production Alert Setup

Send critical alerts to Slack, warnings to email:

```python
from flowyml.monitoring.alerts import AlertHandler, Alert, AlertLevel, alert_manager
import requests

class SlackAlertHandler(AlertHandler):
    """Only send CRITICAL/ERROR to Slack to avoid noise."""

    def handle(self, alert: Alert):
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.ERROR]:
            requests.post(
                "https://hooks.slack.com/services/...",
                json={"text": f"🚨 {alert.title}: {alert.message}"},
            )

class EmailAlertHandler(AlertHandler):
    """Send all warnings and above via email digest."""

    def handle(self, alert: Alert):
        if alert.level.value >= AlertLevel.WARNING.value:
            send_email(
                subject=f"[FlowyML] {alert.title}",
                body=alert.message,
                to=["ml-team@company.com"],
            )

# Register both handlers
alert_manager.add_handler(SlackAlertHandler())
alert_manager.add_handler(EmailAlertHandler())
```

---

## 💻 CLI Monitoring

Check status and health from the command line:

```bash
# Check system status
flowyml monitor status

# Show recent alerts
flowyml monitor alerts --last 24h
```

!!! note "Beta Feature"
    CLI monitoring commands are currently in beta and may change in future releases.

---

## Best Practices

!!! tip "Use alert levels wisely"
    Reserve `CRITICAL` for production outages only. Over-alerting causes alert fatigue — your team will start ignoring notifications.

!!! tip "Combine monitors"
    Use `SystemMonitor` for infrastructure health AND `PipelineMonitor` for business logic health. Both are needed for full coverage.

!!! warning "Don't alert on expected failures"
    If a pipeline legitimately fails during development, exclude dev environments from alerting to reduce noise.

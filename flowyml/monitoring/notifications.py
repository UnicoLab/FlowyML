"""Notification system for pipeline events."""

import contextlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Notification:
    """A notification about a pipeline event."""

    title: str
    message: str
    level: str  # 'info', 'warning', 'error', 'success'
    timestamp: datetime
    metadata: dict[str, Any]


class NotificationChannel(ABC):
    """Base class for notification channels."""

    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """Send a notification."""
        pass


class ConsoleNotifier(NotificationChannel):
    """Print notifications to console."""

    def send(self, notification: Notification) -> bool:
        emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }.get(notification.level, "📢")

        print(f"{emoji} [{notification.level.upper()}] {notification.title}: {notification.message}")
        return True


class SlackNotifier(NotificationChannel):
    """Send notifications to Slack with rich Block Kit formatting."""

    def __init__(self, webhook_url: str | None = None, ui_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.ui_url = ui_url or os.getenv("FLOWYML_UI_URL", "http://localhost:5173")

    def send(self, notification: Notification) -> bool:
        if not self.webhook_url:
            return False

        try:
            import requests

            from flowyml.monitoring.slack_blocks import build_simple_message

            # Use rich Block Kit message
            payload = build_simple_message(
                title=notification.title,
                message=notification.message,
                level=notification.level,
                metadata=notification.metadata if notification.metadata else None,
            )

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def send_pipeline_success(
        self,
        pipeline_name: str,
        run_id: str,
        duration: float,
        metrics: dict[str, float] | None = None,
    ) -> bool:
        """Send a rich pipeline success notification."""
        if not self.webhook_url:
            return False

        try:
            import requests

            from flowyml.monitoring.slack_blocks import build_pipeline_success_message

            payload = build_pipeline_success_message(
                pipeline_name=pipeline_name,
                run_id=run_id,
                duration=duration,
                metrics=metrics,
                ui_url=self.ui_url,
            )

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def send_pipeline_failure(
        self,
        pipeline_name: str,
        run_id: str,
        error: str,
        step_name: str | None = None,
    ) -> bool:
        """Send a rich pipeline failure notification."""
        if not self.webhook_url:
            return False

        try:
            import requests

            from flowyml.monitoring.slack_blocks import build_pipeline_failure_message

            payload = build_pipeline_failure_message(
                pipeline_name=pipeline_name,
                run_id=run_id,
                error=error,
                step_name=step_name,
                ui_url=self.ui_url,
            )

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def send_drift_warning(
        self,
        feature: str,
        psi: float,
        threshold: float = 0.2,
        model_name: str | None = None,
    ) -> bool:
        """Send a rich drift warning notification."""
        if not self.webhook_url:
            return False

        try:
            import requests

            from flowyml.monitoring.slack_blocks import build_drift_warning_message

            payload = build_drift_warning_message(
                feature=feature,
                psi=psi,
                threshold=threshold,
                model_name=model_name,
                ui_url=self.ui_url,
            )

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception:
            return False


class EmailNotifier(NotificationChannel):
    """Send notifications via email."""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int = 587,
        username: str | None = None,
        password: str | None = None,
        from_addr: str | None = None,
        to_addrs: list[str] | None = None,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.from_addr = from_addr or os.getenv("SMTP_FROM")
        self.to_addrs = to_addrs or []

    def send(self, notification: Notification) -> bool:
        if not all([self.smtp_host, self.username, self.password, self.from_addr]):
            return False

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)
            msg["Subject"] = notification.title

            body = f"{notification.message}\n\nTime: {notification.timestamp}"
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True
        except Exception:
            return False


class NotificationManager:
    """Manage notifications across channels.

    Examples:
        >>> notifier = NotificationManager()
        >>> notifier.add_channel(ConsoleNotifier())
        >>> notifier.add_channel(SlackNotifier())
        >>> # Send notification
        >>> notifier.notify(title="Pipeline Failed", message="Training pipeline failed at step 3", level="error")
    """

    def __init__(self):
        self.channels: list[NotificationChannel] = []
        self.enabled = True

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self.channels.append(channel)

    def remove_channel(self, channel: NotificationChannel) -> None:
        """Remove a notification channel."""
        if channel in self.channels:
            self.channels.remove(channel)

    def notify(
        self,
        title: str,
        message: str,
        level: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send a notification to all channels."""
        if not self.enabled:
            return

        notification = Notification(
            title=title,
            message=message,
            level=level,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )

        for channel in self.channels:
            with contextlib.suppress(Exception):
                channel.send(notification)

    def on_pipeline_start(self, pipeline_name: str, run_id: str) -> None:
        """Notify when pipeline starts."""
        self.notify(
            title="Pipeline Started",
            message=f"Pipeline '{pipeline_name}' started (Run: {run_id})",
            level="info",
            metadata={"pipeline": pipeline_name, "run_id": run_id},
        )

    def on_pipeline_success(self, pipeline_name: str, run_id: str, duration: float) -> None:
        """Notify when pipeline succeeds."""
        self.notify(
            title="Pipeline Completed",
            message=f"Pipeline '{pipeline_name}' completed successfully in {duration:.2f}s",
            level="success",
            metadata={"pipeline": pipeline_name, "run_id": run_id, "duration": duration},
        )

    def on_pipeline_failure(self, pipeline_name: str, run_id: str, error: str) -> None:
        """Notify when pipeline fails."""
        self.notify(
            title="Pipeline Failed",
            message=f"Pipeline '{pipeline_name}' failed: {error}",
            level="error",
            metadata={"pipeline": pipeline_name, "run_id": run_id, "error": error},
        )

    def on_drift_detected(self, feature: str, psi: float) -> None:
        """Notify when data drift is detected."""
        self.notify(
            title="Data Drift Detected",
            message=f"Drift detected in feature '{feature}' (PSI: {psi:.4f})",
            level="warning",
            metadata={"feature": feature, "psi": psi},
        )


# Global notification manager
_global_notifier = NotificationManager()


def get_notifier() -> NotificationManager:
    """Get the global notification manager."""
    return _global_notifier


def configure_notifications(
    console: bool = True,
    slack_webhook: str | None = None,
    email_config: dict[str, Any] | None = None,
) -> None:
    """Configure notifications.

    Args:
        console: Enable console notifications
        slack_webhook: Slack webhook URL
        email_config: Email configuration dict
    """
    notifier = get_notifier()

    # Clear existing channels
    notifier.channels = []

    if console:
        notifier.add_channel(ConsoleNotifier())

    if slack_webhook:
        notifier.add_channel(SlackNotifier(slack_webhook))

    if email_config:
        notifier.add_channel(EmailNotifier(**email_config))

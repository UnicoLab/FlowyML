from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    title: str
    message: str
    level: AlertLevel
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] | None = None


class AlertHandler:
    def handle(self, alert: Alert) -> None:
        raise NotImplementedError


class ConsoleAlertHandler(AlertHandler):
    def handle(self, alert: Alert) -> None:
        prefix = {
            AlertLevel.INFO: "ℹ️  [INFO]",
            AlertLevel.WARNING: "⚠️  [WARNING]",
            AlertLevel.ERROR: "❌ [ERROR]",
            AlertLevel.CRITICAL: "🚨 [CRITICAL]",
        }.get(alert.level, "📢 [ALERT]")
        logger.log(
            {
                AlertLevel.INFO: logging.INFO,
                AlertLevel.WARNING: logging.WARNING,
                AlertLevel.ERROR: logging.ERROR,
                AlertLevel.CRITICAL: logging.CRITICAL,
            }.get(alert.level, logging.INFO),
            "%s %s — %s",
            prefix,
            alert.title,
            alert.message,
        )


class AlertManager:
    def __init__(self):
        self.handlers: list[AlertHandler] = [ConsoleAlertHandler()]
        self.history: list[Alert] = []

    def add_handler(self, handler: AlertHandler) -> None:
        self.handlers.append(handler)

    def send_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        metadata: dict | None = None,
    ) -> None:
        alert = Alert(title=title, message=message, level=level, metadata=metadata)
        self.history.append(alert)
        for handler in self.handlers:
            try:
                handler.handle(alert)
            except Exception as e:
                logger.error(f"Failed to handle alert: {e}")

    def alert(
        self,
        message: str,
        title: str = "Pipeline Alert",
        level: AlertLevel = AlertLevel.INFO,
        metadata: dict | None = None,
    ) -> None:
        """Convenience method for sending alerts."""
        self.send_alert(title=title, message=message, level=level, metadata=metadata)


# Global instance
alert_manager = AlertManager()

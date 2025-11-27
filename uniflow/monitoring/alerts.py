from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Never
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
    def handle(self, alert: Alert) -> Never:
        raise NotImplementedError


class ConsoleAlertHandler(AlertHandler):
    def handle(self, alert: Alert) -> None:
        # Simple ANSI colors if supported
        if alert.level == AlertLevel.ERROR or alert.level == AlertLevel.CRITICAL or alert.level == AlertLevel.WARNING:
            pass


class AlertManager:
    def __init__(self):
        self.handlers: list[AlertHandler] = [ConsoleAlertHandler()]
        self.history: list[Alert] = []

    def add_handler(self, handler: AlertHandler) -> None:
        self.handlers.append(handler)

    def send_alert(self, title: str, message: str, level: AlertLevel = AlertLevel.INFO, metadata: dict = None) -> None:
        alert = Alert(title=title, message=message, level=level, metadata=metadata)
        self.history.append(alert)
        for handler in self.handlers:
            try:
                handler.handle(alert)
            except Exception as e:
                logger.error(f"Failed to handle alert: {e}")


# Global instance
alert_manager = AlertManager()

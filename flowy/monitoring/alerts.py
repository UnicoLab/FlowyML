from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
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
    metadata: Optional[Dict[str, Any]] = None

class AlertHandler:
    def handle(self, alert: Alert):
        raise NotImplementedError

class ConsoleAlertHandler(AlertHandler):
    def handle(self, alert: Alert):
        color = ""
        reset = ""
        # Simple ANSI colors if supported
        if alert.level == AlertLevel.ERROR or alert.level == AlertLevel.CRITICAL:
            color = "\033[91m" # Red
            reset = "\033[0m"
        elif alert.level == AlertLevel.WARNING:
            color = "\033[93m" # Yellow
            reset = "\033[0m"
            
        print(f"{color}[{alert.level.value.upper()}] {alert.title}: {alert.message}{reset}")

class AlertManager:
    def __init__(self):
        self.handlers: List[AlertHandler] = [ConsoleAlertHandler()]
        self.history: List[Alert] = []

    def add_handler(self, handler: AlertHandler):
        self.handlers.append(handler)

    def send_alert(self, title: str, message: str, level: AlertLevel = AlertLevel.INFO, metadata: Dict = None):
        alert = Alert(title=title, message=message, level=level, metadata=metadata)
        self.history.append(alert)
        for handler in self.handlers:
            try:
                handler.handle(alert)
            except Exception as e:
                logger.error(f"Failed to handle alert: {e}")

# Global instance
alert_manager = AlertManager()

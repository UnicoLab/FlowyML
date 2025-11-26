"""
Notification system for pipeline events.
"""

import os
import json
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Notification:
    """A notification about a pipeline event."""
    title: str
    message: str
    level: str  # 'info', 'warning', 'error', 'success'
    timestamp: datetime
    metadata: Dict[str, Any]

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
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅'
        }.get(notification.level, '📢')
        
        print(f"\n{emoji} {notification.title}")
        print(f"   {notification.message}")
        print(f"   Time: {notification.timestamp}")
        return True

class SlackNotifier(NotificationChannel):
    """Send notifications to Slack."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        
    def send(self, notification: Notification) -> bool:
        if not self.webhook_url:
            print("⚠️  Slack webhook URL not configured")
            return False
            
        try:
            import requests
            
            color = {
                'info': '#36a64f',
                'warning': '#ff9900',
                'error': '#ff0000',
                'success': '#00ff00'
            }.get(notification.level, '#cccccc')
            
            payload = {
                'attachments': [{
                    'color': color,
                    'title': notification.title,
                    'text': notification.message,
                    'footer': 'UniFlow',
                    'ts': int(notification.timestamp.timestamp())
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Slack notification: {e}")
            return False

class EmailNotifier(NotificationChannel):
    """Send notifications via email."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_addr: Optional[str] = None,
        to_addrs: Optional[List[str]] = None
    ):
        self.smtp_host = smtp_host or os.getenv('SMTP_HOST')
        self.smtp_port = smtp_port
        self.username = username or os.getenv('SMTP_USERNAME')
        self.password = password or os.getenv('SMTP_PASSWORD')
        self.from_addr = from_addr or os.getenv('SMTP_FROM')
        self.to_addrs = to_addrs or []
        
    def send(self, notification: Notification) -> bool:
        if not all([self.smtp_host, self.username, self.password, self.from_addr]):
            print("⚠️  Email configuration incomplete")
            return False
            
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)
            msg['Subject'] = notification.title
            
            body = f"{notification.message}\n\nTime: {notification.timestamp}"
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
                
            return True
        except Exception as e:
            print(f"Failed to send email notification: {e}")
            return False

class NotificationManager:
    """
    Manage notifications across channels.
    
    Examples:
        >>> notifier = NotificationManager()
        >>> notifier.add_channel(ConsoleNotifier())
        >>> notifier.add_channel(SlackNotifier())
        >>> 
        >>> # Send notification
        >>> notifier.notify(
        ...     title="Pipeline Failed",
        ...     message="Training pipeline failed at step 3",
        ...     level="error"
        ... )
    """
    
    def __init__(self):
        self.channels: List[NotificationChannel] = []
        self.enabled = True
        
    def add_channel(self, channel: NotificationChannel):
        """Add a notification channel."""
        self.channels.append(channel)
        
    def remove_channel(self, channel: NotificationChannel):
        """Remove a notification channel."""
        if channel in self.channels:
            self.channels.remove(channel)
            
    def notify(
        self,
        title: str,
        message: str,
        level: str = 'info',
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Send a notification to all channels."""
        if not self.enabled:
            return
            
        notification = Notification(
            title=title,
            message=message,
            level=level,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        for channel in self.channels:
            try:
                channel.send(notification)
            except Exception as e:
                print(f"Failed to send notification via {channel.__class__.__name__}: {e}")
                
    def on_pipeline_start(self, pipeline_name: str, run_id: str):
        """Notify when pipeline starts."""
        self.notify(
            title="Pipeline Started",
            message=f"Pipeline '{pipeline_name}' started (Run: {run_id})",
            level='info',
            metadata={'pipeline': pipeline_name, 'run_id': run_id}
        )
        
    def on_pipeline_success(self, pipeline_name: str, run_id: str, duration: float):
        """Notify when pipeline succeeds."""
        self.notify(
            title="Pipeline Completed",
            message=f"Pipeline '{pipeline_name}' completed successfully in {duration:.2f}s",
            level='success',
            metadata={'pipeline': pipeline_name, 'run_id': run_id, 'duration': duration}
        )
        
    def on_pipeline_failure(self, pipeline_name: str, run_id: str, error: str):
        """Notify when pipeline fails."""
        self.notify(
            title="Pipeline Failed",
            message=f"Pipeline '{pipeline_name}' failed: {error}",
            level='error',
            metadata={'pipeline': pipeline_name, 'run_id': run_id, 'error': error}
        )
        
    def on_drift_detected(self, feature: str, psi: float):
        """Notify when data drift is detected."""
        self.notify(
            title="Data Drift Detected",
            message=f"Drift detected in feature '{feature}' (PSI: {psi:.4f})",
            level='warning',
            metadata={'feature': feature, 'psi': psi}
        )

# Global notification manager
_global_notifier = NotificationManager()

def get_notifier() -> NotificationManager:
    """Get the global notification manager."""
    return _global_notifier

def configure_notifications(
    console: bool = True,
    slack_webhook: Optional[str] = None,
    email_config: Optional[Dict[str, Any]] = None
):
    """
    Configure notifications.
    
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

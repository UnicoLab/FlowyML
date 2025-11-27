from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from uniflow.monitoring.notifications import (
    get_notifier,
    configure_notifications,
    ConsoleNotifier,
    SlackNotifier,
    EmailNotifier,
)

router = APIRouter()


class NotificationConfig(BaseModel):
    console: bool = True
    slack_webhook: str | None = None
    email_config: dict[str, Any] | None = None


@router.get("/")
async def get_notification_config():
    """Get current notification configuration."""
    notifier = get_notifier()
    config = {
        "console": False,
        "slack": False,
        "email": False,
        "channels": [],
    }

    for channel in notifier.channels:
        if isinstance(channel, ConsoleNotifier):
            config["console"] = True
            config["channels"].append("console")
        elif isinstance(channel, SlackNotifier):
            config["slack"] = True
            config["channels"].append("slack")
        elif isinstance(channel, EmailNotifier):
            config["email"] = True
            config["channels"].append("email")

    return config


@router.post("/")
async def update_notification_config(config: NotificationConfig):
    """Update notification configuration."""
    try:
        configure_notifications(
            console=config.console,
            slack_webhook=config.slack_webhook,
            email_config=config.email_config,
        )
        return {"status": "success", "message": "Notification configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_notification(channel: str = "console"):
    """Send a test notification."""
    notifier = get_notifier()
    try:
        notifier.notify(
            title="Test Notification",
            message=f"This is a test notification sent to {channel}",
            level="info",
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

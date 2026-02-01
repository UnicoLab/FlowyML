"""Slack Alerter - Native FlowyML Plugin.

This plugin allows sending alerts and notifications to Slack channels
using incoming webhooks or bot tokens.
"""

import logging
import json
import urllib.request
import urllib.error

from flowyml.plugins.base import AlerterPlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class SlackAlerter(AlerterPlugin):
    """Native Slack alerter for FlowyML.

    Sends notifications to Slack.

    Args:
        webhook_url: Slack incoming webhook URL (optional if token provided).
        token: Slack bot token (optional if webhook provided).
        default_channel: Default channel to post to (required if using token).
    """

    metadata = PluginMetadata(
        name="slack",
        version="1.0.0",
        description="Slack Alerter for pipeline notifications",
        author="FlowyML Team",
        plugin_type=PluginType.ALERTER,
        tags=["notification", "slack", "ops"],
    )

    def __init__(
        self,
        webhook_url: str = None,
        token: str = None,
        default_channel: str = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.webhook_url = webhook_url
        self.token = token
        self.default_channel = default_channel

    @property
    def plugin_type(self) -> PluginType:
        return PluginType.ALERTER

    def validate(self) -> bool:
        """Validate configuration."""
        if not self.webhook_url and not self.token:
            raise ValueError("SlackAlerter requires either 'webhook_url' or 'token'.")
        if self.token and not self.default_channel:
            raise ValueError("SlackAlerter with 'token' requires 'default_channel'.")
        return True

    def send_alert(
        self,
        title: str,
        message: str,
        level: str = "info",
        channel: str = None,
        **kwargs,
    ) -> bool:
        """Send an alert to Slack.

        Args:
            title: Title of the alert.
            message: Main message body.
            level: Alert level (info, success, warning, error).
            channel: Target channel (overrides default).
            **kwargs: Additional Slack payload options (attachments, blocks, etc.).

        Returns:
            True if successful.
        """
        color_map = {
            "info": "#3498db",  # Blue
            "success": "#2ecc71",  # Green
            "warning": "#f1c40f",  # Yellow
            "error": "#e74c3c",  # Red
            "critical": "#c0392b",  # Dark Red
        }
        color = color_map.get(level.lower(), "#3498db")

        # Construct payload
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "mrkdwn_in": ["text"],
                    "fields": [
                        {"title": "Level", "value": level.upper(), "short": True},
                    ],
                },
            ],
        }

        # Determine method: Webhook vs Token
        if self.webhook_url:
            return self._send_via_webhook(payload)
        elif self.token:
            target_channel = channel or self.default_channel
            payload["channel"] = target_channel
            return self._send_via_api(payload)

        return False

    def _send_via_webhook(self, payload: dict) -> bool:
        """Send using Incoming Webhook."""
        try:
            if not self.webhook_url.startswith(("http://", "https://")):
                raise ValueError("Slack webhook URL must start with http:// or https://")

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(  # noqa: S310
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                if response.status == 200:
                    logger.info("Slack alert sent successfully (webhook).")
                    return True
                else:
                    logger.error(f"Slack webhook failed: {response.status} {response.read()}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def _send_via_api(self, payload: dict) -> bool:
        """Send using Slack Web API (chat.postMessage)."""
        try:
            url = "https://slack.com/api/chat.postMessage"

            # Formatting for API differs slightly from pure attachments
            api_payload = {
                "channel": payload.pop("channel"),
                "attachments": payload["attachments"],
            }

            data = json.dumps(api_payload).encode("utf-8")
            req = urllib.request.Request(  # noqa: S310
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                },
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                resp_body = json.loads(response.read().decode())
                if resp_body.get("ok"):
                    logger.info("Slack alert sent successfully (API).")
                    return True
                else:
                    logger.error(f"Slack API failed: {resp_body.get('error')}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Slack alert (API): {e}")
            return False

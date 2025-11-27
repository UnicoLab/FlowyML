"""
Tests for notification system.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from uniflow.monitoring.notifications import (
    Notification,
    NotificationManager,
    ConsoleNotifier,
    SlackNotifier,
    EmailNotifier,
    configure_notifications,
    get_notifier,
)


class TestNotificationSystem(unittest.TestCase):
    def setUp(self):
        self.manager = NotificationManager()

    def test_console_notifier(self):
        """Test console notifications."""
        notifier = ConsoleNotifier()
        notification = Notification(
            title="Test",
            message="Test message",
            level="info",
            timestamp=datetime.now(),
            metadata={},
        )

        result = notifier.send(notification)
        self.assertTrue(result)

    def test_slack_notifier_no_webhook(self):
        """Test Slack notifier without webhook."""
        notifier = SlackNotifier()
        notification = Notification(
            title="Test",
            message="Test message",
            level="success",
            timestamp=datetime.now(),
            metadata={},
        )

        result = notifier.send(notification)
        self.assertFalse(result)

    @patch("requests.post")
    def test_slack_notifier_with_webhook(self, mock_post):
        """Test Slack notifier with webhook."""
        mock_post.return_value.status_code = 200

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        notification = Notification(
            title="Test",
            message="Test message",
            level="success",
            timestamp=datetime.now(),
            metadata={},
        )

        result = notifier.send(notification)
        self.assertTrue(result)
        mock_post.assert_called_once()

    def test_notification_manager_add_channel(self):
        """Test adding notification channels."""
        channel = ConsoleNotifier()
        self.manager.add_channel(channel)

        self.assertIn(channel, self.manager.channels)

    def test_notification_manager_remove_channel(self):
        """Test removing notification channels."""
        channel = ConsoleNotifier()
        self.manager.add_channel(channel)
        self.manager.remove_channel(channel)

        self.assertNotIn(channel, self.manager.channels)

    def test_notification_manager_notify(self):
        """Test sending notifications."""
        channel = MagicMock()
        self.manager.add_channel(channel)

        self.manager.notify(
            title="Test",
            message="Test message",
            level="info",
        )

        channel.send.assert_called_once()

    def test_event_based_notifications(self):
        """Test event-based notification helpers."""
        channel = MagicMock()
        self.manager.add_channel(channel)

        # Test pipeline start
        self.manager.on_pipeline_start("test_pipeline", "run_123")
        self.assertEqual(channel.send.call_count, 1)

        # Test pipeline success
        self.manager.on_pipeline_success("test_pipeline", "run_123", 10.5)
        self.assertEqual(channel.send.call_count, 2)

        # Test pipeline failure
        self.manager.on_pipeline_failure("test_pipeline", "run_123", "Error")
        self.assertEqual(channel.send.call_count, 3)

        # Test drift detection
        self.manager.on_drift_detected("feature_x", 0.25)
        self.assertEqual(channel.send.call_count, 4)

    def test_configure_notifications(self):
        """Test configuration helper."""
        configure_notifications(console=True)

        notifier = get_notifier()
        self.assertEqual(len(notifier.channels), 1)
        self.assertIsInstance(notifier.channels[0], ConsoleNotifier)


if __name__ == "__main__":
    unittest.main()

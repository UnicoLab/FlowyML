"""📡 Session Event Stream — Real-Time GenAI Observability.

Provides event emission for real-time dashboard integration.
Events are fired as turns start/end, evals complete, and sessions
finalize — enabling live monitoring of chatbot performance.

Usage::

    from flowyml.integrations.streaming import SessionEventStream

    # Console logger
    stream = SessionEventStream()

    # Webhook poster
    stream = SessionEventStream(webhook_url="https://api.example.com/events")

    # Custom callback
    stream = SessionEventStream(callback=my_handler)

    with session_trace("chatbot", project="demo") as tracer:
        tracer.genai_session.on_event(stream)
        with tracer.turn("user") as t:
            t.content = response  # Event fires on turn end
"""

from __future__ import annotations

import json
import logging
from typing import Any
from collections.abc import Callable

logger = logging.getLogger(__name__)

__all__ = ["SessionEventStream"]


class SessionEventStream:
    """Emits session events for real-time visualization.

    Can be attached to a :class:`GenAISession` via ``session.on_event(stream)``
    or passed as part of the ``session_trace()`` setup.

    Events emitted:
        - ``turn_start``     — A new turn begins
        - ``turn_end``       — A turn completes (with aggregated metrics)
        - ``eval_complete``  — An evaluation result is available
        - ``session_end``    — The session is finalized

    Args:
        callback: Optional ``(event_type, data) -> None`` function.
        webhook_url: Optional URL to POST events to (requires ``httpx``).
        buffer_size: Number of events to keep in memory for replay.
    """

    def __init__(
        self,
        *,
        callback: Callable[[str, dict[str, Any]], None] | None = None,
        webhook_url: str | None = None,
        buffer_size: int = 1000,
    ):
        self._callbacks: list[Callable[[str, dict[str, Any]], None]] = []
        self._webhook_url = webhook_url
        self._buffer: list[dict[str, Any]] = []
        self._buffer_size = buffer_size

        if callback:
            self._callbacks.append(callback)

    def __call__(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle an event (called by GenAISession's event system)."""
        event = {
            "event_type": event_type,
            "data": data,
        }

        # Buffer
        self._buffer.append(event)
        if len(self._buffer) > self._buffer_size:
            self._buffer = self._buffer[-self._buffer_size :]

        # Dispatch to callbacks
        for cb in self._callbacks:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.warning(f"Event callback error: {e}")

        # Webhook (fire-and-forget)
        if self._webhook_url:
            self._post_webhook(event)

    def on(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """Register an additional event callback."""
        self._callbacks.append(callback)

    @property
    def events(self) -> list[dict[str, Any]]:
        """Return buffered events (most recent first)."""
        return list(reversed(self._buffer))

    @property
    def event_count(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        """Clear the event buffer."""
        self._buffer.clear()

    def _post_webhook(self, event: dict[str, Any]) -> None:
        """POST event to webhook URL (non-blocking best-effort)."""
        try:
            import httpx

            with httpx.Client(timeout=5.0) as client:
                client.post(
                    self._webhook_url,
                    json=event,
                    headers={"Content-Type": "application/json"},
                )
        except ImportError:
            logger.debug(
                "httpx not installed — webhook events disabled. Install with: pip install httpx",
            )
        except Exception as e:
            logger.debug(f"Webhook POST failed: {e}")

    def console_logger(self) -> SessionEventStream:
        """Add a console logging callback (for debugging).

        Returns self for chaining::

            stream = SessionEventStream().console_logger()
        """

        def _log(event_type: str, data: dict[str, Any]) -> None:
            icon = {
                "turn_start": "▶",
                "turn_end": "✅",
                "eval_complete": "📈",
                "session_end": "🏁",
            }.get(event_type, "•")
            summary = json.dumps(data, default=str)[:120]
            logger.info(f"[FlowyML Stream] {icon} {event_type}: {summary}")

        self._callbacks.append(_log)
        return self

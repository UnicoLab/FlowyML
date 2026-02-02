"""Real-time log streaming utilities.

This module provides utilities for capturing and streaming logs from
pipeline executions to connected WebSocket clients.
"""

import asyncio
import contextlib
import logging
import sys
import threading
from collections import deque
from datetime import datetime
from io import StringIO
from collections.abc import Callable

from flowyml.ui.backend.routers.websocket import manager as ws_manager


class LogBuffer:
    """Thread-safe log buffer with configurable max size."""

    def __init__(self, max_size: int = 1000):
        self._buffer: deque[dict] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def append(self, entry: dict) -> None:
        """Append a log entry to the buffer."""
        with self._lock:
            self._buffer.append(entry)

    def get_recent(self, count: int = 100) -> list[dict]:
        """Get recent log entries."""
        with self._lock:
            return list(self._buffer)[-count:]

    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._buffer.clear()


class LogStreamer:
    """Captures and streams logs to WebSocket clients.

    This class hooks into Python's logging system and stdout/stderr
    to capture all output and stream it to connected WebSocket clients.

    Example:
        ```python
        streamer = LogStreamer(run_id="abc123")

        # Start capturing
        streamer.start()

        # Your pipeline code runs here...
        print("Processing step 1...")
        logger.info("Step 1 complete")

        # Stop capturing
        streamer.stop()
        ```
    """

    def __init__(self, run_id: str, step_name: str = "__all__", buffer_size: int = 1000):
        self.run_id = run_id
        self.step_name = step_name
        self.buffer = LogBuffer(max_size=buffer_size)
        self._active = False
        self._original_stdout = None
        self._original_stderr = None
        self._log_handler = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        """Start capturing logs."""
        if self._active:
            return

        self._active = True

        # Try to get the event loop
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

        # Install stdout/stderr hooks
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = _StreamWrapper(self._original_stdout, self._on_output, "stdout")
        sys.stderr = _StreamWrapper(self._original_stderr, self._on_output, "stderr")

        # Install logging handler
        self._log_handler = _StreamLoggingHandler(self._on_log)
        logging.root.addHandler(self._log_handler)

    def stop(self) -> None:
        """Stop capturing logs."""
        if not self._active:
            return

        self._active = False

        # Restore stdout/stderr
        if self._original_stdout:
            sys.stdout = self._original_stdout
        if self._original_stderr:
            sys.stderr = self._original_stderr

        # Remove logging handler
        if self._log_handler:
            logging.root.removeHandler(self._log_handler)
            self._log_handler = None

    def _on_output(self, text: str, stream: str) -> None:
        """Handle stdout/stderr output."""
        if not text.strip():
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR" if stream == "stderr" else "INFO",
            "message": text.strip(),
            "source": stream,
        }

        self.buffer.append(entry)
        self._broadcast(entry)

    def _on_log(self, record: logging.LogRecord) -> None:
        """Handle log record."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "source": "logging",
            "logger": record.name,
        }

        self.buffer.append(entry)
        self._broadcast(entry)

    def _broadcast(self, entry: dict) -> None:
        """Broadcast log entry to WebSocket clients."""
        content = f"[{entry['timestamp'][:19]}] [{entry['level']}] {entry['message']}"

        if self._loop and self._loop.is_running():
            # Schedule the coroutine on the event loop
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast_log(self.run_id, self.step_name, content),
                self._loop,
            )

    def get_history(self, count: int = 100) -> list[dict]:
        """Get recent log history."""
        return self.buffer.get_recent(count)

    def __enter__(self) -> "LogStreamer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


class _StreamWrapper:
    """Wrapper for stdout/stderr to capture output."""

    def __init__(self, original: StringIO, callback: Callable, stream_name: str):
        self._original = original
        self._callback = callback
        self._stream_name = stream_name

    def write(self, text: str) -> int:
        """Write to the stream and callback."""
        # Write to original
        result = self._original.write(text)
        # Callback for streaming
        self._callback(text, self._stream_name)
        return result

    def flush(self) -> None:
        """Flush the stream."""
        self._original.flush()

    def __getattr__(self, name: str):
        """Proxy other attributes to original stream."""
        return getattr(self._original, name)


class _StreamLoggingHandler(logging.Handler):
    """Logging handler that calls a callback for each record."""

    def __init__(self, callback: Callable):
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        with contextlib.suppress(Exception):
            self._callback(record)


# Global registry of active streamers
_active_streamers: dict[str, LogStreamer] = {}


def get_streamer(run_id: str) -> LogStreamer | None:
    """Get an active streamer by run ID."""
    return _active_streamers.get(run_id)


def create_streamer(run_id: str, step_name: str = "__all__") -> LogStreamer:
    """Create and register a new log streamer."""
    streamer = LogStreamer(run_id, step_name)
    _active_streamers[run_id] = streamer
    return streamer


def remove_streamer(run_id: str) -> None:
    """Remove a streamer from the registry."""
    if run_id in _active_streamers:
        _active_streamers[run_id].stop()
        del _active_streamers[run_id]

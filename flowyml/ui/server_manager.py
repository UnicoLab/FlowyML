"""UI Server Manager - Auto-start and manage the UI server in background."""

import threading
import time
import subprocess
from typing import Optional

from flowyml.ui.utils import is_ui_running, get_ui_url, get_ui_host_port


class UIServerManager:
    """Manages the UI server lifecycle in background threads."""

    _instance: Optional["UIServerManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._server_thread: Optional[threading.Thread] = None
        self._server_process: Optional[subprocess.Popen] = None
        # Initialize from config/env vars
        self._host, self._port = get_ui_host_port()
        self._running = False
        self._started = False

    @classmethod
    def get_instance(cls) -> "UIServerManager":
        """Get singleton instance of UI server manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def ensure_running(self, host: str | None = None, port: int | None = None, auto_start: bool = True) -> bool:
        """Ensure UI server is running, start it if not and auto_start is True.

        Args:
            host: Host to bind to (uses config/env if None)
            port: Port to bind to (uses config/env if None)
            auto_start: If True, automatically start server if not running

        Returns:
            True if server is running, False otherwise
        """
        # Use provided values or get from config
        if host is None or port is None:
            config_host, config_port = get_ui_host_port()
            self._host = host if host is not None else config_host
            self._port = port if port is not None else config_port
        else:
            self._host = host
            self._port = port

        # Check if already running
        if is_ui_running(host, port):
            return True

        if not auto_start:
            return False

        # Try to start the server
        return self.start(host, port)

    def start(self, host: str | None = None, port: int | None = None) -> bool:
        """Start the UI server in a background thread.

        Args:
            host: Host to bind to (uses config/env if None)
            port: Port to bind to (uses config/env if None)

        Returns:
            True if started successfully, False otherwise
        """
        # Use provided values or get from config
        if host is None or port is None:
            config_host, config_port = get_ui_host_port()
            self._host = host if host is not None else config_host
            self._port = port if port is not None else config_port
        else:
            self._host = host
            self._port = port

        if self._running:
            return is_ui_running(self._host, self._port)

        try:
            # Check if UI dependencies are available
            try:
                import uvicorn  # noqa: F401 - just check import
            except ImportError:
                return False

            # Capture host/port for closure
            server_host = self._host
            server_port = self._port
            startup_error = {"error": None}

            # Start server in a daemon thread
            def run_server():
                try:
                    import uvicorn

                    # Run uvicorn server (blocking call, but in daemon thread)
                    uvicorn.run(
                        "flowyml.ui.backend.main:app",
                        host=server_host,
                        port=server_port,
                        log_level="warning",  # Show startup issues
                        access_log=False,
                    )
                except Exception as e:
                    startup_error["error"] = str(e)

            # Start in daemon thread
            self._server_thread = threading.Thread(
                target=run_server,
                daemon=True,
                name="flowyml-ui-server",
            )
            self._server_thread.start()
            self._running = True
            self._started = True

            # Wait a bit for server to start (up to 8 seconds)
            max_wait = 8
            for _ in range(max_wait * 10):  # Check every 100ms
                time.sleep(0.1)
                # Check if server started successfully
                if is_ui_running(server_host, server_port):
                    return True
                # Check if we have an error
                if startup_error["error"]:
                    self._running = False
                    return False

            # If we get here, server didn't start in time
            self._running = False
            return False

        except Exception:
            self._running = False
            return False

    def stop(self) -> None:
        """Stop the UI server."""
        # Since we're using a daemon thread, it will be killed when main process exits
        # For now, we just mark it as stopped
        self._running = False
        self._server_thread = None

    def get_url(self) -> Optional[str]:
        """Get the URL of the running UI server.

        Returns:
            URL string if server is running, None otherwise
        """
        return get_ui_url(self._host, self._port)

    def is_running(self) -> bool:
        """Check if UI server is running."""
        return is_ui_running(self._host, self._port)

    def get_run_url(self, run_id: str) -> Optional[str]:
        """Get URL to view a specific pipeline run.

        Args:
            run_id: ID of the pipeline run

        Returns:
            URL string if server is running, None otherwise
        """
        base_url = self.get_url()
        if base_url:
            return f"{base_url}/runs/{run_id}"
        return None

    def get_pipeline_url(self, pipeline_name: str) -> Optional[str]:
        """Get URL to view a specific pipeline.

        Args:
            pipeline_name: Name of the pipeline

        Returns:
            URL string if server is running, None otherwise
        """
        base_url = self.get_url()
        if base_url:
            return f"{base_url}/pipelines/{pipeline_name}"
        return None

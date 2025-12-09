"""UI Server Manager - Auto-start and manage the UI server in background."""

import threading
import time
import subprocess
from typing import Optional

from flowyml.ui.utils import is_ui_running, get_ui_url


class UIServerManager:
    """Manages the UI server lifecycle in background threads."""

    _instance: Optional["UIServerManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._server_thread: Optional[threading.Thread] = None
        self._server_process: Optional[subprocess.Popen] = None
        self._host = "localhost"
        self._port = 8080
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

    def ensure_running(self, host: str = "localhost", port: int = 8080, auto_start: bool = True) -> bool:
        """Ensure UI server is running, start it if not and auto_start is True.

        Args:
            host: Host to bind to
            port: Port to bind to
            auto_start: If True, automatically start server if not running

        Returns:
            True if server is running, False otherwise
        """
        self._host = host
        self._port = port

        # Check if already running
        if is_ui_running(host, port):
            return True

        if not auto_start:
            return False

        # Try to start the server
        return self.start(host, port)

    def start(self, host: str = "localhost", port: int = 8080) -> bool:
        """Start the UI server in a background thread.

        Args:
            host: Host to bind to
            port: Port to bind to

        Returns:
            True if started successfully, False otherwise
        """
        if self._running:
            return is_ui_running(host, port)

        self._host = host
        self._port = port

        try:
            # Check if UI dependencies are available
            try:
                import uvicorn

                print(f"uvicorn {uvicorn.__version__}")
            except ImportError:
                return False

            # Start server in a daemon thread
            def run_server():
                try:
                    import uvicorn

                    # Run uvicorn server (blocking call, but in daemon thread)
                    uvicorn.run(
                        "flowyml.ui.backend.main:app",
                        host=host,
                        port=port,
                        log_level="warning",  # Reduce noise in background
                        access_log=False,
                    )
                except Exception:
                    pass  # Server will be stopped

            # Start in daemon thread
            self._server_thread = threading.Thread(
                target=run_server,
                daemon=True,
                name="flowyml-ui-server",
            )
            self._server_thread.start()
            self._running = True
            self._started = True

            # Wait a bit for server to start
            max_wait = 5
            for _ in range(max_wait * 10):  # Check every 100ms
                time.sleep(0.1)
                if is_ui_running(host, port):
                    return True

            # If we get here, server didn't start
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

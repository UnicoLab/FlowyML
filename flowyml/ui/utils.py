"""UI utility functions for checking UI server status and getting URLs."""

import os
import http.client


def get_ui_server_url() -> str:
    """Get the UI server URL from configuration or environment variables.

    Priority order:
    1. FLOWYML_SERVER_URL environment variable (explicit override)
    2. FLOWYML_REMOTE_UI_URL from config (for centralized deployments)
    3. FLOWYML_UI_HOST and FLOWYML_UI_PORT from config/env
    4. Default: http://localhost:8080

    Returns:
        Base URL of the UI server (e.g., "http://localhost:8080" or "https://flowyml.example.com")
    """
    # Check for explicit server URL override
    server_url = os.getenv("FLOWYML_SERVER_URL")
    if server_url:
        return server_url.rstrip("/")

    # Check for remote UI URL (centralized deployment)
    try:
        from flowyml.utils.config import get_config

        config = get_config()
        if config.remote_ui_url:
            return config.remote_ui_url.rstrip("/")

        # Use config values for host/port
        host = os.getenv("FLOWYML_UI_HOST", config.ui_host)
        port = int(os.getenv("FLOWYML_UI_PORT", str(config.ui_port)))

        # Determine protocol based on port (443 = https, else http)
        protocol = "https" if port == 443 else "http"

        return f"{protocol}://{host}:{port}"
    except Exception:
        # Fallback to defaults
        host = os.getenv("FLOWYML_UI_HOST", "localhost")
        port = int(os.getenv("FLOWYML_UI_PORT", "8080"))
        protocol = "https" if port == 443 else "http"
        return f"{protocol}://{host}:{port}"


def get_ui_host_port() -> tuple[str, int]:
    """Get UI host and port from configuration.

    Returns:
        Tuple of (host, port)
    """
    try:
        from flowyml.utils.config import get_config

        config = get_config()
        host = os.getenv("FLOWYML_UI_HOST", config.ui_host)
        port = int(os.getenv("FLOWYML_UI_PORT", str(config.ui_port)))
        return (host, port)
    except Exception:
        host = os.getenv("FLOWYML_UI_HOST", "localhost")
        port = int(os.getenv("FLOWYML_UI_PORT", "8080"))
        return (host, port)


def is_ui_running(host: str = "localhost", port: int = 8080) -> bool:
    """Check if the flowyml UI server is running.

    Args:
        host: Host to check (default: localhost)
        port: Port to check (default: 8080)

    Returns:
        True if UI server is running and responding, False otherwise
    """
    try:
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", "/api/health")
        response = conn.getresponse()

        # Check if response is successful and from flowyml
        # Note: must read data BEFORE closing connection
        if response.status == 200:
            data = response.read().decode("utf-8")
            conn.close()
            return "flowyml" in data.lower() or "ok" in data.lower()
        conn.close()
        return False
    except Exception:
        return False


def get_ui_url(host: str = "localhost", port: int = 8080) -> str | None:
    """Get the URL of the running flowyml UI server.

    Args:
        host: Host of the UI server (default: localhost)
        port: Port of the UI server (default: 8080)

    Returns:
        URL string if server is running, None otherwise
    """
    if is_ui_running(host, port):
        protocol = "https" if port == 443 else "http"
        return f"{protocol}://{host}:{port}"
    return None


def get_run_url(run_id: str, host: str = "localhost", port: int = 8080) -> str | None:
    """Get the URL to view a specific pipeline run.

    Args:
        run_id: ID of the pipeline run
        host: Host of the UI server (default: localhost)
        port: Port of the UI server (default: 8080)

    Returns:
        URL string to the run view if server is running, None otherwise
    """
    base_url = get_ui_url(host, port)
    if base_url:
        return f"{base_url}/runs/{run_id}"
    return None


def get_pipeline_url(pipeline_name: str, host: str = "localhost", port: int = 8080) -> str | None:
    """Get the URL to view a specific pipeline.

    Args:
        pipeline_name: Name of the pipeline
        host: Host of the UI server (default: localhost)
        port: Port of the UI server (default: 8080)

    Returns:
        URL string to the pipeline view if server is running, None otherwise
    """
    base_url = get_ui_url(host, port)
    if base_url:
        return f"{base_url}/pipelines/{pipeline_name}"
    return None

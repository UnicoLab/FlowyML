"""UI utility functions for checking UI server status and getting URLs."""

import os
import socket
import http.client

# Common ports to check for FlowyML unified server (backend serves frontend too)
# Priority order: 8080 (default), then alternates if port is busy
DEFAULT_SERVER_PORTS = [8080, 8081, 8082, 3000, 8000]


def find_available_port(start_port: int = 8081, max_attempts: int = 10) -> int:
    """Find an available port starting from the given port.

    Args:
        start_port: Port to start checking from
        max_attempts: Maximum number of ports to try

    Returns:
        First available port found
    """
    for offset in range(max_attempts):
        port = start_port + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue
    return start_port + max_attempts


def _check_port(host: str, port: int, path: str = "/", timeout: float = 1.0) -> bool:
    """Check if a port is responding to HTTP requests.

    Args:
        host: Host to check
        port: Port to check
        path: Path to request
        timeout: Connection timeout in seconds

    Returns:
        True if port is responding, False otherwise
    """
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", path)
        response = conn.getresponse()
        response.read()  # Must read before closing
        conn.close()
        return response.status in (200, 301, 302, 404)  # Accept common status codes
    except Exception:
        return False


def discover_server(host: str = "localhost") -> tuple[str, int] | None:
    """Auto-discover the running FlowyML server.

    The FlowyML backend serves both API and frontend on the same port.
    This function finds where the unified server is running.

    Args:
        host: Host to check

    Returns:
        Tuple of (host, port) if found, None otherwise
    """
    # First check environment variables
    env_port = os.getenv("FLOWYML_UI_PORT") or os.getenv("FLOWYML_SERVER_PORT")
    if env_port:
        port = int(env_port)
        if _check_port(host, port, "/api/health"):
            return (host, port)

    # Check environment URL
    env_url = os.getenv("FLOWYML_REMOTE_SERVER_URL")
    if env_url:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(env_url)
            if parsed.port and _check_port(host, parsed.port, "/api/health"):
                return (host, parsed.port)
        except Exception:
            pass

    # Check common server ports
    for port in DEFAULT_SERVER_PORTS:
        if _check_port(host, port, "/api/health"):
            return (host, port)

    return None


# Keep these as aliases for backwards compatibility
def discover_ui_server(host: str = "localhost") -> tuple[str, int] | None:
    """Alias for discover_server (unified server serves both UI and API)."""
    return discover_server(host)


def discover_api_server(host: str = "localhost") -> tuple[str, int] | None:
    """Alias for discover_server (unified server serves both UI and API)."""
    return discover_server(host)


def get_ui_server_url() -> str:
    """Get the unified server URL, auto-discovering if possible.

    The FlowyML backend serves both API and frontend on the same port.

    Priority order:
    1. FLOWYML_SERVER_URL environment variable (explicit override)
    2. FLOWYML_REMOTE_UI_URL from config (for centralized deployments)
    3. Auto-discover running server
    4. FLOWYML_UI_HOST and FLOWYML_UI_PORT from config/env
    5. Default: http://localhost:8080

    Returns:
        Base URL of the server
    """
    # Check for explicit server URL override
    server_url = os.getenv("FLOWYML_SERVER_URL")
    if server_url:
        # Strip /api suffix if present since we want base URL
        return server_url.rstrip("/").replace("/api", "")

    # Check for remote UI URL (centralized deployment)
    try:
        from flowyml.utils.config import get_config

        config = get_config()
        if config.remote_ui_url:
            return config.remote_ui_url.rstrip("/")
    except Exception:
        pass

    # Try auto-discovery
    host = os.getenv("FLOWYML_UI_HOST", "localhost")
    discovered = discover_server(host)
    if discovered:
        h, p = discovered
        protocol = "https" if p == 443 else "http"
        return f"{protocol}://{h}:{p}"

    # Fallback to config or defaults
    try:
        from flowyml.utils.config import get_config

        config = get_config()
        host = os.getenv("FLOWYML_UI_HOST", config.ui_host)
        port = int(os.getenv("FLOWYML_UI_PORT", str(config.ui_port)))
    except Exception:
        host = os.getenv("FLOWYML_UI_HOST", "localhost")
        port = int(os.getenv("FLOWYML_UI_PORT", "8080"))

    protocol = "https" if port == 443 else "http"
    return f"{protocol}://{host}:{port}"


def get_ui_host_port() -> tuple[str, int]:
    """Get server host and port, auto-discovering if possible.

    Returns:
        Tuple of (host, port)
    """
    host = os.getenv("FLOWYML_UI_HOST", "localhost")

    # Try auto-discovery first
    discovered = discover_server(host)
    if discovered:
        return discovered

    # Fallback to config or defaults
    try:
        from flowyml.utils.config import get_config

        config = get_config()
        host = os.getenv("FLOWYML_UI_HOST", config.ui_host)
        port = int(os.getenv("FLOWYML_UI_PORT", str(config.ui_port)))
        return (host, port)
    except Exception:
        port = int(os.getenv("FLOWYML_UI_PORT", "8080"))
        return (host, port)


def is_ui_running(host: str = "localhost", port: int | None = None) -> bool:
    """Check if the flowyml UI server is running.

    Args:
        host: Host to check (default: localhost)
        port: Port to check (default: auto-discover)

    Returns:
        True if UI server is running and responding, False otherwise
    """
    if port is None:
        # Try auto-discovery
        discovered = discover_ui_server(host)
        return discovered is not None

    return _check_port(host, port)


def get_ui_url(host: str = "localhost", port: int | None = None) -> str | None:
    """Get the URL of the running flowyml UI server.

    Args:
        host: Host of the UI server (default: localhost)
        port: Port of the UI server (default: auto-discover)

    Returns:
        URL string if server is running, None otherwise
    """
    if port is None:
        discovered = discover_ui_server(host)
        if discovered:
            h, p = discovered
            protocol = "https" if p == 443 else "http"
            return f"{protocol}://{h}:{p}"
        return None

    if _check_port(host, port):
        protocol = "https" if port == 443 else "http"
        return f"{protocol}://{host}:{port}"
    return None


def get_run_url(run_id: str, host: str = "localhost", port: int | None = None) -> str | None:
    """Get the URL to view a specific pipeline run.

    Args:
        run_id: ID of the pipeline run
        host: Host of the UI server (default: localhost)
        port: Port of the UI server (default: auto-discover)

    Returns:
        URL string to the run view if server is running, None otherwise
    """
    base_url = get_ui_url(host, port)
    if base_url:
        return f"{base_url}/runs/{run_id}"
    return None


def get_pipeline_url(
    pipeline_name: str,
    host: str = "localhost",
    port: int | None = None,
) -> str | None:
    """Get the URL to view a specific pipeline.

    Args:
        pipeline_name: Name of the pipeline
        host: Host of the UI server (default: localhost)
        port: Port of the UI server (default: auto-discover)

    Returns:
        URL string to the pipeline view if server is running, None otherwise
    """
    base_url = get_ui_url(host, port)
    if base_url:
        return f"{base_url}/pipelines/{pipeline_name}"
    return None

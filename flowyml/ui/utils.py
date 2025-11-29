"""UI utility functions for checking UI server status and getting URLs."""

import http.client


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
        conn.close()

        # Check if response is successful and from flowyml
        if response.status == 200:
            data = response.read().decode("utf-8")
            return "flowyml" in data.lower() or "ok" in data.lower()
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
        return f"http://{host}:{port}"
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

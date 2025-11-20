"""UI server CLI commands - Placeholder for FastAPI backend."""

from typing import Optional


def start_ui_server(host: str = "localhost", port: int = 8080, dev: bool = False) -> None:
    """Start the Flowy UI server.

    Args:
        host: Host to bind to
        port: Port to bind to
        dev: Run in development mode
    """
    print(f"Starting Flowy UI on http://{host}:{port}")
    print("Note: UI backend not yet implemented. Coming in Phase 2!")
    print("\nFor now, you can:")
    print("  - Use flowy experiment list to view experiments")
    print("  - Use flowy cache stats to view cache statistics")
    print("  - Check .flowy/runs/ for detailed run information")


def stop_ui_server() -> None:
    """Stop the Flowy UI server."""
    print("Stopping UI server...")

"""UI server CLI commands - Placeholder for FastAPI backend."""

from typing import Optional


def start_ui_server(host: str = "localhost", port: int = 8080, dev: bool = False) -> None:
    """Start the UniFlow UI server.

    Args:
        host: Host to bind to
        port: Port to bind to
        dev: Run in development mode
    """
    try:
        import uvicorn
    except ImportError:
        print("Error: 'ui' dependencies not installed.")
        print("Please install with: pip install 'uniflow[ui]'")
        return

    print(f"Starting UniFlow UI on http://{host}:{port}")
    
    # In development mode, we want reloading
    reload = dev
    
    uvicorn.run(
        "uniflow.ui.backend.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


def stop_ui_server() -> None:
    """Stop the UniFlow UI server."""
    # Since uvicorn blocks, stopping is usually done by Ctrl+C in the terminal
    # or by killing the process if run in background.
    # For now, we just print a message as we don't have a daemon manager yet.
    print("To stop the UI server, press Ctrl+C in the terminal where it is running.")

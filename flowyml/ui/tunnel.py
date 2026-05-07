"""Auto-Tunneling Engine for FlowyML remote telemetry.

Manages ephemeral ngrok tunnels to securely expose the local dashboard
to remote cloud execution nodes (Vertex AI, AWS, etc.).
"""

import os
import time
import requests
import subprocess
import logging
from typing import Optional

logger = logging.getLogger("flowyml.ui.tunnel")

NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"


def get_active_tunnel() -> Optional[str]:
    """Get the active ngrok tunnel URL if one exists.

    Returns:
        Secure ngrok https URL, or None if not found/running.
    """
    try:
        response = requests.get(NGROK_API_URL, timeout=1.0)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get("tunnels", [])
            for tunnel in tunnels:
                if tunnel.get("public_url", "").startswith("https://"):
                    return tunnel.get("public_url")
    except Exception:
        return None
    return None


def start_tunnel(port: int = 8080) -> Optional[str]:
    """Start an ngrok tunnel for the specified port.

    Args:
        port: The local port to expose.

    Returns:
        The secure ngrok https URL, or None if ngrok is not installed or failed.
    """
    # 1. Check if a tunnel is already running
    active_url = get_active_tunnel()
    if active_url:
        logger.debug(f"Found existing ngrok tunnel: {active_url}")
        return active_url

    # 2. Check if ngrok is installed
    try:
        subprocess.run(
            ["ngrok", "--version"],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        logger.warning(
            "ngrok not found. Remote UI telemetry will be disabled. "
            "Install ngrok to enable transparent local-to-cloud tracking.",
        )
        return None

    # 3. Start ngrok in the background
    logger.info(f"Starting auto-tunnel for local port {port}...")
    try:
        # We start it as a daemon process and send output to devnull
        with open(os.devnull, "w") as devnull:
            subprocess.Popen(
                ["ngrok", "http", str(port)],
                stdout=devnull,
                stderr=devnull,
                start_new_session=True,
            )

        # 4. Wait for the API to come up and the tunnel to be established
        # Poll up to 15 times (1.5 seconds)
        for _ in range(15):
            time.sleep(0.1)
            active_url = get_active_tunnel()
            if active_url:
                logger.info(f"Tunnel established: {active_url}")
                return active_url

        logger.warning("ngrok process started but failed to establish tunnel in time.")
        return None

    except Exception as e:
        logger.warning(f"Failed to start auto-tunnel: {str(e)}")
        return None

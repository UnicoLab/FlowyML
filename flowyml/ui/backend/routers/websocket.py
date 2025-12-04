"""WebSocket router for real-time log streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio
import contextlib

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for log streaming."""

    def __init__(self):
        # Format: {run_id: {step_name: [websocket, ...]}}
        self.active_connections: dict[str, dict[str, list[WebSocket]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, run_id: str, step_name: str = "__all__"):
        """Accept and track a WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            if run_id not in self.active_connections:
                self.active_connections[run_id] = {}
            if step_name not in self.active_connections[run_id]:
                self.active_connections[run_id][step_name] = []
            self.active_connections[run_id][step_name].append(websocket)

    async def disconnect(self, websocket: WebSocket, run_id: str, step_name: str = "__all__"):
        """Remove a WebSocket connection."""
        async with self._lock:
            if run_id in self.active_connections:
                if step_name in self.active_connections[run_id]:
                    with contextlib.suppress(ValueError):
                        self.active_connections[run_id][step_name].remove(websocket)
                    if not self.active_connections[run_id][step_name]:
                        del self.active_connections[run_id][step_name]
                if not self.active_connections[run_id]:
                    del self.active_connections[run_id]

    async def broadcast_log(self, run_id: str, step_name: str, log_content: str):
        """Broadcast log content to all connected clients for a run/step."""
        async with self._lock:
            connections_to_notify = []

            if run_id in self.active_connections:
                # Notify step-specific subscribers
                if step_name in self.active_connections[run_id]:
                    connections_to_notify.extend(self.active_connections[run_id][step_name])
                # Notify all-steps subscribers
                if "__all__" in self.active_connections[run_id]:
                    connections_to_notify.extend(self.active_connections[run_id]["__all__"])

        # Send to all relevant connections (outside lock to avoid blocking)
        message = {
            "type": "log",
            "step": step_name,
            "content": log_content,
            "timestamp": datetime.now().isoformat(),
        }
        for ws in connections_to_notify:
            with contextlib.suppress(Exception):
                await ws.send_json(message)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/runs/{run_id}/logs")
async def websocket_logs(websocket: WebSocket, run_id: str, step_name: str = "__all__"):
    """WebSocket endpoint for streaming logs.

    Query params:
        step_name: Optional. Subscribe to specific step logs only.

    Messages sent:
        {"type": "log", "step": "step_name", "content": "...", "timestamp": "..."}
        {"type": "dead_steps", "steps": ["step1", "step2"]}
    """
    await manager.connect(websocket, run_id, step_name)
    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for any message (ping/pong or close)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Could handle client commands here if needed
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, run_id, step_name)


@router.websocket("/ws/runs/{run_id}/steps/{step_name}/logs")
async def websocket_step_logs(websocket: WebSocket, run_id: str, step_name: str):
    """WebSocket endpoint for streaming logs of a specific step."""
    await manager.connect(websocket, run_id, step_name)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, run_id, step_name)

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Any
from flowyml.monitoring.alerts import alert_manager, AlertLevel

router = APIRouter()


class ClientError(BaseModel):
    message: str
    stack: str | None = None
    component_stack: str | None = None
    url: str | None = None
    user_agent: str | None = None
    additional_info: dict[str, Any] | None = None


@router.post("/errors")
async def report_client_error(error: ClientError, request: Request):
    """Report an error from the frontend client."""

    # Construct a detailed message
    details = f"Client Error: {error.message}\n"
    if error.url:
        details += f"URL: {error.url}\n"
    if error.user_agent:
        details += f"User Agent: {error.user_agent}\n"
    if error.component_stack:
        details += f"Component Stack:\n{error.component_stack}\n"
    if error.stack:
        details += f"Stack Trace:\n{error.stack}\n"

    # Send alert
    alert_manager.send_alert(
        title=f"Frontend Error: {error.message[:50]}...",
        message=details,
        level=AlertLevel.ERROR,
        metadata={
            "source": "frontend",
            "url": error.url,
            "user_agent": error.user_agent,
            "additional_info": error.additional_info,
        },
    )

    return {"status": "recorded"}

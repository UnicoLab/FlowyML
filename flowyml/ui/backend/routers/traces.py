from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from flowyml.ui.backend.dependencies import get_store

router = APIRouter()


@router.get("/")
async def list_traces(
    limit: int = 50,
    trace_id: str | None = None,
    event_type: str | None = None,
    project: str | None = None,
):
    """List traces, optionally filtered by project."""
    store = get_store()
    return store.list_traces(limit=limit, trace_id=trace_id, event_type=event_type, project=project)


@router.get("/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific trace tree."""
    store = get_store()
    events = store.get_trace(trace_id)
    if not events:
        raise HTTPException(status_code=404, detail="Trace not found")

    # Reconstruct tree
    root_events = [e for e in events if not e["parent_id"]]

    def build_tree(event):
        children = [e for e in events if e["parent_id"] == event["event_id"]]
        event["children"] = [build_tree(child) for child in children]
        return event

    return [build_tree(root) for root in root_events]


class TraceEventCreate(BaseModel):
    event_id: str
    trace_id: str
    parent_id: str | None = None
    event_type: str
    name: str
    inputs: dict | None = None
    outputs: dict | None = None
    start_time: float | None = None
    end_time: float | None = None
    duration: float | None = None
    status: str | None = None
    error: str | None = None
    metadata: dict | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    model: str | None = None


@router.post("/")
async def create_trace_event(event: TraceEventCreate):
    """Create or update a trace event."""
    try:
        store = get_store()
        store.save_trace_event(event.dict())
        return {"status": "success", "event_id": event.event_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

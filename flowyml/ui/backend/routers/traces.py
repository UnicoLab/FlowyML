from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from flowyml.ui.backend.dependencies import get_store

router = APIRouter()

#: Upper bound on any client-supplied page size. Without it a request such as
#: `?limit=100000000` makes the server materialise an unbounded result set.
MAX_PAGE_SIZE = 1000



@router.get("/")
async def list_traces(
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    trace_id: str | None = None,
    event_type: str | None = None,
    project: str | None = None,
    model: str | None = None,
    status: str | None = None,
):
    """List traces, optionally filtered by project, event type, model, or status."""
    store = get_store()
    traces = store.list_traces(limit=limit, trace_id=trace_id, event_type=event_type, project=project)

    # Apply additional filters not supported by storage layer
    if model:
        traces = [t for t in traces if t.get("model") and model.lower() in t["model"].lower()]
    if status:
        traces = [t for t in traces if t.get("status") == status]

    return traces


@router.get("/stats")
async def trace_stats(project: str | None = None):
    """Get aggregated GenAI observability statistics.

    Returns total traces, tokens, cost, model distribution, and event type breakdown.
    """
    store = get_store()
    traces = store.list_traces(limit=500, project=project)

    total_tokens = 0
    total_cost = 0.0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    models: dict[str, int] = {}
    event_types: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    for t in traces:
        total_tokens += t.get("total_tokens") or 0
        total_cost += t.get("cost") or 0
        total_prompt_tokens += t.get("prompt_tokens") or 0
        total_completion_tokens += t.get("completion_tokens") or 0

        model = t.get("model")
        if model:
            models[model] = models.get(model, 0) + 1

        etype = t.get("event_type", "unknown")
        event_types[etype] = event_types.get(etype, 0) + 1

        st = t.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1

    return {
        "total_traces": len(traces),
        "total_tokens": total_tokens,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_cost": round(total_cost, 6),
        "models": models,
        "event_types": event_types,
        "status_distribution": status_counts,
    }


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    project: str | None = None,
):
    """List session-level traces (aggregated multi-turn sessions)."""
    store = get_store()
    # Sessions are stored as event_type='session' or 'genai_session'
    sessions = store.list_traces(limit=limit, event_type="session", project=project)
    genai_sessions = store.list_traces(limit=limit, event_type="genai_session", project=project)

    all_sessions = sessions + genai_sessions
    # Sort by start_time descending
    all_sessions.sort(key=lambda s: s.get("start_time") or 0, reverse=True)
    return all_sessions[:limit]


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
    project: str | None = None


@router.post("/")
async def create_trace_event(event: TraceEventCreate):
    """Create or update a trace event."""
    try:
        store = get_store()
        store.save_trace_event(event.dict())
        return {"status": "success", "event_id": event.event_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{trace_id}")
async def delete_trace(trace_id: str):
    """Delete all events for a given trace."""
    store = get_store()
    try:
        events = store.get_trace(trace_id)
        if not events:
            raise HTTPException(status_code=404, detail="Trace not found")

        from sqlalchemy import delete as sql_delete

        with store.engine.connect() as conn:
            conn.execute(
                sql_delete(store.traces).where(store.traces.c.trace_id == trace_id),
            )
            conn.commit()

        return {"status": "deleted", "trace_id": trace_id, "events_deleted": len(events)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

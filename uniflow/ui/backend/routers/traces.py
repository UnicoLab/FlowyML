from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from uniflow.storage.metadata import SQLiteMetadataStore

router = APIRouter()

@router.get("/")
async def list_traces(
    limit: int = 50,
    trace_id: Optional[str] = None,
    event_type: Optional[str] = None
):
    """List traces."""
    store = SQLiteMetadataStore()
    
    # We need to implement list_traces in metadata store or query manually
    # For now, let's query manually via sqlite
    import sqlite3
    conn = sqlite3.connect(store.db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM traces"
    params = []
    conditions = []
    
    if trace_id:
        conditions.append("trace_id = ?")
        params.append(trace_id)
        
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY start_time DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    
    traces = []
    import json
    for row in rows:
        trace = dict(zip(columns, row))
        # Parse JSON fields
        for field in ['inputs', 'outputs', 'metadata']:
            if trace[field]:
                try:
                    trace[field] = json.loads(trace[field])
                except:
                    pass
        traces.append(trace)
        
    conn.close()
    return traces

@router.get("/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific trace tree."""
    store = SQLiteMetadataStore()
    events = store.get_trace(trace_id)
    if not events:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    # Reconstruct tree
    root_events = [e for e in events if not e['parent_id']]
    
    def build_tree(event):
        children = [e for e in events if e['parent_id'] == event['event_id']]
        event['children'] = [build_tree(child) for child in children]
        return event
        
    return [build_tree(root) for root in root_events]

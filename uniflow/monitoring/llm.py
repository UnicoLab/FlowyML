"""
LLM Monitoring and Observability module.
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import functools

from uniflow.core.context import Context

@dataclass
class LLMEvent:
    """Event representing an LLM interaction."""
    event_id: str
    trace_id: str
    parent_id: Optional[str]
    event_type: str  # 'llm', 'tool', 'chain', 'agent'
    name: str
    inputs: Dict[str, Any]
    outputs: Optional[Dict[str, Any]] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: str = "running"  # 'running', 'success', 'error'
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Token usage and cost
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: Optional[str] = None

    def end(self, outputs: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """End the event."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.outputs = outputs
        if error:
            self.status = "error"
            self.error = str(error)
        else:
            self.status = "success"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class LLMTracer:
    """Tracer for LLM calls."""
    
    def __init__(self):
        self.current_trace_id: Optional[str] = None
        self.event_stack: List[LLMEvent] = []
        self._metadata_store = None
        
    @property
    def metadata_store(self):
        if self._metadata_store is None:
            from uniflow.storage.metadata import SQLiteMetadataStore
            self._metadata_store = SQLiteMetadataStore()
        return self._metadata_store

    def start_trace(self, name: str = "root") -> str:
        """Start a new trace."""
        self.current_trace_id = str(uuid.uuid4())
        return self.current_trace_id

    def start_event(
        self,
        name: str,
        event_type: str,
        inputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None
    ) -> LLMEvent:
        """Start a new event."""
        if not self.current_trace_id:
            self.start_trace()
            
        event = LLMEvent(
            event_id=str(uuid.uuid4()),
            trace_id=self.current_trace_id,
            parent_id=parent_id or (self.event_stack[-1].event_id if self.event_stack else None),
            event_type=event_type,
            name=name,
            inputs=inputs,
            metadata=metadata or {}
        )
        self.event_stack.append(event)
        return event

    def end_event(
        self,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """End the current event."""
        if not self.event_stack:
            return
            
        event = self.event_stack.pop()
        event.end(outputs, error)
        
        if metrics:
            event.prompt_tokens = metrics.get('prompt_tokens', 0)
            event.completion_tokens = metrics.get('completion_tokens', 0)
            event.total_tokens = metrics.get('total_tokens', 0)
            event.cost = metrics.get('cost', 0.0)
            event.model = metrics.get('model')
            
        # Save to storage
        self.metadata_store.save_trace_event(event.to_dict())
        
        return event

# Global tracer instance
tracer = LLMTracer()

def trace_llm(name: str = None, event_type: str = "llm"):
    """Decorator to trace LLM calls."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            event_name = name or func.__name__
            
            # Capture inputs
            inputs = {
                'args': [str(a) for a in args],
                'kwargs': {k: str(v) for k, v in kwargs.items()}
            }
            
            tracer.start_event(event_name, event_type, inputs)
            
            try:
                result = func(*args, **kwargs)
                
                # Try to extract metrics if result has them (e.g. OpenAI response)
                metrics = {}
                if hasattr(result, 'usage'): # OpenAI style
                    metrics['prompt_tokens'] = getattr(result.usage, 'prompt_tokens', 0)
                    metrics['completion_tokens'] = getattr(result.usage, 'completion_tokens', 0)
                    metrics['total_tokens'] = getattr(result.usage, 'total_tokens', 0)
                
                tracer.end_event(outputs={'result': str(result)}, metrics=metrics)
                return result
            except Exception as e:
                tracer.end_event(error=str(e))
                raise e
        return wrapper
    return decorator

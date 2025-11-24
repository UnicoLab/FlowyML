"""
Step Decorator - Define pipeline steps with automatic context injection.
"""

import hashlib
import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps
from dataclasses import dataclass, field


@dataclass
class StepConfig:
    """Configuration for a pipeline step."""
    name: str
    func: Callable
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    cache: Union[bool, str, Callable] = "code_hash"
    retry: int = 0
    timeout: Optional[int] = None
    resources: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    condition: Optional[Callable] = None
    
    def __hash__(self):
        """Make StepConfig hashable."""
        return hash(self.name)


class Step:
    """
    A pipeline step that can be executed with automatic context injection.
    """
    
    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        inputs: Optional[List[str]] = None,
        outputs: Optional[List[str]] = None,
        cache: Union[bool, str, Callable] = "code_hash",
        retry: int = 0,
        timeout: Optional[int] = None,
        resources: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        condition: Optional[Callable] = None
    ):
        self.func = func
        self.name = name or func.__name__
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.cache = cache
        self.retry = retry
        self.timeout = timeout
        self.resources = resources or {}
        self.tags = tags or {}
        self.condition = condition
        
        self.config = StepConfig(
            name=self.name,
            func=func,
            inputs=self.inputs,
            outputs=self.outputs,
            cache=self.cache,
            retry=self.retry,
            timeout=self.timeout,
            resources=self.resources,
            tags=self.tags,
            condition=self.condition
        )
    
    def __call__(self, *args, **kwargs):
        """Execute the step function."""
        # Check condition if present
        if self.condition:
            # We might need to inject context into condition too, 
            # but for now assume it takes no args or same args as step?
            # This is tricky without context injection logic here.
            # The executor handles execution, so maybe we just store it here.
            pass
            
        return self.func(*args, **kwargs)
    
    def get_code_hash(self) -> str:
        """Generate hash of function code for caching."""
        source = inspect.getsource(self.func)
        return hashlib.sha256(source.encode()).hexdigest()[:16]
    
    def get_input_hash(self, inputs: Dict[str, Any]) -> str:
        """Generate hash of inputs for caching."""
        input_str = json.dumps(inputs, sort_keys=True, default=str)
        return hashlib.sha256(input_str.encode()).hexdigest()[:16]
    
    def get_cache_key(self, inputs: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate cache key based on caching strategy.
        
        Args:
            inputs: Input data for the step
            
        Returns:
            Cache key string
        """
        if self.cache == "code_hash":
            return f"{self.name}:{self.get_code_hash()}"
        elif self.cache == "input_hash" and inputs:
            return f"{self.name}:{self.get_input_hash(inputs)}"
        elif callable(self.cache) and inputs:
            return self.cache(inputs, {})
        else:
            return f"{self.name}:no-cache"
    
    def __repr__(self) -> str:
        return f"Step(name='{self.name}', inputs={self.inputs}, outputs={self.outputs})"


def step(
    inputs: Optional[List[str]] = None,
    outputs: Optional[List[str]] = None,
    cache: Union[bool, str, Callable] = "code_hash",
    retry: int = 0,
    timeout: Optional[int] = None,
    resources: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    name: Optional[str] = None,
    condition: Optional[Callable] = None
):
    """
    Decorator to define a pipeline step with automatic context injection.
    
    Args:
        inputs: List of input asset names
        outputs: List of output asset names
        cache: Caching strategy ("code_hash", "input_hash", callable, or False)
        retry: Number of retry attempts on failure
        timeout: Maximum execution time in seconds
        resources: Resource requirements (e.g., {"gpu": 1, "memory": "16GB"})
        tags: Metadata tags for the step
        name: Optional custom name for the step
        condition: Optional callable that returns True if step should run
    
    Example:
        >>> @step(inputs=["data/train"], outputs=["model/trained"])
        ... def train_model(train_data, learning_rate: float, epochs: int):
        ...     # learning_rate and epochs auto-injected from context!
        ...     model = Model()
        ...     model.train(train_data, lr=learning_rate, epochs=epochs)
        ...     return model
    """
    def decorator(func: Callable) -> Step:
        return Step(
            func=func,
            name=name,
            inputs=inputs,
            outputs=outputs,
            cache=cache,
            retry=retry,
            timeout=timeout,
            resources=resources,
            tags=tags,
            condition=condition
        )
    
    return decorator

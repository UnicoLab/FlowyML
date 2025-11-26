"""
Context Management - Automatic parameter injection for ML pipelines.
"""

import inspect
from typing import Any, Dict, Optional, List, Set
from copy import deepcopy


class Context:
    """
    Pipeline context with automatic parameter injection.
    
    Example:
        >>> ctx = Context(
        ...     learning_rate=0.001,
        ...     epochs=10,
        ...     batch_size=32,
        ...     device="cuda"
        ... )
    """
    
    def __init__(self, **kwargs):
        self._params = kwargs
        self._parent = None
        self._metadata = {}
    
    def __getattr__(self, name: str) -> Any:
        """Allow dot notation access to parameters."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        
        if name in self._params:
            return self._params[name]
        
        if self._parent and name in self._parent._params:
            return self._parent._params[name]
        
        raise AttributeError(f"Context has no parameter '{name}'")
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access to parameters."""
        if key in self._params:
            return self._params[key]
        
        if self._parent and key in self._parent._params:
            return self._parent._params[key]
        
        raise KeyError(f"Context has no parameter '{key}'")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get parameter with default value."""
        try:
            return self[key]
        except KeyError:
            return default
    
    def keys(self) -> Set[str]:
        """Return all parameter keys."""
        keys = set(self._params.keys())
        if self._parent:
            keys.update(self._parent.keys())
        return keys
    
    def items(self) -> List[tuple]:
        """Return all parameter items."""
        result = {}
        if self._parent:
            result.update(dict(self._parent.items()))
        result.update(self._params)
        return list(result.items())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        result = {}
        if self._parent:
            result.update(self._parent.to_dict())
        result.update(self._params)
        return result
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        Update context with new data.
        
        Args:
            data: Dictionary of key-value pairs to add to context
        """
        self._params.update(data)
    
    def inherit(self, **overrides) -> "Context":
        """Create child context with inheritance."""
        child = Context(**overrides)
        child._parent = self
        return child
    
    def inject_params(self, func: callable) -> Dict[str, Any]:
        """
        Automatically inject parameters based on function signature.
        
        Args:
            func: Function to analyze and inject parameters for
            
        Returns:
            Dictionary of parameters to inject
        """
        sig = inspect.signature(func)
        injected = {}
        
        for param_name, param in sig.parameters.items():
            # Skip self, cls, args, kwargs
            if param_name in ('self', 'cls'):
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, 
                             inspect.Parameter.VAR_KEYWORD):
                continue
            
            # Check if parameter exists in context
            if param_name in self.keys():
                injected[param_name] = self[param_name]
        
        return injected
    
    def validate_for_step(self, step_func: callable, exclude: List[str] = None) -> List[str]:
        """
        Validate that all required parameters are available.
        
        Args:
            step_func: Step function to validate
            exclude: List of parameter names to exclude from validation (e.g. inputs)
            
        Returns:
            List of missing required parameters
        """
        sig = inspect.signature(step_func)
        missing = []
        exclude = exclude or []
        
        for param_name, param in sig.parameters.items():
            # Skip optional parameters
            if param_name in ('self', 'cls'):
                continue
            if param_name in exclude:
                continue
            if param.default != inspect.Parameter.empty:
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL,
                             inspect.Parameter.VAR_KEYWORD):
                continue
            
            # Check if required param is missing
            if param_name not in self.keys():
                missing.append(param_name)
        
        return missing
    
    def __repr__(self) -> str:
        params_str = ", ".join(f"{k}={v}" for k, v in list(self._params.items())[:5])
        if len(self._params) > 5:
            params_str += "..."
        return f"Context({params_str})"


def context(**kwargs) -> Context:
    """
    Create a new context with parameters.
    
    Example:
        >>> ctx = context(
        ...     learning_rate=0.001,
        ...     epochs=10,
        ...     batch_size=32
        ... )
    """
    return Context(**kwargs)

"""
Pipeline registry for managing available pipelines.
"""

from typing import Callable, Dict, Optional, Any
from uniflow.core.pipeline import Pipeline

class PipelineRegistry:
    """
    Registry for pipelines to enable lookup by name.
    
    Crucial for scheduling and remote execution where we need to 
    find a pipeline definition by its string name.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PipelineRegistry, cls).__new__(cls)
            cls._instance.pipelines = {}
        return cls._instance
        
    def register(self, name: str, pipeline_factory: Callable[..., Pipeline]):
        """
        Register a pipeline factory function.
        
        Args:
            name: Unique name for the pipeline
            pipeline_factory: Function that returns a Pipeline instance
        """
        self.pipelines[name] = pipeline_factory
        print(f"📝 Registered pipeline: {name}")
        
    def get(self, name: str) -> Optional[Callable[..., Pipeline]]:
        """Get a pipeline factory by name."""
        return self.pipelines.get(name)
        
    def list_pipelines(self) -> Dict[str, str]:
        """List all registered pipelines."""
        return {name: str(func) for name, func in self.pipelines.items()}
        
    def clear(self):
        """Clear all registrations."""
        self.pipelines = {}

# Global instance
pipeline_registry = PipelineRegistry()

def register_pipeline(name: str):
    """Decorator to register a pipeline factory."""
    def decorator(func):
        pipeline_registry.register(name, func)
        return func
    return decorator

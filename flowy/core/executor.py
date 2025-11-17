"""
Executor Module - Execute pipeline steps with retry and error handling.
"""

import time
import traceback
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExecutionResult:
    """Result of step execution."""
    step_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    cached: bool = False
    retries: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class Executor:
    """Base executor for running pipeline steps."""
    
    def execute_step(
        self,
        step,
        inputs: Dict[str, Any],
        context_params: Dict[str, Any],
        cache_store: Optional[Any] = None
    ) -> ExecutionResult:
        """
        Execute a single step.
        
        Args:
            step: Step to execute
            inputs: Input data for the step
            context_params: Parameters from context
            cache_store: Cache store for caching
            
        Returns:
            ExecutionResult with output or error
        """
        raise NotImplementedError


class LocalExecutor(Executor):
    """
    Local executor - runs steps in the current process.
    """
    
    def execute_step(
        self,
        step,
        inputs: Dict[str, Any],
        context_params: Dict[str, Any],
        cache_store: Optional[Any] = None
    ) -> ExecutionResult:
        """Execute step locally with retry and caching."""
        start_time = time.time()
        retries = 0
        
        # Check cache
        if cache_store and step.cache:
            cache_key = step.get_cache_key(inputs)
            cached_result = cache_store.get(cache_key)
            
            if cached_result is not None:
                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=True,
                    output=cached_result,
                    duration_seconds=duration,
                    cached=True
                )
        
        # Execute with retry
        max_retries = step.retry
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Prepare arguments
                kwargs = {**inputs, **context_params}
                
                # Execute step
                result = step.func(**kwargs)
                
                # Cache result
                if cache_store and step.cache:
                    cache_key = step.get_cache_key(inputs)
                    cache_store.set(
                        cache_key,
                        result,
                        step.name,
                        step.get_code_hash()
                    )
                
                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=True,
                    output=result,
                    duration_seconds=duration,
                    retries=retries
                )
                
            except Exception as e:
                last_error = str(e)
                retries += 1
                
                if attempt < max_retries:
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                
                # All retries exhausted
                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=False,
                    error=f"{last_error}\n{traceback.format_exc()}",
                    duration_seconds=duration,
                    retries=retries
                )
        
        # Should never reach here
        duration = time.time() - start_time
        return ExecutionResult(
            step_name=step.name,
            success=False,
            error=last_error,
            duration_seconds=duration,
            retries=retries
        )


class DistributedExecutor(Executor):
    """
    Distributed executor - runs steps on remote workers.
    (Placeholder for future implementation)
    """
    
    def __init__(self, worker_pool_size: int = 4):
        self.worker_pool_size = worker_pool_size
    
    def execute_step(
        self,
        step,
        inputs: Dict[str, Any],
        context_params: Dict[str, Any],
        cache_store: Optional[Any] = None
    ) -> ExecutionResult:
        """Execute step in distributed manner."""
        # Placeholder - would use Ray, Dask, or similar
        # For now, fall back to local execution
        local_executor = LocalExecutor()
        return local_executor.execute_step(step, inputs, context_params, cache_store)

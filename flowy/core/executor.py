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
    skipped: bool = False
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
        
        # Check condition
        if step.condition:
            try:
                # We pass inputs and context params to condition if it accepts them
                # For simplicity, let's try to inspect the condition function 
                # or just pass what we can.
                # A simple approach: pass nothing if it takes no args, or kwargs if it does.
                # But inspect is safer.
                import inspect
                sig = inspect.signature(step.condition)
                kwargs = {**inputs, **context_params}
                
                # Filter kwargs to only what condition accepts
                cond_kwargs = {
                    k: v for k, v in kwargs.items() 
                    if k in sig.parameters
                }
                
                should_run = step.condition(**cond_kwargs)
                
                if not should_run:
                    duration = time.time() - start_time
                    return ExecutionResult(
                        step_name=step.name,
                        success=True,
                        output=None, # Skipped steps produce None
                        duration_seconds=duration,
                        skipped=True
                    )
            except Exception as e:
                # If condition check fails, treat as step failure
                duration = time.time() - start_time
                return ExecutionResult(
                    step_name=step.name,
                    success=False,
                    error=f"Condition check failed: {str(e)}",
                    duration_seconds=duration
                )
        
        # Check cache
        if cache_store and step.cache:
            cache_key = step.get_cache_key(inputs)
            cached_result = cache_store.get(cache_key)
            
            if cached_result is not None:
                duration = time.time() - start_time
                # Store outputs for next steps
                step_outputs = {}
                if cached_result is not None:
                    if isinstance(cached_result, (list, tuple)) and len(step.outputs) == len(cached_result):
                        for output_name, out_val in zip(step.outputs, cached_result):
                            step_outputs[output_name] = out_val
                    else:
                        for output_name in step.outputs:
                            step_outputs[output_name] = cached_result
                return ExecutionResult(
                    step_name=step.name,
                    success=True,
                    output=step_outputs if step.outputs else cached_result,
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

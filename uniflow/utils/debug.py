"""
Pipeline and step debugging tools.
"""

import sys
import traceback
import pdb
from typing import Any, Callable, Optional
from functools import wraps
import json

class StepDebugger:
    """
    Debug individual pipeline steps.
    
    Features:
    - Breakpoints
    - Input/output inspection
    - Exception debugging
    - Step profiling
    
    Examples:
        >>> from uniflow import step, StepDebugger
        >>> 
        >>> debugger = StepDebugger()
        >>> 
        >>> @step(outputs=["processed"])
        ... @debugger.breakpoint()
        ... def process_data(data):
        ...     # Debugger will stop here
        ...     return data * 2
    """
    
    def __init__(self):
        self.breakpoints = set()
        self.step_history = []
        self.enabled = True
        
    def breakpoint(self, condition: Optional[Callable] = None):
        """
        Add a breakpoint to a step.
        
        Args:
            condition: Optional condition function. Break only if returns True.
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                    
                # Check condition
                should_break = True
                if condition:
                    should_break = condition(*args, **kwargs)
                    
                if should_break:
                    print(f"\n🔍 Breakpoint: {func.__name__}")
                    print(f"   Args: {args}")
                    print(f"   Kwargs: {kwargs}")
                    print("\n   Commands:")
                    print("   - 'c' to continue")
                    print("   - 'i' to inspect inputs")
                    print("   - 'p <expr>' to print expression")
                    print("   - 'pdb' to enter pdb debugger")
                    
                    while True:
                        cmd = input("\n(debug) ").strip()
                        
                        if cmd == 'c':
                            break
                        elif cmd == 'i':
                            print(f"Args: {args}")
                            print(f"Kwargs: {kwargs}")
                        elif cmd.startswith('p '):
                            expr = cmd[2:]
                            try:
                                # Evaluate in context
                                result = eval(expr, {'args': args, 'kwargs': kwargs})
                                print(result)
                            except Exception as e:
                                print(f"Error: {e}")
                        elif cmd == 'pdb':
                            pdb.set_trace()
                            break
                            
                # Execute function
                try:
                    result = func(*args, **kwargs)
                    
                    # Log execution
                    self.step_history.append({
                        'step': func.__name__,
                        'inputs': {'args': args, 'kwargs': kwargs},
                        'output': result,
                        'success': True
                    })
                    
                    return result
                except Exception as e:
                    # Log error
                    self.step_history.append({
                        'step': func.__name__,
                        'inputs': {'args': args, 'kwargs': kwargs},
                        'error': str(e),
                        'success': False
                    })
                    raise
                    
            return wrapper
        return decorator
        
    def trace(self):
        """Enable step tracing (print inputs/outputs)."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                    
                print(f"\n🔍 Tracing: {func.__name__}")
                print(f"   Inputs: args={args}, kwargs={kwargs}")
                
                result = func(*args, **kwargs)
                
                print(f"   Output: {result}")
                
                return result
            return wrapper
        return decorator
        
    def profile(self):
        """Profile step execution time."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                import time
                
                start = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start
                
                print(f"⏱️  {func.__name__}: {duration:.3f}s")
                
                return result
            return wrapper
        return decorator
        
    def get_history(self):
        """Get step execution history."""
        return self.step_history
        
    def clear_history(self):
        """Clear execution history."""
        self.step_history = []

class PipelineDebugger:
    """
    Debug entire pipelines.
    
    Features:
    - Step-by-step execution
    - DAG visualization
    - Execution replay
    - Error analysis
    """
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.execution_log = []
        
    def step_through(self):
        """Execute pipeline step-by-step with breaks."""
        print(f"\n🔍 Stepping through pipeline: {self.pipeline.name}")
        print(f"   Steps: {len(self.pipeline.steps)}")
        
        self.pipeline.build()
        order = self.pipeline.dag.topological_sort()
        
        for i, node in enumerate(order):
            step = node.step
            print(f"\n--- Step {i+1}/{len(order)}: {step.name} ---")
            print(f"Inputs: {step.inputs}")
            print(f"Outputs: {step.outputs}")
            
            response = input("\nExecute this step? [Y/n/q]: ").lower()
            
            if response == 'q':
                print("Debugging stopped.")
                break
            elif response == 'n':
                print("Skipping step.")
                continue
                
            # Execute step would happen here in actual implementation
            print("✓ Step executed (simulation)")
            
    def visualize_dag(self):
        """Visualize the pipeline DAG."""
        self.pipeline.build()
        print(self.pipeline.dag.visualize())
        
    def analyze_errors(self, run_id: str):
        """Analyze errors from a failed run."""
        # Load run metadata
        metadata = self.pipeline.metadata_store.load_run(run_id)
        
        if not metadata:
            print(f"Run {run_id} not found")
            return
            
        print(f"\n🔍 Error Analysis for run: {run_id}")
        print("=" * 60)
        
        steps_metadata = metadata.get('steps', {})
        
        failed_steps = []
        for step_name, step_data in steps_metadata.items():
            if not step_data.get('success', True):
                failed_steps.append((step_name, step_data))
                
        if not failed_steps:
            print("No errors found in this run.")
            return
            
        for step_name, step_data in failed_steps:
            print(f"\n❌ Failed Step: {step_name}")
            print(f"   Error: {step_data.get('error', 'Unknown')}")
            print(f"   Duration: {step_data.get('duration', 0):.2f}s")
            
            if step_data.get('source_code'):
                print(f"\n   Source Code:")
                for i, line in enumerate(step_data['source_code'].split('\n')[:10], 1):
                    print(f"   {i:3d} | {line}")
                    
    def replay_run(self, run_id: str, start_from: Optional[str] = None):
        """Replay a previous run, optionally starting from a specific step."""
        print(f"🔄 Replaying run: {run_id}")
        if start_from:
            print(f"   Starting from step: {start_from}")
            
        # Implementation would load state and re-execute
        print("   (Replay functionality - would re-execute pipeline)")

def inspect_step(step):
    """
    Inspect a step's metadata.
    
    Args:
        step: Step to inspect
    """
    print(f"\n🔍 Step Inspection: {step.name}")
    print("=" * 60)
    print(f"Function: {step.func.__name__}")
    print(f"Inputs: {step.inputs}")
    print(f"Outputs: {step.outputs}")
    print(f"Tags: {step.tags}")
    print(f"Resources: {step.resources}")
    
    if step.source_code:
        print(f"\nSource Code:")
        print("-" * 60)
        print(step.source_code)
        print("-" * 60)
        
def print_dag(pipeline):
    """Pretty print pipeline DAG."""
    pipeline.build()
    print(pipeline.visualize())

# Global debugger instance
_global_debugger = StepDebugger()

def debug_step(*args, **kwargs):
    """Convenience function to debug a step."""
    return _global_debugger.breakpoint(*args, **kwargs)

def trace_step():
    """Convenience function to trace a step."""
    return _global_debugger.trace()

def profile_step():
    """Convenience function to profile a step."""
    return _global_debugger.profile()

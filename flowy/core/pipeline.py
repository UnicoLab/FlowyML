"""
Pipeline Module - Main orchestration for ML pipelines.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from flowy.core.context import Context
from flowy.core.step import Step
from flowy.core.graph import DAG, Node
from flowy.core.executor import Executor, LocalExecutor, ExecutionResult
from flowy.core.cache import CacheStore


class PipelineResult:
    """Result of pipeline execution."""
    
    def __init__(self, run_id: str, pipeline_name: str):
        self.run_id = run_id
        self.pipeline_name = pipeline_name
        self.success = False
        self.step_results: Dict[str, ExecutionResult] = {}
        self.outputs: Dict[str, Any] = {}
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.duration_seconds: float = 0.0
    
    def add_step_result(self, result: ExecutionResult):
        """Add result from a step execution."""
        self.step_results[result.step_name] = result
        
        # Track outputs
        if result.success and result.output is not None:
            # Assuming single output for simplicity
            self.outputs[result.step_name] = result.output
    
    def finalize(self, success: bool):
        """Mark pipeline as complete."""
        self.success = success
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access to outputs."""
        return self.outputs.get(key)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'run_id': self.run_id,
            'pipeline_name': self.pipeline_name,
            'success': self.success,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'steps': {
                name: {
                    'success': result.success,
                    'duration': result.duration_seconds,
                    'cached': result.cached,
                    'retries': result.retries,
                    'error': result.error
                }
                for name, result in self.step_results.items()
            }
        }
    
    def summary(self) -> str:
        """Generate execution summary."""
        lines = [
            f"Pipeline: {self.pipeline_name}",
            f"Run ID: {self.run_id}",
            f"Status: {'✓ SUCCESS' if self.success else '✗ FAILED'}",
            f"Duration: {self.duration_seconds:.2f}s",
            "",
            "Steps:"
        ]
        
        for name, result in self.step_results.items():
            status = "✓" if result.success else "✗"
            cached = " (cached)" if result.cached else ""
            retries = f" [{result.retries} retries]" if result.retries > 0 else ""
            lines.append(
                f"  {status} {name}: {result.duration_seconds:.2f}s{cached}{retries}"
            )
            if result.error:
                lines.append(f"     Error: {result.error.split(chr(10))[0]}")
        
        return "\n".join(lines)


class Pipeline:
    """
    Main pipeline class for orchestrating ML workflows.
    
    Example:
        >>> from flowy import Pipeline, step, context
        >>> 
        >>> ctx = context(learning_rate=0.001, epochs=10)
        >>> 
        >>> @step(outputs=["model/trained"])
        ... def train(learning_rate: float, epochs: int):
        ...     return train_model(learning_rate, epochs)
        >>> 
        >>> pipeline = Pipeline("my_pipeline", context=ctx)
        >>> pipeline.add_step(train)
        >>> result = pipeline.run()
    """
    
    def __init__(
        self,
        name: str,
        context: Optional[Context] = None,
        executor: Optional[Executor] = None,
        enable_cache: bool = True,
        cache_dir: str = ".flowy/cache"
    ):
        self.name = name
        self.context = context or Context()
        self.executor = executor or LocalExecutor()
        self.enable_cache = enable_cache
        
        self.steps: List[Step] = []
        self.dag = DAG()
        
        # Storage
        self.cache_store = CacheStore(cache_dir) if enable_cache else None
        self.runs_dir = Path(".flowy/runs")
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        
        # State
        self._built = False
    
    def add_step(self, step: Step) -> "Pipeline":
        """
        Add a step to the pipeline.
        
        Args:
            step: Step to add
            
        Returns:
            Self for chaining
        """
        self.steps.append(step)
        self._built = False
        return self
    
    def build(self):
        """Build the execution DAG."""
        if self._built:
            return
        
        # Clear previous DAG
        self.dag = DAG()
        
        # Add nodes
        for step in self.steps:
            node = Node(
                name=step.name,
                step=step,
                inputs=step.inputs,
                outputs=step.outputs
            )
            self.dag.add_node(node)
        
        # Build edges
        self.dag.build_edges()
        
        # Validate
        errors = self.dag.validate()
        if errors:
            raise ValueError(f"Pipeline validation failed:\n" + "\n".join(errors))
        
        self._built = True
    
    def run(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        debug: bool = False
    ) -> PipelineResult:
        """
        Execute the pipeline.
        
        Args:
            inputs: Optional input data for the pipeline
            debug: Enable debug mode with detailed logging
            
        Returns:
            PipelineResult with outputs and execution info
        """
        # Build DAG if needed
        if not self._built:
            self.build()
        
        # Generate run ID
        run_id = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = PipelineResult(run_id, self.name)
        
        # Get execution order
        execution_order = self.dag.topological_sort()
        
        if debug:
            print(f"\n🌊 Starting pipeline: {self.name}")
            print(f"Run ID: {run_id}")
            print(f"Steps: {len(execution_order)}")
            print(self.dag.visualize())
        
        # Track outputs from executed steps
        step_outputs: Dict[str, Any] = inputs or {}
        
        # Execute steps in order
        for node in execution_order:
            step = node.step
            
            if debug:
                print(f"\n▶ Executing step: {step.name}")
            
            # Validate context parameters
            missing_params = self.context.validate_for_step(step.func)
            if missing_params:
                error_msg = f"Missing required parameters: {missing_params}"
                step_result = ExecutionResult(
                    step_name=step.name,
                    success=False,
                    error=error_msg
                )
                result.add_step_result(step_result)
                result.finalize(success=False)
                return result
            
            # Prepare step inputs
            step_inputs = {}
            for input_name in step.inputs:
                if input_name in step_outputs:
                    step_inputs[input_name] = step_outputs[input_name]
                else:
                    # Input might be parameter name, not asset name
                    # This is simplified - real implementation would be smarter
                    pass
            
            # Get context parameters for this step
            context_params = self.context.inject_params(step.func)
            
            # Execute step
            step_result = self.executor.execute_step(
                step,
                step_inputs,
                context_params,
                self.cache_store
            )
            
            result.add_step_result(step_result)
            
            if debug:
                status = "✓" if step_result.success else "✗"
                cached = " (cached)" if step_result.cached else ""
                print(f"{status} Completed in {step_result.duration_seconds:.2f}s{cached}")
            
            # Handle failure
            if not step_result.success:
                if debug:
                    print(f"\n✗ Pipeline failed at step: {step.name}")
                    print(f"Error: {step_result.error}")
                result.finalize(success=False)
                self._save_run(result)
                return result
            
            # Store outputs for next steps
            if step_result.output is not None:
                for output_name in step.outputs:
                    step_outputs[output_name] = step_result.output
        
        # Success!
        result.finalize(success=True)
        
        if debug:
            print(f"\n✓ Pipeline completed successfully!")
            print(f"Total duration: {result.duration_seconds:.2f}s")
        
        self._save_run(result)
        return result
    
    def _save_run(self, result: PipelineResult):
        """Save run results to disk."""
        run_file = self.runs_dir / f"{result.run_id}.json"
        with open(run_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
    
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.cache_store:
            return self.cache_store.stats()
        return {}
    
    def invalidate_cache(
        self,
        step: Optional[str] = None,
        before: Optional[str] = None
    ):
        """
        Invalidate cache entries.
        
        Args:
            step: Invalidate cache for specific step
            before: Invalidate cache entries before date
        """
        if self.cache_store:
            if step:
                self.cache_store.invalidate(step_name=step)
            else:
                self.cache_store.clear()
    
    def visualize(self) -> str:
        """Generate pipeline visualization."""
        if not self._built:
            self.build()
        return self.dag.visualize()
    
    def __repr__(self) -> str:
        return f"Pipeline(name='{self.name}', steps={len(self.steps)})"

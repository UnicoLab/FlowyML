import unittest
from uniflow import Pipeline, step, context
from tests.base import BaseTestCase

class TestCore(BaseTestCase):
    """Tests for core functionality."""

    def test_simple_pipeline(self):
        """Test a simple pipeline execution."""
        
        @step(outputs=["data"])
        def step1():
            return "hello"
            
        @step(inputs=["data"])
        def step2(data):
            return f"{data} world"
            
        # Explicit pipeline construction
        p = Pipeline("my_pipeline")
        p.add_step(step1)
        p.add_step(step2)
            
        run = p.run()
        self.assertTrue(run.success)
        # The result of the pipeline is the result of the last step or all outputs?
        # PipelineResult.outputs contains outputs of steps.
        # step2 returns "hello world".
        # We need to check how to access result.
        # run.outputs is a dict.
        # step2 has no named outputs, so it might be under step name.
        self.assertEqual(run.outputs.get("step2"), "hello world")

    def test_context_injection(self):
        """Test automatic context injection."""
        
        ctx = context(param1="value1", param2=123)
        
        @step
        def step_with_params(param1, param2):
            return f"{param1}-{param2}"
            
        p = Pipeline("context_pipeline", context=ctx)
        p.add_step(step_with_params)
            
        run = p.run()
        self.assertTrue(run.success)
        self.assertEqual(run.outputs.get("step_with_params"), "value1-123")

    def test_pipeline_failure(self):
        """Test pipeline failure handling."""
        
        @step
        def failing_step():
            raise ValueError("Something went wrong")
            
        p = Pipeline("failing_pipeline")
        p.add_step(failing_step)
            
        # Should not raise exception, but return failed run
        run = p.run()
        self.assertFalse(run.success)
        # Error might be in step_results
        self.assertIn("failing_step", run.step_results)
        self.assertFalse(run.step_results["failing_step"].success)

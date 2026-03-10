"""Tests for sub-pipeline composition."""

import unittest
from flowyml.core.subpipeline import SubPipelineStep, sub_pipeline
from tests.base import BaseTestCase


class MockPipeline:
    """Mock pipeline for sub-pipeline tests."""

    def __init__(self, name="mock_pipeline", steps=None):
        self.name = name
        self.steps = steps or []


class TestSubPipeline(BaseTestCase):
    """Test suite for SubPipelineStep."""

    def test_sub_pipeline_step_creation(self):
        """SubPipelineStep wraps a pipeline correctly."""
        child = MockPipeline("child")
        step = SubPipelineStep(
            sub_pipeline=child,
            inputs=["raw_data"],
            outputs=["clean_data"],
        )
        self.assertEqual(step.name, "sub:child")
        self.assertEqual(step.inputs, ["raw_data"])
        self.assertEqual(step.outputs, ["clean_data"])
        self.assertTrue(step._is_sub_pipeline)

    def test_sub_pipeline_custom_name(self):
        """SubPipelineStep accepts custom name."""
        child = MockPipeline("child")
        step = SubPipelineStep(
            sub_pipeline=child,
            name="preprocessing",
            inputs=["data"],
            outputs=["result"],
        )
        self.assertEqual(step.name, "preprocessing")

    def test_sub_pipeline_function(self):
        """sub_pipeline() convenience function creates SubPipelineStep."""
        child = MockPipeline("child")
        step = sub_pipeline(
            child,
            inputs=["raw"],
            outputs=["clean"],
        )
        self.assertIsInstance(step, SubPipelineStep)
        self.assertEqual(step.inputs, ["raw"])
        self.assertEqual(step.outputs, ["clean"])

    def test_sub_pipeline_mappings(self):
        """SubPipelineStep stores input/output mappings."""
        child = MockPipeline("child")
        step = SubPipelineStep(
            sub_pipeline=child,
            input_mapping={"parent_data": "child_input"},
            output_mapping={"child_output": "parent_result"},
        )
        self.assertEqual(step.input_mapping, {"parent_data": "child_input"})
        self.assertEqual(step.output_mapping, {"child_output": "parent_result"})


if __name__ == "__main__":
    unittest.main()

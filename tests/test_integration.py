"""Integration tests for full pipeline workflows."""

import unittest
import pandas as pd
from uniflow import Pipeline, step, Dataset, Model, Metrics
from uniflow.core.context import Context
from tests.base import BaseTestCase


class TestIntegration(BaseTestCase):
    """Integration tests for complete workflows."""

    def test_ml_training_pipeline(self):
        """Test complete ML training pipeline workflow."""
        @step
        def load_data():
            df = pd.DataFrame({
                "feature1": [1, 2, 3, 4, 5],
                "feature2": [2, 4, 6, 8, 10],
                "target": [0, 0, 1, 1, 1]
            })
            return Dataset.create(data=df, name="training_data", rows=5, cols=3)

        @step
        def train_model(dataset: Dataset):
            # Simulate training
            model_data = {"weights": [0.5, 0.3], "bias": 0.1}
            return Model.create(
                data=model_data,
                name="trained_model",
                framework="sklearn",
                accuracy=0.95
            )

        @step
        def evaluate_model(model: Model):
            return Metrics.create(
                accuracy=0.95,
                precision=0.93,
                recall=0.94,
                f1_score=0.935
            )

        p = Pipeline("ml_training")
        p.add_step(load_data)
        p.add_step(train_model)
        p.add_step(evaluate_model)

        result = p.run()
        
        self.assertTrue(result.success)
        self.assertIn("load_data", result.outputs)
        self.assertIn("train_model", result.outputs)
        self.assertIn("evaluate_model", result.outputs)

    def test_data_processing_pipeline(self):
        """Test data processing pipeline."""
        @step
        def extract_data(source: str):
            return {"data": [1, 2, 3, 4, 5], "source": source}

        @step
        def transform_data(data: dict):
            transformed = [x * 2 for x in data["data"]]
            return {"data": transformed, "operation": "multiply_by_2"}

        @step
        def load_data(data: dict):
            return {"loaded": True, "count": len(data["data"])}

        ctx = Context(source="test_source")
        p = Pipeline("etl_pipeline", context=ctx)
        p.add_step(extract_data)
        p.add_step(transform_data)
        p.add_step(load_data)

        result = p.run()
        
        self.assertTrue(result.success)
        self.assertEqual(result["load_data"]["count"], 5)

    def test_pipeline_with_asset_lineage(self):
        """Test pipeline tracking asset lineage."""
        @step
        def create_raw_data():
            return Dataset.create(data=[1, 2, 3], name="raw_data")

        @step
        def process_data(raw_data: Dataset):
            return Dataset.create(
                data=[2, 4, 6],
                name="processed_data",
                parent=raw_data
            )

        @step
        def aggregate_data(processed_data: Dataset):
            return Dataset.create(
                data=[12],
                name="aggregated_data",
                parent=processed_data
            )

        p = Pipeline("lineage_pipeline")
        p.add_step(create_raw_data)
        p.add_step(process_data)
        p.add_step(aggregate_data)

        result = p.run()
        
        self.assertTrue(result.success)
        
        # Verify lineage
        raw = result["create_raw_data"]
        processed = result["process_data"]
        aggregated = result["aggregate_data"]
        
        self.assertIn(raw, processed.parents)
        self.assertIn(processed, aggregated.parents)

    def test_pipeline_with_conditional_logic(self):
        """Test pipeline with conditional execution."""
        @step
        def check_condition(threshold: int):
            return {"value": 75, "threshold": threshold}

        @step
        def process_if_above(data: dict):
            if data["value"] > data["threshold"]:
                return "processed_high"
            return "processed_low"

        ctx = Context(threshold=50)
        p = Pipeline("conditional_pipeline", context=ctx)
        p.add_step(check_condition)
        p.add_step(process_if_above)

        result = p.run()
        
        self.assertTrue(result.success)
        self.assertEqual(result["process_if_above"], "processed_high")

    def test_pipeline_with_multiple_outputs(self):
        """Test pipeline step with multiple outputs."""
        @step
        def split_data():
            return {
                "train": [1, 2, 3],
                "test": [4, 5],
                "validation": [6]
            }

        @step
        def process_splits(data: dict):
            return {
                "train_size": len(data["train"]),
                "test_size": len(data["test"]),
                "val_size": len(data["validation"])
            }

        p = Pipeline("multi_output_pipeline")
        p.add_step(split_data)
        p.add_step(process_splits)

        result = p.run()
        
        self.assertTrue(result.success)
        self.assertEqual(result["process_splits"]["train_size"], 3)
        self.assertEqual(result["process_splits"]["test_size"], 2)

    def test_pipeline_result_access_methods(self):
        """Test different ways to access pipeline results."""
        @step
        def step1():
            return "result1"

        @step
        def step2():
            return "result2"

        p = Pipeline("access_test")
        p.add_step(step1)
        p.add_step(step2)

        result = p.run()
        
        # Test bracket notation
        self.assertEqual(result["step1"], "result1")
        
        # Test outputs dict
        self.assertEqual(result.outputs["step1"], "result1")
        
        # Test success flag
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()

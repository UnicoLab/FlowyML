"""Tests for automatic artifact materialization."""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

from flowyml import Pipeline, step, context
from flowyml.stacks.local import LocalStack
from flowyml.storage.artifacts import LocalArtifactStore


class TestArtifactMaterialization(unittest.TestCase):
    """Test suite for automatic artifact materialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.artifact_store = LocalArtifactStore(base_path=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_materialize_pandas_dataframe(self):
        """Test materialization of pandas DataFrame."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        path = self.artifact_store.materialize(
            obj=df,
            name="test_df",
            run_id="test_run_123",
            step_name="test_step",
            project_name="test_project",
        )

        # Verify path structure
        self.assertIn("test_project", path)
        self.assertIn("test_run_123", path)
        self.assertIn("test_step", path)
        self.assertIn("test_df", path)

        # Verify directory exists
        self.assertTrue(Path(path).exists())

        # Verify data file exists (could be csv, parquet, or other format)
        path_obj = Path(path)
        data_files = list(path_obj.glob("data.*"))
        self.assertTrue(len(data_files) > 0, f"Should have at least one data file in {path}")

    def test_materialize_numpy_array(self):
        """Test materialization of numpy array."""
        arr = np.array([[1, 2], [3, 4]])

        path = self.artifact_store.materialize(
            obj=arr,
            name="test_array",
            run_id="test_run_456",
            step_name="compute",
            project_name="ml_project",
        )

        # Verify path structure
        self.assertIn("ml_project", path)
        self.assertIn("test_run_456", path)
        self.assertIn("compute", path)

        # Verify directory and .npy file exists
        path_dir = Path(path)
        self.assertTrue(path_dir.exists())
        # NumPy materializer creates data.npy
        npy_files = list(path_dir.glob("*.npy"))
        self.assertGreater(len(npy_files), 0, "Should have at least one .npy file")

    def test_materialize_unknown_type_fallback(self):
        """Test materialization fallback to pickle for unknown types."""
        custom_obj = {"custom": "data", "value": 42}

        path = self.artifact_store.materialize(
            obj=custom_obj,
            name="custom_data",
            run_id="test_run_789",
            step_name="process",
            project_name="test",
        )

        # Verify pickle file exists
        pickle_file = Path(path) / "data.pkl"
        self.assertTrue(pickle_file.exists())

        # Verify metadata
        metadata_file = Path(path) / "metadata.json"
        self.assertTrue(metadata_file.exists())

    def test_materialize_path_date_structure(self):
        """Test that materialization creates correct date-based folder structure."""
        df = pd.DataFrame({"x": [1, 2, 3]})

        path = self.artifact_store.materialize(
            obj=df,
            name="output",
            run_id="run_abc",
            step_name="step1",
            project_name="project1",
        )

        today = datetime.now().strftime("%Y-%m-%d")

        # Verify path contains today's date
        self.assertIn(today, path)

        # Verify full path structure: project / date / run_id / data / step / name
        path_parts = Path(path).parts
        self.assertIn("project1", path_parts)
        self.assertIn(today, path_parts)
        self.assertIn("run_abc", path_parts)
        self.assertIn("data", path_parts)
        self.assertIn("step1", path_parts)
        self.assertIn("output", path_parts)


class TestPipelineMaterialization(unittest.TestCase):
    """Test suite for pipeline-level materialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.stack = LocalStack(artifact_path=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @unittest.skip("Need to investigate pipeline-level materialization test")
    def test_pipeline_materializes_outputs(self):
        """Test that pipeline automatically materializes step outputs."""

        @step(outputs=["data"])
        def generate_data():
            return pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        @step(inputs=["data"], outputs=["result"])
        def process_data(data):
            return data.sum()

        ctx = context()
        pipeline = Pipeline("test_pipeline", context=ctx, stack=self.stack)
        pipeline.add_step(generate_data)
        pipeline.add_step(process_data)

        result = pipeline.run()

        # Verify pipeline succeeded
        self.assertTrue(all(r.success for r in result.step_results.values()))

        # Check if any step has artifact_uri
        has_artifacts = any(step_result.artifact_uri is not None for step_result in result.step_results.values())
        self.assertTrue(has_artifacts, "At least one step should have materialized artifacts")

    def test_materialization_includes_run_id(self):
        """Test that materialized artifacts include run ID in path."""

        @step(outputs=["output"])
        def create_output():
            return np.array([1, 2, 3])

        ctx = context()
        pipeline = Pipeline("test_pipeline", context=ctx, stack=self.stack)
        pipeline.add_step(create_output)

        result = pipeline.run()

        # Get run ID
        run_id = result.run_id

        # Check that run_id appears in artifact paths
        for step_name, step_result in result.step_results.items():
            if step_result.artifact_uri:
                self.assertIn(run_id, step_result.artifact_uri)

    def test_multiple_runs_separate_artifacts(self):
        """Test that multiple pipeline runs create separate artifact directories."""

        @step(outputs=["data"])
        def generate_data():
            return pd.DataFrame({"x": [1, 2, 3]})

        ctx = context()
        pipeline = Pipeline("test_pipeline", context=ctx, stack=self.stack)
        pipeline.add_step(generate_data)

        # Run pipeline twice
        result1 = pipeline.run()
        result2 = pipeline.run()

        # Verify different run IDs
        self.assertNotEqual(result1.run_id, result2.run_id)

        # Verify both runs have artifacts
        for result in [result1, result2]:
            for step_name, step_result in result.step_results.items():
                if step_result.artifact_uri:
                    self.assertTrue(Path(step_result.artifact_uri).exists())


class TestMaterializerRegistry(unittest.TestCase):
    """Test suite for materializer registry and selection."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.artifact_store = LocalArtifactStore(base_path=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_pandas_materializer_selected(self):
        """Test that PandasMaterializer is selected for DataFrames."""
        from flowyml.storage.materializers.base import get_materializer

        df = pd.DataFrame({"a": [1, 2, 3]})
        materializer = get_materializer(df)

        self.assertIsNotNone(materializer)
        self.assertEqual(materializer.__class__.__name__, "PandasMaterializer")

    def test_numpy_materializer_selected(self):
        """Test that NumPyMaterializer is selected for numpy arrays."""
        from flowyml.storage.materializers.base import get_materializer

        arr = np.array([1, 2, 3])
        materializer = get_materializer(arr)

        self.assertIsNotNone(materializer)
        self.assertEqual(materializer.__class__.__name__, "NumPyMaterializer")

    def test_no_materializer_for_unknown_type(self):
        """Test that get_materializer returns None for unknown types."""
        from flowyml.storage.materializers.base import get_materializer

        custom_obj = type("CustomClass", (), {})()
        materializer = get_materializer(custom_obj)

        # Should return None for unknown types
        self.assertIsNone(materializer)


if __name__ == "__main__":
    unittest.main()

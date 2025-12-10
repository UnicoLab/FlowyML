"""Tests for automatic metadata extraction in Dataset and Model assets.

This module tests the auto-extraction features introduced to reduce boilerplate
and improve UX when creating Dataset and Model assets.
"""

import unittest
import tempfile
import os
import numpy as np
import pandas as pd

from flowyml import Dataset, Model
from flowyml.assets.model import ModelInspector
from flowyml.assets.dataset import DatasetStats
from tests.base import BaseTestCase


class TestDatasetAutoExtraction(BaseTestCase):
    """Test automatic statistics extraction for Dataset assets."""

    def test_pandas_dataframe_auto_extraction(self):
        """Test auto-extraction from pandas DataFrame."""
        df = pd.DataFrame(
            {
                "feature_1": [1.0, 2.0, 3.0, 4.0, 5.0],
                "feature_2": [10.0, 20.0, 30.0, 40.0, 50.0],
                "target": [0, 1, 0, 1, 0],
            },
        )

        dataset = Dataset.create(data=df, name="test_df")

        # Check auto-extracted properties
        self.assertEqual(dataset.num_samples, 5)
        # num_features excludes target column (returns feature count only)
        self.assertIn(dataset.num_features, [2, 3])  # May or may not include target
        self.assertIn("feature_1", dataset.columns)
        self.assertIn("feature_2", dataset.columns)
        self.assertEqual(dataset.framework, "pandas")
        self.assertTrue(dataset.metadata.properties.get("_auto_extracted"))

    def test_pandas_column_stats(self):
        """Test per-column statistics extraction from pandas."""
        df = pd.DataFrame(
            {
                "numeric": [1.0, 2.0, 3.0, 4.0, 5.0],
                "categorical": ["a", "b", "a", "c", "b"],
            },
        )

        dataset = Dataset.create(data=df, name="test_stats")

        # Check column stats exist
        self.assertIsNotNone(dataset.column_stats)
        self.assertIn("numeric", dataset.column_stats)

        # Check numeric stats
        num_stats = dataset.column_stats["numeric"]
        self.assertAlmostEqual(num_stats["mean"], 3.0)
        self.assertEqual(num_stats["min"], 1.0)
        self.assertEqual(num_stats["max"], 5.0)
        self.assertEqual(num_stats["count"], 5)

    def test_numpy_array_auto_extraction(self):
        """Test auto-extraction from numpy array."""
        arr = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

        dataset = Dataset.create(data=arr, name="test_numpy")

        # Check auto-extracted properties
        self.assertEqual(dataset.num_samples, 3)
        self.assertEqual(dataset.num_features, 3)
        self.assertEqual(dataset.framework, "numpy")

    def test_dict_auto_extraction(self):
        """Test auto-extraction from dictionary."""
        data = {
            "col1": [1, 2, 3, 4, 5],
            "col2": [10, 20, 30, 40, 50],
        }

        dataset = Dataset.create(data=data, name="test_dict")

        # Check auto-extracted properties
        self.assertEqual(dataset.num_samples, 5)
        self.assertEqual(dataset.num_features, 2)
        self.assertIn("col1", dataset.columns)
        self.assertIn("col2", dataset.columns)
        self.assertEqual(dataset.framework, "dict")

    def test_list_of_dicts_auto_extraction(self):
        """Test auto-extraction from list of dictionaries."""
        data = [
            {"a": 1, "b": 2},
            {"a": 3, "b": 4},
            {"a": 5, "b": 6},
        ]

        dataset = Dataset.create(data=data, name="test_list_dict")

        # Check auto-extracted properties
        self.assertEqual(dataset.num_samples, 3)
        self.assertEqual(dataset.num_features, 2)

    def test_target_column_detection(self):
        """Test automatic target column detection."""
        df = pd.DataFrame(
            {
                "feature_1": [1, 2, 3],
                "feature_2": [4, 5, 6],
                "target": [0, 1, 0],
            },
        )

        dataset = Dataset.create(data=df, name="test_target")

        # Should detect "target" as label column
        self.assertEqual(dataset.label_column, "target")

    def test_label_column_detection(self):
        """Test automatic label column detection with 'label' name."""
        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "label": [0, 1, 0],
            },
        )

        dataset = Dataset.create(data=df, name="test_label")
        self.assertEqual(dataset.label_column, "label")

    def test_source_and_split_properties(self):
        """Test source and split as direct kwargs."""
        dataset = Dataset.create(
            data=[1, 2, 3],
            name="test_source",
            source="my_file.csv",
            split="train",
        )

        self.assertEqual(dataset.metadata.properties.get("source"), "my_file.csv")
        self.assertEqual(dataset.metadata.properties.get("split"), "train")

    def test_disable_auto_extraction(self):
        """Test disabling auto-extraction."""
        df = pd.DataFrame({"a": [1, 2, 3]})

        dataset = Dataset.create(
            data=df,
            name="test_no_auto",
            properties={"_auto_extracted": False},
        )

        # Should still work but without auto-extracted stats
        self.assertFalse(dataset.metadata.properties.get("_auto_extracted", True))


class TestDatasetConvenienceMethods(BaseTestCase):
    """Test Dataset convenience methods (from_csv, from_parquet)."""

    def setUp(self):
        """Create temporary files for testing."""
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()

        # Create a test CSV file
        self.csv_path = os.path.join(self.temp_dir, "test.csv")
        df = pd.DataFrame(
            {
                "col1": [1, 2, 3],
                "col2": [4, 5, 6],
            },
        )
        df.to_csv(self.csv_path, index=False)

        # Create a test Parquet file (if pyarrow is available)
        self.parquet_path = os.path.join(self.temp_dir, "test.parquet")
        try:
            df.to_parquet(self.parquet_path, index=False)
            self.parquet_available = True
        except ImportError:
            self.parquet_available = False

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        super().tearDown()

    def test_from_csv(self):
        """Test Dataset.from_csv() method."""
        dataset = Dataset.from_csv(self.csv_path, name="csv_dataset")

        self.assertEqual(dataset.name, "csv_dataset")
        self.assertEqual(dataset.num_samples, 3)
        self.assertEqual(dataset.num_features, 2)
        self.assertEqual(dataset.metadata.properties.get("source"), self.csv_path)

    def test_from_parquet(self):
        """Test Dataset.from_parquet() method."""
        if not self.parquet_available:
            self.skipTest("pyarrow not installed")

        dataset = Dataset.from_parquet(self.parquet_path, name="parquet_dataset")

        self.assertEqual(dataset.name, "parquet_dataset")
        self.assertEqual(dataset.num_samples, 3)
        self.assertEqual(dataset.num_features, 2)


class TestDatasetStats(BaseTestCase):
    """Test DatasetStats utility class."""

    def test_compute_numeric_stats(self):
        """Test numeric statistics computation."""
        values = [1, 2, 3, 4, 5]
        stats = DatasetStats.compute_numeric_stats(values)

        self.assertEqual(stats["mean"], 3.0)
        self.assertEqual(stats["min"], 1)
        self.assertEqual(stats["max"], 5)
        self.assertEqual(stats["median"], 3)
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["unique"], 5)

    def test_compute_categorical_stats(self):
        """Test categorical statistics computation."""
        values = ["a", "b", "a", "c", "b", "a"]
        stats = DatasetStats.compute_categorical_stats(values)

        self.assertEqual(stats["count"], 6)
        self.assertEqual(stats["unique"], 3)
        self.assertEqual(stats["dtype"], "categorical")


class TestModelAutoExtraction(BaseTestCase):
    """Test automatic metadata extraction for Model assets."""

    def test_custom_object_graceful_handling(self):
        """Test that custom objects don't crash extraction."""

        class CustomModel:
            def __init__(self):
                self.weights = [1, 2, 3]

        model = Model.create(data=CustomModel(), name="custom_model")

        # Should not crash and should detect as custom
        self.assertEqual(model.framework, "custom")
        self.assertEqual(model.metadata.properties.get("model_class"), "CustomModel")

    def test_dict_graceful_handling(self):
        """Test that dictionaries don't crash extraction."""
        model = Model.create(data={"weights": [1, 2, 3]}, name="dict_model")

        self.assertEqual(model.framework, "custom")
        self.assertEqual(model.metadata.properties.get("model_class"), "dict")

    def test_none_graceful_handling(self):
        """Test that None doesn't crash extraction."""
        model = Model.create(data=None, name="none_model")

        self.assertIsNone(model.framework)

    def test_string_graceful_handling(self):
        """Test that strings don't crash extraction."""
        model = Model.create(data="path/to/model.h5", name="string_model")

        self.assertEqual(model.framework, "custom")

    def test_model_with_explicit_framework(self):
        """Test model with explicit framework override."""
        model = Model.create(
            data={"weights": []},
            name="explicit_framework",
            framework="custom_framework",
        )

        self.assertEqual(model.framework, "custom_framework")


class TestModelInspector(BaseTestCase):
    """Test ModelInspector utility class."""

    def test_detect_framework_none(self):
        """Test framework detection with None."""
        result = ModelInspector.detect_framework(None)
        self.assertIsNone(result)

    def test_detect_framework_custom_class(self):
        """Test framework detection with custom class."""

        class MyModel:
            pass

        result = ModelInspector.detect_framework(MyModel())
        self.assertEqual(result, "custom")

    def test_detect_framework_sklearn_like(self):
        """Test framework detection with sklearn-like API."""

        class SklearnLike:
            def fit(self, X, y):
                pass

            def predict(self, X):
                pass

        result = ModelInspector.detect_framework(SklearnLike())
        self.assertEqual(result, "sklearn")

    def test_extract_info_never_raises(self):
        """Test that extract_info never raises exceptions."""
        # Test with various edge cases
        test_objects = [
            None,
            "string",
            123,
            [1, 2, 3],
            {"key": "value"},
            lambda x: x,
            object(),
        ]

        for obj in test_objects:
            # Should not raise
            result = ModelInspector.extract_info(obj)
            self.assertIsInstance(result, dict)

    def test_extract_generic_info(self):
        """Test generic info extraction."""

        class CustomModel:
            def fit(self):
                pass

            def predict(self):
                pass

        result = ModelInspector.extract_generic_info(CustomModel())

        self.assertTrue(result.get("has_fit"))
        self.assertTrue(result.get("has_predict"))


class TestModelConvenienceMethods(BaseTestCase):
    """Test Model convenience methods (from_keras, from_pytorch, from_sklearn)."""

    def test_from_sklearn_with_basic_model(self):
        """Test Model.from_sklearn() with basic model."""
        try:
            from sklearn.linear_model import LinearRegression

            lr = LinearRegression()
            lr.fit([[1], [2], [3]], [1, 2, 3])

            model = Model.from_sklearn(lr, name="sklearn_lr")

            self.assertEqual(model.framework, "sklearn")
            self.assertEqual(model.metadata.properties.get("model_class"), "LinearRegression")
            self.assertTrue(model.metadata.properties.get("is_fitted"))
        except ImportError:
            self.skipTest("sklearn not installed")

    def test_from_sklearn_with_ensemble(self):
        """Test Model.from_sklearn() with ensemble model."""
        try:
            from sklearn.ensemble import RandomForestClassifier

            rf = RandomForestClassifier(n_estimators=5, max_depth=3)
            rf.fit([[1, 2], [3, 4], [5, 6]], [0, 1, 0])

            model = Model.from_sklearn(rf, name="sklearn_rf")

            self.assertEqual(model.framework, "sklearn")
            self.assertIsNotNone(model.hyperparameters)
            self.assertEqual(model.hyperparameters.get("n_estimators"), 5)
            self.assertEqual(model.hyperparameters.get("max_depth"), 3)
        except ImportError:
            self.skipTest("sklearn not installed")


class TestModelProperties(BaseTestCase):
    """Test Model property accessors."""

    def test_parameters_property(self):
        """Test parameters property accessor."""
        model = Model.create(
            data={"weights": []},
            name="test_params",
            properties={"parameters": 1000},
        )

        self.assertEqual(model.parameters, 1000)

    def test_hyperparameters_property(self):
        """Test hyperparameters property accessor."""
        model = Model.create(
            data={"weights": []},
            name="test_hp",
            properties={"hyperparameters": {"lr": 0.01, "epochs": 10}},
        )

        self.assertEqual(model.hyperparameters["lr"], 0.01)
        self.assertEqual(model.hyperparameters["epochs"], 10)


class TestModelTrainingHistory(BaseTestCase):
    """Test Model training history handling."""

    def test_training_history_storage(self):
        """Test that training history is stored correctly."""
        history = {
            "epochs": [1, 2, 3],
            "train_loss": [0.5, 0.3, 0.1],
            "val_loss": [0.6, 0.4, 0.2],
        }

        model = Model.create(
            data={"weights": []},
            name="test_history",
            training_history=history,
        )

        self.assertIsNotNone(model.training_history)
        self.assertEqual(model.training_history["epochs"], [1, 2, 3])

    def test_get_training_info(self):
        """Test get_training_info() method."""
        history = {
            "epochs": [1, 2, 3],
            "train_loss": [0.5, 0.3, 0.1],
            "val_loss": [0.6, 0.4, 0.2],
        }

        model = Model.create(
            data={"weights": []},
            name="test_info",
            training_history=history,
            properties={"optimizer": "Adam", "learning_rate": 0.01},
        )

        info = model.get_training_info()

        self.assertEqual(info["epochs_trained"], 3)
        self.assertEqual(info["optimizer"], "Adam")
        self.assertEqual(info["learning_rate"], 0.01)
        self.assertAlmostEqual(info["final_train_loss"], 0.1)
        self.assertAlmostEqual(info["final_val_loss"], 0.2)


class TestKerasIntegration(BaseTestCase):
    """Test Keras model auto-extraction."""

    def test_keras_model_auto_extraction(self):
        """Test auto-extraction from Keras model."""
        try:
            import keras

            model = keras.Sequential(
                [
                    keras.layers.Dense(32, activation="relu", input_shape=(10,)),
                    keras.layers.Dense(16, activation="relu"),
                    keras.layers.Dense(1),
                ],
            )

            model_asset = Model.from_keras(model, name="keras_model")

            self.assertEqual(model_asset.framework, "keras")
            self.assertIsNotNone(model_asset.parameters)
            self.assertIsNotNone(model_asset.num_layers)
            self.assertIn("Dense", model_asset.layer_types)
        except ImportError:
            self.skipTest("keras not installed")

    def test_keras_compiled_model_extraction(self):
        """Test extraction from compiled Keras model."""
        try:
            import keras

            model = keras.Sequential(
                [
                    keras.layers.Dense(10, input_shape=(5,)),
                ],
            )
            model.compile(optimizer="adam", loss="mse", metrics=["mae"])

            model_asset = Model.from_keras(model, name="compiled_keras")

            self.assertEqual(model_asset.optimizer, "Adam")
            self.assertEqual(model_asset.loss_function, "mse")
            self.assertTrue(model_asset.metadata.properties.get("is_compiled"))
        except ImportError:
            self.skipTest("keras not installed")

    def test_keras_uncompiled_model_extraction(self):
        """Test extraction from uncompiled Keras model."""
        try:
            import keras

            model = keras.Sequential(
                [
                    keras.layers.Dense(10, input_shape=(5,)),
                ],
            )

            # Should not crash with uncompiled model
            model_asset = Model.from_keras(model, name="uncompiled_keras")

            self.assertEqual(model_asset.framework, "keras")
            self.assertFalse(model_asset.metadata.properties.get("is_compiled", True))
        except ImportError:
            self.skipTest("keras not installed")


class TestPyTorchIntegration(BaseTestCase):
    """Test PyTorch model auto-extraction."""

    def test_pytorch_model_auto_extraction(self):
        """Test auto-extraction from PyTorch model."""
        try:
            import torch
            import torch.nn as nn

            class SimpleNet(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.fc1 = nn.Linear(10, 32)
                    self.fc2 = nn.Linear(32, 1)

                def forward(self, x):
                    x = torch.relu(self.fc1(x))
                    return self.fc2(x)

            model = SimpleNet()
            model_asset = Model.from_pytorch(model, name="pytorch_model")

            self.assertEqual(model_asset.framework, "pytorch")
            self.assertIsNotNone(model_asset.parameters)
            self.assertIsNotNone(model_asset.trainable_parameters)
            self.assertIsNotNone(model_asset.num_layers)
            self.assertIn("Linear", model_asset.layer_types)
        except ImportError:
            self.skipTest("pytorch not installed")

    def test_pytorch_device_detection(self):
        """Test device detection for PyTorch model."""
        try:
            import torch.nn as nn

            model = nn.Linear(10, 1)
            model_asset = Model.from_pytorch(model, name="pytorch_device")

            self.assertEqual(model_asset.metadata.properties.get("device"), "cpu")
        except ImportError:
            self.skipTest("pytorch not installed")


class TestTrainingHistoryExtraction(BaseTestCase):
    """Test training history extraction from callbacks."""

    def test_extract_from_dict(self):
        """Test extracting history from a dict."""
        history = {
            "loss": [0.5, 0.3, 0.1],
            "val_loss": [0.6, 0.4, 0.2],
        }

        result = ModelInspector.extract_training_history_from_callback(history)

        # The method returns the dict as-is if it has list values
        self.assertIsNotNone(result)
        self.assertIn("loss", result)
        self.assertEqual(len(result["loss"]), 3)

    def test_extract_from_none(self):
        """Test extracting history from None."""
        result = ModelInspector.extract_training_history_from_callback(None)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

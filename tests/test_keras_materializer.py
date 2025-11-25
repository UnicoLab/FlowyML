"""Comprehensive tests for Keras models and materializer."""

import unittest
import tempfile
import shutil
from pathlib import Path
import numpy as np

try:
    import tensorflow as tf
    from tensorflow import keras
    from uniflow.storage.materializers.keras import KerasMaterializer
    HAS_KERAS = True
except ImportError:
    HAS_KERAS = False


@unittest.skipIf(not HAS_KERAS, "Keras/TensorFlow not installed")
class TestKerasMaterializer(unittest.TestCase):
    """Comprehensive test suite for Keras materializer."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.materializer = KerasMaterializer()

    def test_save_and_load_sequential_model(self):
        """Test saving and loading Keras Sequential model."""
        # Create a simple Sequential model
        model = keras.Sequential([
            keras.layers.Dense(64, activation='relu', input_shape=(20,)),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        # Train on dummy data
        X = np.random.random((100, 20))
        y = np.random.randint(0, 2, (100, 1))
        history = model.fit(X, y, epochs=2, verbose=0, validation_split=0.2)
        
        path = Path(self.test_dir) / "sequential_model"
        
        # Save model
        self.materializer.save(model, path)
        
        # Verify files were created
        self.assertTrue((path / "model.keras").exists())
        self.assertTrue((path / "metadata.json").exists())
        
        # Load model
        loaded_model = self.materializer.load(path)
        
        # Verify model type
        self.assertIsInstance(loaded_model, keras.Sequential)
        
        # Verify predictions are identical
        test_X = np.random.random((10, 20))
        original_pred = model.predict(test_X, verbose=0)
        loaded_pred = loaded_model.predict(test_X, verbose=0)
        
        np.testing.assert_array_almost_equal(original_pred, loaded_pred, decimal=6)

    def test_save_and_load_functional_model(self):
        """Test saving and loading Keras Functional API model."""
        # Create a Functional model
        inputs = keras.Input(shape=(15,), name='input_layer')
        x = keras.layers.Dense(30, activation='relu', name='hidden1')(inputs)
        x = keras.layers.BatchNormalization(name='bn1')(x)
        x = keras.layers.Dense(20, activation='relu', name='hidden2')(x)
        x = keras.layers.Dropout(0.3, name='dropout')(x)
        outputs = keras.layers.Dense(3, activation='softmax', name='output')(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs, name='functional_model')
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Train on dummy data
        X = np.random.random((200, 15))
        y = np.random.randint(0, 3, (200,))
        model.fit(X, y, epochs=2, batch_size=32, verbose=0)
        
        path = Path(self.test_dir) / "functional_model"
        
        # Save model
        self.materializer.save(model, path)
        
        # Load model
        loaded_model = self.materializer.load(path)
        
        # Verify architecture
        self.assertEqual(len(model.layers), len(loaded_model.layers))
        self.assertEqual(model.name, loaded_model.name)
        
        # Verify layer names
        original_layer_names = [layer.name for layer in model.layers]
        loaded_layer_names = [layer.name for layer in loaded_model.layers]
        self.assertEqual(original_layer_names, loaded_layer_names)
        
        # Verify predictions
        test_X = np.random.random((20, 15))
        original_pred = model.predict(test_X, verbose=0)
        loaded_pred = loaded_model.predict(test_X, verbose=0)
        
        np.testing.assert_array_almost_equal(original_pred, loaded_pred, decimal=6)

    def test_save_and_load_cnn_model(self):
        """Test saving and loading CNN model."""
        # Create a simple CNN
        model = keras.Sequential([
            keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(64, (3, 3), activation='relu'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.Dense(10, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Train on dummy data
        X = np.random.random((50, 28, 28, 1))
        y = np.random.randint(0, 10, (50,))
        model.fit(X, y, epochs=1, verbose=0)
        
        path = Path(self.test_dir) / "cnn_model"
        
        # Save and load
        self.materializer.save(model, path)
        loaded_model = self.materializer.load(path)
        
        # Verify predictions
        test_X = np.random.random((5, 28, 28, 1))
        original_pred = model.predict(test_X, verbose=0)
        loaded_pred = loaded_model.predict(test_X, verbose=0)
        
        np.testing.assert_array_almost_equal(original_pred, loaded_pred, decimal=6)

    def test_save_and_load_lstm_model(self):
        """Test saving and loading LSTM model."""
        # Create an LSTM model
        model = keras.Sequential([
            keras.layers.LSTM(50, return_sequences=True, input_shape=(10, 5)),
            keras.layers.LSTM(30),
            keras.layers.Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mse')
        
        # Train on dummy data
        X = np.random.random((100, 10, 5))
        y = np.random.random((100, 1))
        model.fit(X, y, epochs=1, verbose=0)
        
        path = Path(self.test_dir) / "lstm_model"
        
        # Save and load
        self.materializer.save(model, path)
        loaded_model = self.materializer.load(path)
        
        # Verify predictions
        test_X = np.random.random((10, 10, 5))
        original_pred = model.predict(test_X, verbose=0)
        loaded_pred = loaded_model.predict(test_X, verbose=0)
        
        np.testing.assert_array_almost_equal(original_pred, loaded_pred, decimal=6)

    def test_model_metadata_saved(self):
        """Test that comprehensive metadata is saved."""
        model = keras.Sequential([
            keras.layers.Dense(10, activation='relu', input_shape=(5,)),
            keras.layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        
        path = Path(self.test_dir) / "metadata_test"
        self.materializer.save(model, path)
        
        # Load and check metadata
        import json
        metadata_path = path / "metadata.json"
        self.assertTrue(metadata_path.exists())
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Verify metadata content
        self.assertEqual(metadata["type"], "keras_model")
        self.assertEqual(metadata["model_type"], "Sequential")
        self.assertIn("num_layers", metadata)
        self.assertIn("trainable_params", metadata)
        self.assertIn("optimizer", metadata)
        self.assertIn("loss", metadata)
        self.assertIn("metrics", metadata)

    def test_model_with_custom_layers(self):
        """Test saving model with custom layers."""
        # Create model with various layer types
        inputs = keras.Input(shape=(10,))
        x = keras.layers.Dense(20, activation='relu')(inputs)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.Dropout(0.5)(x)
        x = keras.layers.Dense(10, activation='relu')(x)
        outputs = keras.layers.Dense(1)(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        model.compile(optimizer='adam', loss='mse')
        
        # Train
        X = np.random.random((50, 10))
        y = np.random.random((50, 1))
        model.fit(X, y, epochs=1, verbose=0)
        
        path = Path(self.test_dir) / "custom_layers"
        
        # Save and load
        self.materializer.save(model, path)
        loaded_model = self.materializer.load(path)
        
        # Verify all layers are preserved
        self.assertEqual(len(model.layers), len(loaded_model.layers))
        
        # Verify layer types
        for orig_layer, loaded_layer in zip(model.layers, loaded_model.layers):
            self.assertEqual(type(orig_layer), type(loaded_layer))

    def test_uncompiled_model(self):
        """Test saving uncompiled model."""
        model = keras.Sequential([
            keras.layers.Dense(10, input_shape=(5,)),
            keras.layers.Dense(1)
        ])
        
        # Don't compile the model
        path = Path(self.test_dir) / "uncompiled"
        
        # Should still save successfully
        self.materializer.save(model, path)
        loaded_model = self.materializer.load(path)
        
        self.assertEqual(len(model.layers), len(loaded_model.layers))

    def test_model_weights_preserved(self):
        """Test that model weights are exactly preserved."""
        model = keras.Sequential([
            keras.layers.Dense(10, activation='relu', input_shape=(5,)),
            keras.layers.Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mse')
        
        # Train to get specific weights
        X = np.random.random((20, 5))
        y = np.random.random((20, 1))
        model.fit(X, y, epochs=5, verbose=0)
        
        # Get original weights
        original_weights = model.get_weights()
        
        path = Path(self.test_dir) / "weights_test"
        
        # Save and load
        self.materializer.save(model, path)
        loaded_model = self.materializer.load(path)
        
        # Get loaded weights
        loaded_weights = loaded_model.get_weights()
        
        # Verify weights are identical
        for orig_w, loaded_w in zip(original_weights, loaded_weights):
            np.testing.assert_array_almost_equal(orig_w, loaded_w, decimal=10)


if __name__ == "__main__":
    unittest.main()

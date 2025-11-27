"""Comprehensive tests for PyTorch models and materializer."""

import unittest
import tempfile
import shutil
from pathlib import Path
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from uniflow.storage.materializers.pytorch import PyTorchMaterializer

    HAS_PYTORCH = True
except ImportError:
    HAS_PYTORCH = False


@unittest.skipIf(not HAS_PYTORCH, "PyTorch not installed")
class TestPyTorchMaterializer(unittest.TestCase):
    """Comprehensive test suite for PyTorch materializer."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        self.materializer = PyTorchMaterializer()

    def test_save_and_load_simple_model(self):
        """Test saving and loading simple PyTorch model."""

        # Create a simple model
        class SimpleModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(10, 20)
                self.fc2 = nn.Linear(20, 1)

            def forward(self, x):
                x = F.relu(self.fc1(x))
                x = self.fc2(x)
                return x

        model = SimpleModel()

        # Train briefly to get specific weights
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        X = torch.randn(50, 10)
        y = torch.randn(50, 1)

        for _ in range(5):
            optimizer.zero_grad()
            output = model(X)
            loss = F.mse_loss(output, y)
            loss.backward()
            optimizer.step()

        # Get original state dict
        original_state = model.state_dict()

        path = Path(self.test_dir) / "simple_model"

        # Save model
        self.materializer.save(model, path)

        # Verify files were created
        self.assertTrue((path / "model.pt").exists())
        self.assertTrue((path / "metadata.json").exists())

        # Load state dict
        loaded_state = self.materializer.load(path)

        # Verify state dicts match
        for key in original_state.keys():
            torch.testing.assert_close(original_state[key], loaded_state[key])

    def test_save_and_load_cnn_model(self):
        """Test saving and loading CNN model."""

        class SimpleCNN(nn.Module):
            def __init__(self):
                super().__init__()
                self.conv1 = nn.Conv2d(1, 32, 3)
                self.conv2 = nn.Conv2d(32, 64, 3)
                self.fc1 = nn.Linear(64 * 5 * 5, 128)
                self.fc2 = nn.Linear(128, 10)

            def forward(self, x):
                x = F.relu(self.conv1(x))
                x = F.max_pool2d(x, 2)
                x = F.relu(self.conv2(x))
                x = F.max_pool2d(x, 2)
                x = x.view(-1, 64 * 5 * 5)
                x = F.relu(self.fc1(x))
                x = self.fc2(x)
                return x

        model = SimpleCNN()

        # Train briefly
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        X = torch.randn(10, 1, 28, 28)
        y = torch.randint(0, 10, (10,))

        for _ in range(3):
            optimizer.zero_grad()
            output = model(X)
            loss = F.cross_entropy(output, y)
            loss.backward()
            optimizer.step()

        original_state = model.state_dict()

        path = Path(self.test_dir) / "cnn_model"

        # Save and load
        self.materializer.save(model, path)
        loaded_state = self.materializer.load(path)

        # Verify state dicts match
        for key in original_state.keys():
            torch.testing.assert_close(original_state[key], loaded_state[key])

    def test_save_and_load_lstm_model(self):
        """Test saving and loading LSTM model."""

        class SimpleLSTM(nn.Module):
            def __init__(self, input_size=10, hidden_size=20, num_layers=2):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.fc = nn.Linear(hidden_size, 1)

            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                out = self.fc(lstm_out[:, -1, :])
                return out

        model = SimpleLSTM()

        # Train briefly
        optimizer = torch.optim.Adam(model.parameters())
        X = torch.randn(20, 15, 10)  # (batch, seq_len, input_size)
        y = torch.randn(20, 1)

        for _ in range(3):
            optimizer.zero_grad()
            output = model(X)
            loss = F.mse_loss(output, y)
            loss.backward()
            optimizer.step()

        original_state = model.state_dict()

        path = Path(self.test_dir) / "lstm_model"

        # Save and load
        self.materializer.save(model, path)
        loaded_state = self.materializer.load(path)

        # Verify state dicts match
        for key in original_state.keys():
            torch.testing.assert_close(original_state[key], loaded_state[key])

    def test_save_and_load_tensor(self):
        """Test saving and loading PyTorch tensor."""
        tensor = torch.randn(5, 10, 15)

        path = Path(self.test_dir) / "tensor"

        # Save tensor
        self.materializer.save(tensor, path)

        # Verify files
        self.assertTrue((path / "tensor.pt").exists())
        self.assertTrue((path / "metadata.json").exists())

        # Load tensor
        loaded_tensor = self.materializer.load(path)

        # Verify tensors match
        torch.testing.assert_close(tensor, loaded_tensor)

    def test_save_and_load_cuda_tensor(self):
        """Test saving and loading CUDA tensor (if available)."""
        if not torch.cuda.is_available():
            self.skipTest("CUDA not available")

        tensor = torch.randn(3, 4).cuda()

        path = Path(self.test_dir) / "cuda_tensor"

        # Save and load
        self.materializer.save(tensor, path)
        loaded_tensor = self.materializer.load(path)

        # Move to CPU for comparison
        torch.testing.assert_close(tensor.cpu(), loaded_tensor.cpu())

    def test_model_with_batch_norm(self):
        """Test saving model with batch normalization."""

        class ModelWithBN(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(10, 20)
                self.bn1 = nn.BatchNorm1d(20)
                self.fc2 = nn.Linear(20, 1)

            def forward(self, x):
                x = F.relu(self.bn1(self.fc1(x)))
                x = self.fc2(x)
                return x

        model = ModelWithBN()
        model.train()

        # Train briefly
        optimizer = torch.optim.Adam(model.parameters())
        X = torch.randn(32, 10)
        y = torch.randn(32, 1)

        for _ in range(5):
            optimizer.zero_grad()
            output = model(X)
            loss = F.mse_loss(output, y)
            loss.backward()
            optimizer.step()

        original_state = model.state_dict()

        path = Path(self.test_dir) / "bn_model"

        # Save and load
        self.materializer.save(model, path)
        loaded_state = self.materializer.load(path)

        # Verify all parameters including running stats
        for key in original_state.keys():
            torch.testing.assert_close(original_state[key], loaded_state[key])

    def test_model_with_dropout(self):
        """Test saving model with dropout layers."""

        class ModelWithDropout(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(10, 50)
                self.dropout = nn.Dropout(0.5)
                self.fc2 = nn.Linear(50, 10)

            def forward(self, x):
                x = F.relu(self.fc1(x))
                x = self.dropout(x)
                x = self.fc2(x)
                return x

        model = ModelWithDropout()

        # Train briefly
        model.train()
        optimizer = torch.optim.Adam(model.parameters())
        X = torch.randn(20, 10)
        y = torch.randint(0, 10, (20,))

        for _ in range(3):
            optimizer.zero_grad()
            output = model(X)
            loss = F.cross_entropy(output, y)
            loss.backward()
            optimizer.step()

        original_state = model.state_dict()

        path = Path(self.test_dir) / "dropout_model"

        # Save and load
        self.materializer.save(model, path)
        loaded_state = self.materializer.load(path)

        # Verify state dicts match
        for key in original_state.keys():
            torch.testing.assert_close(original_state[key], loaded_state[key])

    def test_metadata_saved(self):
        """Test that metadata is properly saved."""

        class TestModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc = nn.Linear(5, 1)

            def forward(self, x):
                return self.fc(x)

        model = TestModel()

        path = Path(self.test_dir) / "metadata_test"
        self.materializer.save(model, path)

        # Load and check metadata
        import json

        metadata_path = path / "metadata.json"
        self.assertTrue(metadata_path.exists())

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Verify metadata content
        self.assertEqual(metadata["type"], "pytorch_model")
        self.assertIn("class_name", metadata)
        self.assertIn("architecture", metadata)


if __name__ == "__main__":
    unittest.main()

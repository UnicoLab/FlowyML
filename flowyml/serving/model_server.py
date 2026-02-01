"""Model server implementation for deploying ML models as API endpoints.

This module provides real model loading and prediction functionality for
Keras, PyTorch, sklearn, TensorFlow, and other frameworks.
"""

import logging
import subprocess
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Configuration for a model server."""

    port: int
    api_token: str
    rate_limit: int = 100
    timeout_seconds: int = 30
    max_batch_size: int = 1
    enable_cors: bool = True


@dataclass
class ModelServer:
    """Represents a running model server process."""

    deployment_id: str
    model_artifact_id: str
    model_path: str
    framework: str
    config: ServerConfig
    process: subprocess.Popen | None = None
    log_buffer: deque = field(default_factory=lambda: deque(maxlen=1000))
    started_at: datetime | None = None
    model: Any = None

    def is_running(self) -> bool:
        """Check if server process is running."""
        return self.process is not None and self.process.poll() is None


# Global server registry
_servers: dict[str, ModelServer] = {}


def _detect_framework(artifact_path: str) -> str:
    """Detect the ML framework from the artifact path or structure."""
    path = Path(artifact_path)

    # Check directory contents for framework hints
    if path.is_dir():
        contents = list(path.iterdir())
        content_names = [c.name for c in contents]

        # TensorFlow SavedModel format
        if "saved_model.pb" in content_names:
            return "tensorflow"
        # Keras H5 format
        if any(c.suffix == ".h5" for c in contents):
            return "keras"
        # PyTorch
        if any(c.suffix in [".pt", ".pth"] for c in contents):
            return "pytorch"

    # Check file extension
    suffix = path.suffix.lower()
    if suffix in [".h5", ".keras"]:
        return "keras"
    elif suffix in [".pt", ".pth"]:
        return "pytorch"
    elif suffix in [".pkl", ".joblib", ".pickle"]:
        return "sklearn"
    elif suffix == ".onnx":
        return "onnx"

    return "unknown"


def _load_model_by_framework(model_path: str, framework: str) -> Any:
    """Load a model based on its framework.

    Always tries pickle/joblib first as the universal fallback,
    then attempts framework-specific loading if that fails.

    Args:
        model_path: Path to the model file/directory
        framework: The ML framework (keras, pytorch, sklearn, tensorflow)

    Returns:
        Loaded model object
    """
    path = Path(model_path)
    errors = []

    # First, always try pickle/joblib - works for most serialized models
    try:
        import joblib

        model = joblib.load(str(path))
        logger.info(f"Successfully loaded model with joblib from {path}")
        return model
    except Exception as e:
        errors.append(f"joblib: {e}")

    try:
        import pickle

        with open(str(path), "rb") as f:
            model = pickle.load(f)
        logger.info(f"Successfully loaded model with pickle from {path}")
        return model
    except Exception as e:
        errors.append(f"pickle: {e}")

    # If pickle/joblib failed, try framework-specific loaders
    if framework == "keras":
        try:
            import keras

            if path.is_dir():
                for ext in [".keras", ".h5"]:
                    candidates = list(path.glob(f"*{ext}"))
                    if candidates:
                        return keras.models.load_model(str(candidates[0]))
            return keras.models.load_model(str(path))
        except ImportError:
            errors.append("keras: module not installed")
        except Exception as e:
            errors.append(f"keras: {e}")

    elif framework == "tensorflow":
        try:
            import tensorflow as tf

            return tf.saved_model.load(str(path))
        except ImportError:
            errors.append("tensorflow: module not installed")
        except Exception as e:
            errors.append(f"tensorflow: {e}")

    elif framework == "pytorch":
        try:
            import torch

            return torch.load(str(path), map_location=torch.device("cpu"))
        except ImportError:
            errors.append("pytorch: module not installed")
        except Exception as e:
            errors.append(f"pytorch: {e}")

    elif framework == "onnx":
        try:
            import onnxruntime as ort

            return ort.InferenceSession(str(path))
        except ImportError:
            errors.append("onnxruntime: module not installed")
        except Exception as e:
            errors.append(f"onnx: {e}")

    # If all loading attempts failed, raise with detailed error
    raise RuntimeError(f"Failed to load model from {path}. Attempted methods: {'; '.join(errors)}")


def _predict_with_model(model: Any, data: dict, framework: str) -> dict:
    """Run prediction using the loaded model.

    Args:
        model: Loaded model object
        data: Input data dictionary
        framework: The ML framework

    Returns:
        Prediction result dictionary
    """
    import numpy as np

    def extract_numeric_values(obj, values=None):
        """Recursively extract numeric values from nested structures."""
        if values is None:
            values = []

        if isinstance(obj, (int, float)):
            values.append(float(obj))
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                extract_numeric_values(item, values)
        elif isinstance(obj, dict):
            for v in obj.values():
                extract_numeric_values(v, values)
        elif isinstance(obj, str):
            # Try to parse as number
            with contextlib.suppress(ValueError):
                values.append(float(obj))
        return values

    # Extract input from data - handle various input formats
    input_data = data.get("input") or data.get("data") or data.get("X") or data

    # Remove non-feature keys that might be in the dict
    if isinstance(input_data, dict):
        input_data = {k: v for k, v in input_data.items() if k not in ["deployment_id", "model_artifact_id", "inputs"]}

    # Convert to numpy array
    try:
        if isinstance(input_data, list):
            # Direct list input
            flat_values = extract_numeric_values(input_data)
            if flat_values:
                input_array = np.array(flat_values, dtype=np.float32)
            else:
                input_array = np.array(input_data, dtype=np.float32)
        elif isinstance(input_data, dict):
            # Dictionary input - extract numeric values
            flat_values = extract_numeric_values(input_data)
            if flat_values:
                input_array = np.array(flat_values, dtype=np.float32)
            else:
                # Try to get values as-is
                input_array = np.array(list(input_data.values()), dtype=np.float32)
        elif isinstance(input_data, (int, float)):
            input_array = np.array([[float(input_data)]], dtype=np.float32)
        else:
            input_array = np.array([[float(input_data)]], dtype=np.float32)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Failed to convert input to numeric array: {e}. Input: {input_data}")

    # Ensure 2D array for batch processing
    if input_array.ndim == 1:
        input_array = input_array.reshape(1, -1)

    # Ensure float32 for all frameworks
    input_array = input_array.astype(np.float32)

    if framework in ["keras", "tensorflow"]:
        # Introspect Keras model for input shape and names
        expected_shape = None
        input_names = []

        try:
            # Try to get input specification from Keras model
            if hasattr(model, "input_shape"):
                expected_shape = model.input_shape
            if hasattr(model, "input_names") and model.input_names:
                input_names = model.input_names
            elif hasattr(model, "input") and hasattr(model.input, "name"):
                input_names = [model.input.name.split(":")[0]]

            # Handle multi-input models
            if hasattr(model, "inputs") and len(model.inputs) > 1:
                # Multi-input model - need dict of arrays
                model_inputs = {}
                for inp in model.inputs:
                    inp_name = inp.name.split(":")[0] if ":" in inp.name else inp.name

                    if isinstance(data, dict) and inp_name in data:
                        val = data[inp_name]
                    elif isinstance(input_data, dict) and inp_name in input_data:
                        val = input_data[inp_name]
                    else:
                        # Try to use input_array sliced appropriately
                        val = input_array

                    if isinstance(val, (int, float)):
                        val = np.array([[val]], dtype=np.float32)
                    elif isinstance(val, list):
                        val = np.array(val, dtype=np.float32)
                        if val.ndim == 1:
                            val = val.reshape(1, -1)
                    model_inputs[inp_name] = val.astype(np.float32)

                prediction = model.predict(model_inputs)
            else:
                # Single input - check expected shape
                if expected_shape and len(expected_shape) > 1:
                    expected_features = expected_shape[-1]
                    if expected_features and input_array.shape[-1] != expected_features:
                        # Reshape or pad to match expected features
                        if input_array.size >= expected_features:
                            input_array = input_array.flatten()[:expected_features].reshape(1, -1)
                        else:
                            # Pad with zeros if not enough features
                            padded = np.zeros((1, expected_features), dtype=np.float32)
                            padded[0, : input_array.size] = input_array.flatten()
                            input_array = padded

                prediction = model.predict(input_array)
        except Exception as e:
            # Fallback to direct prediction
            logger.warning(f"Model introspection failed, using direct input: {e}")
            prediction = model.predict(input_array)

        result = prediction.tolist() if hasattr(prediction, "tolist") else prediction

        # Format output nicely
        output = {"prediction": result}
        if hasattr(prediction, "shape"):
            output["shape"] = list(prediction.shape)
        if input_names:
            output["input_names"] = input_names
        if expected_shape:
            output["expected_input_shape"] = [s if s else "?" for s in expected_shape]

        return output

    elif framework == "pytorch":
        import torch

        with torch.no_grad():
            tensor_input = torch.tensor(input_array, dtype=torch.float32)
            prediction = model(tensor_input)
            result = prediction.numpy().tolist() if hasattr(prediction, "numpy") else prediction.tolist()
            return {"prediction": result}

    elif framework == "sklearn":
        prediction = model.predict(input_array)
        result = prediction.tolist() if hasattr(prediction, "tolist") else list(prediction)

        # Try to get probability if available
        proba = None
        if hasattr(model, "predict_proba"):
            with contextlib.suppress(Exception):
                proba = model.predict_proba(input_array).tolist()

        return {
            "prediction": result,
            "probabilities": proba,
        }

    elif framework == "onnx":
        input_name = model.get_inputs()[0].name
        output_name = model.get_outputs()[0].name
        prediction = model.run([output_name], {input_name: input_array.astype(np.float32)})
        return {"prediction": prediction[0].tolist()}

    else:
        # Try generic predict
        if hasattr(model, "predict"):
            prediction = model.predict(input_array)
            result = prediction.tolist() if hasattr(prediction, "tolist") else prediction
            return {"prediction": result}
        elif callable(model):
            prediction = model(input_array)
            return {"prediction": str(prediction)}
        else:
            raise RuntimeError("Model does not have a predict method")


def load_and_predict(
    model_artifact_id: str,
    input_data: dict,
    cached_model: Any = None,
    framework: str | None = None,
) -> tuple[dict, Any]:
    """Load a model and run prediction.

    Args:
        model_artifact_id: ID of the model artifact
        input_data: Input data for prediction
        cached_model: Previously loaded model to reuse
        framework: Framework hint

    Returns:
        Tuple of (prediction_result, loaded_model)
    """
    from flowyml.ui.backend.dependencies import get_store
    import time

    start_time = time.time()
    store = get_store()

    # Get artifact path
    artifacts = store.list_assets()
    artifact = next(
        (
            a
            for a in artifacts
            if a.get("artifact_id") == model_artifact_id
            or f"{a.get('run_id')}_{a.get('step')}_{a.get('name')}" == model_artifact_id
        ),
        None,
    )

    if not artifact:
        raise ValueError(f"Model artifact not found: {model_artifact_id}")

    model_path = artifact.get("path") or artifact.get("uri") or artifact.get("storage_path")
    if not model_path:
        raise ValueError(f"No path found for artifact: {model_artifact_id}")

    # Detect or use provided framework
    if not framework:
        framework = (artifact.get("type") or artifact.get("asset_type") or "").lower()
        if "keras" in framework:
            framework = "keras"
        elif "pytorch" in framework or "torch" in framework:
            framework = "pytorch"
        elif "sklearn" in framework or "scikit" in framework:
            framework = "sklearn"
        elif "tensorflow" in framework or "tf" in framework:
            framework = "tensorflow"
        else:
            framework = _detect_framework(model_path)

    # Load model if not cached
    model = cached_model
    if model is None:
        model = _load_model_by_framework(model_path, framework)

    # Run prediction
    prediction = _predict_with_model(model, input_data, framework)

    prediction["latency_ms"] = (time.time() - start_time) * 1000
    prediction["framework"] = framework

    return prediction, model


def start_model_server(
    deployment_id: str,
    model_artifact_id: str,
    config: ServerConfig,
) -> ModelServer:
    """Start a model server for the given deployment.

    This loads the model and stores it in memory for fast predictions.

    Args:
        deployment_id: Unique deployment identifier
        model_artifact_id: ID of the model artifact
        config: Server configuration

    Returns:
        ModelServer instance
    """
    from flowyml.ui.backend.dependencies import get_store
    import os

    store = get_store()

    # Get artifact info
    artifacts = store.list_assets()
    artifact = next(
        (
            a
            for a in artifacts
            if a.get("artifact_id") == model_artifact_id
            or f"{a.get('run_id')}_{a.get('step')}_{a.get('name')}" == model_artifact_id
        ),
        None,
    )

    if not artifact:
        raise ValueError(f"Model artifact not found: {model_artifact_id}")

    # Get path and normalize it
    relative_path = artifact.get("path") or artifact.get("uri") or artifact.get("storage_path")
    if not relative_path:
        raise ValueError(f"No path found for artifact: {model_artifact_id}")

    # Container paths are relative to /app/artifacts
    model_path = os.path.join("/app/artifacts", relative_path)

    # Check if file/directory exists
    if not os.path.exists(model_path):
        raise ValueError(f"Model file not found at: {model_path}")

    # Detect framework from type or path
    framework = (artifact.get("type") or artifact.get("asset_type") or "").lower()
    if "keras" in framework:
        framework = "keras"
    elif "pytorch" in framework or "torch" in framework:
        framework = "pytorch"
    elif "sklearn" in framework or "scikit" in framework:
        framework = "sklearn"
    elif "tensorflow" in framework or "tf" in framework:
        framework = "tensorflow"
    else:
        framework = _detect_framework(model_path)

    # Create server instance
    server = ModelServer(
        deployment_id=deployment_id,
        model_artifact_id=model_artifact_id,
        model_path=model_path,
        framework=framework,
        config=config,
        started_at=datetime.now(),
    )

    # Load the model
    try:
        server.model = _load_model_by_framework(model_path, framework)
        server.log_buffer.append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": f"Model loaded successfully from {model_path} (framework: {framework})",
            },
        )
    except Exception as e:
        server.log_buffer.append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "message": f"Failed to load model: {str(e)}",
            },
        )
        raise

    # Store in registry
    _servers[deployment_id] = server

    logger.info(f"Started model server for deployment {deployment_id} on port {config.port}")

    return server


def stop_model_server(deployment_id: str) -> bool:
    """Stop a running model server.

    Args:
        deployment_id: ID of the deployment to stop

    Returns:
        True if stopped successfully, False if not found
    """
    if deployment_id not in _servers:
        return False

    server = _servers[deployment_id]

    # Clean up model from memory
    if server.model is not None:
        del server.model
        server.model = None

    server.log_buffer.append(
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": "Server stopped",
        },
    )

    # Remove from registry
    del _servers[deployment_id]

    logger.info(f"Stopped model server for deployment {deployment_id}")

    return True


def get_server(deployment_id: str) -> ModelServer | None:
    """Get a server by deployment ID."""
    return _servers.get(deployment_id)


def get_server_logs(deployment_id: str, lines: int = 100) -> list[dict]:
    """Get logs from a server.

    Args:
        deployment_id: ID of the deployment
        lines: Number of log lines to return

    Returns:
        List of log entries
    """
    server = _servers.get(deployment_id)
    if not server:
        return []

    return list(server.log_buffer)[-lines:]


def predict(deployment_id: str, input_data: dict) -> dict:
    """Run prediction on a deployed model.

    Args:
        deployment_id: ID of the deployment
        input_data: Input data for prediction

    Returns:
        Prediction result
    """
    server = _servers.get(deployment_id)
    if not server:
        raise ValueError(f"Deployment not found: {deployment_id}")

    if server.model is None:
        raise RuntimeError("Model not loaded")

    import time

    start_time = time.time()

    try:
        result = _predict_with_model(server.model, input_data, server.framework)
        latency = (time.time() - start_time) * 1000

        server.log_buffer.append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": f"Prediction completed in {latency:.2f}ms",
            },
        )

        result["latency_ms"] = latency
        return result

    except Exception as e:
        server.log_buffer.append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "message": f"Prediction failed: {str(e)}",
            },
        )
        raise

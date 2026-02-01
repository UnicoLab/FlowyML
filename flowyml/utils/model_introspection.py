"""Utilities for introspecting machine learning models."""

import contextlib
from typing import Any


def introspect_model(model: Any, framework: str) -> dict[str, Any]:
    """Introspect a model to extract input/output schema and metadata.

    Args:
        model: The loaded model object
        framework: Framework name (keras, tensorflow, sklearn, pytorch)

    Returns:
        Dictionary containing schema information like:
        - input_shape: List[int]
        - output_shape: List[int]
        - input_names: List[str]
        - output_names: List[str]
        - input_features: int
        - total_params: int
    """
    info = {
        "framework": framework,
    }

    if framework in ["keras", "tensorflow"]:
        _introspect_keras(model, info)
    elif framework == "sklearn":
        _introspect_sklearn(model, info)
    elif framework == "pytorch":
        _introspect_pytorch(model, info)

    return info


def _introspect_keras(model: Any, info: dict[str, Any]) -> None:
    """Extract metadata from Keras/TensorFlow models."""
    try:
        # Input Shape
        if hasattr(model, "input_shape"):
            shape = model.input_shape
            info["input_shape"] = [s if s else None for s in shape]
            # Try to guess feature count from last dim
            if isinstance(shape, (list, tuple)):
                info["input_features"] = shape[-1] if len(shape) > 1 and shape[-1] else None

        # Output Shape
        if hasattr(model, "output_shape"):
            shape = model.output_shape
            info["output_shape"] = [s if s else None for s in shape]

        # Input Names
        if hasattr(model, "input_names") and model.input_names:
            info["input_names"] = model.input_names
        elif hasattr(model, "inputs"):
            info["input_names"] = [inp.name.split(":")[0] for inp in model.inputs]

        # Output Names
        if hasattr(model, "output_names") and model.output_names:
            info["output_names"] = model.output_names
        elif hasattr(model, "outputs"):
            info["output_names"] = [out.name.split(":")[0] for out in model.outputs]

        # Layer info
        if hasattr(model, "layers"):
            info["layer_count"] = len(model.layers)
            info["first_layer"] = model.layers[0].name if model.layers else None
            info["last_layer"] = model.layers[-1].name if model.layers else None

        # Params
        with contextlib.suppress(Exception):
            info["total_params"] = model.count_params()

    except Exception as e:
        info["introspection_error"] = str(e)


def _introspect_sklearn(model: Any, info: dict[str, Any]) -> None:
    """Extract metadata from Scikit-Learn models."""
    try:
        if hasattr(model, "n_features_in_"):
            info["input_features"] = model.n_features_in_
            # Create synthetic input shape [None, n_features]
            info["input_shape"] = [None, model.n_features_in_]

        if hasattr(model, "feature_names_in_"):
            info["input_names"] = list(model.feature_names_in_)

        if hasattr(model, "classes_"):
            info["classes"] = list(model.classes_)
            info["output_shape"] = [None, 1]  # Binary/Multi-class usually outputs 1 prediction or probas

        if hasattr(model, "n_classes_"):
            info["n_classes"] = model.n_classes_

    except Exception as e:
        info["introspection_error"] = str(e)


def _introspect_pytorch(model: Any, info: dict[str, Any]) -> None:
    """Extract metadata from PyTorch models."""
    try:
        if hasattr(model, "parameters"):
            info["total_params"] = sum(p.numel() for p in model.parameters())

        # Try to infer input features from first layer if possible
        # This is heuristic and might not work for all architectures
        for _, module in getattr(model, "named_children", lambda: [])():
            if hasattr(module, "in_features"):
                info["input_features"] = module.in_features
                info["input_shape"] = [None, module.in_features]
                break
            elif hasattr(module, "weight") and hasattr(module.weight, "shape") and len(module.weight.shape) >= 2:
                # Conv2d weight: [out_channels, in_channels, kH, kW] -> unrelated to input *features* in flat sense usually
                # Linear weight: [out_features, in_features]
                if module.__class__.__name__ == "Linear":
                    info["input_features"] = module.weight.shape[1]
                    info["input_shape"] = [None, module.weight.shape[1]]
                    break

    except Exception as e:
        info["introspection_error"] = str(e)

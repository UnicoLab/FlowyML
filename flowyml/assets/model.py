"""Model Asset - Represents ML models with automatic metadata extraction."""

from typing import Any
import contextlib
import logging

from flowyml.assets.base import Asset

logger = logging.getLogger(__name__)


class ModelInspector:
    """Utility class for extracting model metadata from various frameworks.

    This class provides robust, fail-safe extraction of model metadata.
    It will never raise exceptions - if extraction fails, it returns
    partial results with whatever could be extracted.

    Supported frameworks with rich extraction:
        - Keras/TensorFlow: Full architecture, optimizer, loss, metrics
        - PyTorch: Architecture, parameters, layer info
        - Scikit-learn: Hyperparameters, feature importance
        - XGBoost/LightGBM/CatBoost: Trees, hyperparameters

    All other model types are supported with basic metadata (type name, etc.)
    """

    @staticmethod
    def detect_framework(model: Any) -> str | None:
        """Detect the ML framework of a model.

        Returns one of: 'keras', 'tensorflow', 'pytorch', 'sklearn', 'xgboost',
        'lightgbm', 'catboost', 'huggingface', 'onnx', 'custom', or None

        This method is safe to call on any object and will never raise.
        """
        if model is None:
            return None

        try:
            type_name = type(model).__name__
            module_name = type(model).__module__

            # Keras/TensorFlow - check multiple indicators
            if any(x in module_name.lower() for x in ["keras", "tf.keras"]):
                return "keras"
            if type_name in ("Sequential", "Functional", "Model") and "tensorflow" in module_name.lower():
                return "keras"
            if "tensorflow" in module_name.lower():
                return "tensorflow"

            # PyTorch - check for nn.Module inheritance (handles user-defined models)
            # Check if any base class is from torch
            try:
                for base in type(model).__mro__:
                    base_module = base.__module__
                    if "torch" in base_module.lower():
                        return "pytorch"
            except Exception:
                pass

            # Also check module name directly (for torch tensors, etc.)
            if "torch" in module_name.lower():
                return "pytorch"

            # Check for PyTorch-specific attributes
            if hasattr(model, "forward") and hasattr(model, "parameters") and hasattr(model, "state_dict"):
                # Likely a PyTorch model
                return "pytorch"

            # Scikit-learn - check for common base classes
            if "sklearn" in module_name.lower():
                return "sklearn"

            # XGBoost
            if "xgboost" in module_name.lower() or type_name.startswith("XGB"):
                return "xgboost"

            # LightGBM
            if "lightgbm" in module_name.lower() or type_name.startswith("LGB"):
                return "lightgbm"

            # CatBoost
            if "catboost" in module_name.lower():
                return "catboost"

            # Hugging Face Transformers
            if "transformers" in module_name.lower():
                return "huggingface"

            # ONNX
            if "onnx" in module_name.lower():
                return "onnx"

            # JAX/Flax
            if "flax" in module_name.lower() or "jax" in module_name.lower():
                return "jax"

            # Check for common ML model attributes
            if hasattr(model, "predict") and hasattr(model, "fit"):
                return "sklearn"  # Sklearn-like API

            return "custom"

        except Exception as e:
            logger.debug(f"Error detecting framework: {e}")
            return "unknown"

    @staticmethod
    def extract_keras_info(model: Any) -> dict[str, Any]:
        """Extract metadata from a Keras/TensorFlow model.

        This method is robust and will extract as much as possible,
        even if some attributes are not available (e.g., uncompiled model).
        """
        result = {"framework": "keras", "_auto_extracted": True}

        # Parameter count - handle both built and unbuilt models
        try:
            if hasattr(model, "count_params"):
                with contextlib.suppress(Exception):
                    result["parameters"] = model.count_params()
        except Exception as e:
            logger.debug(f"Error getting param count: {e}")

        # Trainable parameters
        try:
            if hasattr(model, "trainable_weights") and model.trainable_weights:
                trainable = sum(int(w.numpy().size) if hasattr(w, "numpy") else 0 for w in model.trainable_weights)
                if trainable > 0:
                    result["trainable_parameters"] = trainable
        except Exception as e:
            logger.debug(f"Error getting trainable params: {e}")

        # Architecture name
        try:
            if hasattr(model, "name") and model.name:
                result["architecture"] = model.name
            result["model_class"] = type(model).__name__
        except Exception as e:
            logger.debug(f"Error getting architecture: {e}")

        # Layer info - handle models without layers attribute
        try:
            if hasattr(model, "layers"):
                layers = model.layers
                if layers:
                    result["num_layers"] = len(layers)
                    result["layer_types"] = list({type(layer).__name__ for layer in layers})
        except Exception as e:
            logger.debug(f"Error getting layer info: {e}")

        # Input/Output shapes - handle unbuilt models
        with contextlib.suppress(Exception):
            if hasattr(model, "input_shape"):
                input_shape = model.input_shape
                if input_shape is not None:
                    result["input_shape"] = str(input_shape)

        with contextlib.suppress(Exception):
            if hasattr(model, "output_shape"):
                output_shape = model.output_shape
                if output_shape is not None:
                    result["output_shape"] = str(output_shape)

        # Optimizer info (only for compiled models)
        try:
            if hasattr(model, "optimizer") and model.optimizer is not None:
                opt = model.optimizer
                result["optimizer"] = type(opt).__name__

                # Get learning rate - handle different Keras versions
                if hasattr(opt, "learning_rate"):
                    lr = opt.learning_rate
                    if hasattr(lr, "numpy"):
                        lr = float(lr.numpy())
                    elif callable(lr):
                        # Learning rate schedule
                        result["lr_schedule"] = type(lr).__name__
                    else:
                        lr = float(lr)
                    if isinstance(lr, (int, float)):
                        result["learning_rate"] = lr
                elif hasattr(opt, "lr"):
                    # Older Keras versions
                    result["learning_rate"] = float(opt.lr)
        except Exception as e:
            logger.debug(f"Error getting optimizer info: {e}")

        # Loss function (only for compiled models)
        try:
            if hasattr(model, "loss") and model.loss is not None:
                loss = model.loss
                if isinstance(loss, str):
                    result["loss_function"] = loss
                elif hasattr(loss, "__name__"):
                    result["loss_function"] = loss.__name__
                elif hasattr(loss, "name"):
                    result["loss_function"] = loss.name
                elif hasattr(loss, "__class__"):
                    result["loss_function"] = type(loss).__name__
        except Exception as e:
            logger.debug(f"Error getting loss function: {e}")

        # Metrics (only for compiled models)
        try:
            if hasattr(model, "metrics_names") and model.metrics_names:
                result["metrics"] = list(model.metrics_names)
            elif hasattr(model, "metrics") and model.metrics:
                result["metrics"] = [m.name if hasattr(m, "name") else str(m) for m in model.metrics]
        except Exception as e:
            logger.debug(f"Error getting metrics: {e}")

        # Check if model is compiled
        with contextlib.suppress(Exception):
            result["is_compiled"] = hasattr(model, "optimizer") and model.optimizer is not None

        # Check if model is built
        with contextlib.suppress(Exception):
            if hasattr(model, "built"):
                result["is_built"] = model.built

        return result

    @staticmethod
    def extract_pytorch_info(model: Any) -> dict[str, Any]:
        """Extract metadata from a PyTorch model.

        This method is robust and handles:
        - nn.Module models
        - Custom modules
        - Pretrained models from torchvision, transformers, etc.
        - Models in eval or train mode
        """
        result = {"framework": "pytorch", "_auto_extracted": True}

        # Model class name
        try:
            result["model_class"] = type(model).__name__
            result["architecture"] = type(model).__name__
        except Exception:
            pass

        # Parameter count
        try:
            if hasattr(model, "parameters"):
                params = list(model.parameters())
                if params:
                    total_params = sum(p.numel() for p in params)
                    trainable_params = sum(p.numel() for p in params if p.requires_grad)
                    result["parameters"] = total_params
                    result["trainable_parameters"] = trainable_params
                    result["frozen_parameters"] = total_params - trainable_params
        except Exception as e:
            logger.debug(f"Error getting PyTorch param count: {e}")

        # Layer info from modules
        try:
            if hasattr(model, "modules"):
                modules = list(model.modules())
                if modules:
                    # Skip the first module (the model itself)
                    layer_modules = modules[1:] if len(modules) > 1 else modules
                    result["num_layers"] = len(layer_modules)

                    # Get unique layer types
                    layer_types = set()
                    for m in layer_modules:
                        layer_type = type(m).__name__
                        # Skip container modules
                        if layer_type not in ("Sequential", "ModuleList", "ModuleDict"):
                            layer_types.add(layer_type)
                    result["layer_types"] = list(layer_types)
        except Exception as e:
            logger.debug(f"Error getting PyTorch layer info: {e}")

        # Named modules for architecture insights
        try:
            if hasattr(model, "named_modules"):
                named = dict(model.named_modules())
                if named:
                    result["num_named_modules"] = len(named)
        except Exception:
            pass

        # State dict info
        try:
            if hasattr(model, "state_dict"):
                state_dict = model.state_dict()
                if state_dict:
                    result["num_tensors"] = len(state_dict)
                    # Get tensor shapes for key layers
                    tensor_shapes = {}
                    for name, tensor in list(state_dict.items())[:10]:  # First 10 only
                        tensor_shapes[name] = list(tensor.shape)
                    result["tensor_shapes_sample"] = tensor_shapes
        except Exception as e:
            logger.debug(f"Error getting PyTorch state dict: {e}")

        # Training mode
        try:
            if hasattr(model, "training"):
                result["training_mode"] = model.training
        except Exception:
            pass

        # Device info
        try:
            if hasattr(model, "parameters"):
                first_param = next(model.parameters(), None)
                if first_param is not None:
                    result["device"] = str(first_param.device)
                    result["dtype"] = str(first_param.dtype)
        except Exception:
            pass

        # Check for common PyTorch model attributes
        try:
            # Input features (common in many models)
            for attr in ["in_features", "in_channels", "input_size", "num_features"]:
                if hasattr(model, attr):
                    val = getattr(model, attr, None)
                    if val is not None:
                        result[attr] = val
                        break

            # Output features
            for attr in ["out_features", "out_channels", "output_size", "num_classes"]:
                if hasattr(model, attr):
                    val = getattr(model, attr, None)
                    if val is not None:
                        result[attr] = val
                        break
        except Exception:
            pass

        return result

    @staticmethod
    def extract_sklearn_info(model: Any) -> dict[str, Any]:
        """Extract metadata from a scikit-learn model.

        Handles all sklearn estimators including:
        - Classifiers, regressors, transformers
        - Ensemble methods (RandomForest, GradientBoosting, etc.)
        - Linear models
        - Pipelines
        """
        result = {"framework": "sklearn", "_auto_extracted": True}

        # Model type
        try:
            result["model_class"] = type(model).__name__
            result["architecture"] = type(model).__name__
        except Exception:
            pass

        # Get parameters (safe extraction)
        try:
            if hasattr(model, "get_params"):
                params = model.get_params(deep=False)  # Shallow to avoid recursion
                # Filter to serializable values
                filtered_params = {}
                for k, v in params.items():
                    if v is None:
                        continue
                    if isinstance(v, (str, int, float, bool)):
                        filtered_params[k] = v
                    elif isinstance(v, (list, tuple)) and len(v) < 10:
                        # Small lists/tuples of primitives
                        if all(isinstance(x, (str, int, float, bool, type(None))) for x in v):
                            filtered_params[k] = list(v)
                if filtered_params:
                    result["hyperparameters"] = filtered_params
        except Exception as e:
            logger.debug(f"Error getting sklearn params: {e}")

        # Feature importance (tree-based models)
        with contextlib.suppress(Exception):
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
                result["has_feature_importances"] = True
                result["num_features"] = len(importances)
                # Store top 10 feature importances
                if len(importances) <= 20:
                    result["feature_importances"] = list(importances)

        # Coefficients (linear models)
        with contextlib.suppress(Exception):
            if hasattr(model, "coef_"):
                coef = model.coef_
                if hasattr(coef, "shape"):
                    result["coef_shape"] = str(coef.shape)
                if hasattr(coef, "size") and coef.size <= 100:
                    result["num_coefficients"] = int(coef.size)

        # Intercept
        with contextlib.suppress(Exception):
            if hasattr(model, "intercept_"):
                intercept = model.intercept_
                if hasattr(intercept, "tolist"):
                    intercept = intercept.tolist()
                if isinstance(intercept, (int, float)) or (isinstance(intercept, list) and len(intercept) <= 10):
                    result["intercept"] = intercept

        # Classes (classifiers)
        try:
            if hasattr(model, "classes_"):
                classes = model.classes_
                result["num_classes"] = len(classes)
                if len(classes) <= 20:
                    # Convert to list if numpy array
                    if hasattr(classes, "tolist"):
                        classes = classes.tolist()
                    result["classes"] = list(classes)
        except Exception:
            pass

        # Number of estimators (ensemble models)
        try:
            if hasattr(model, "n_estimators"):
                result["n_estimators"] = model.n_estimators
            if hasattr(model, "estimators_"):
                result["num_estimators_fitted"] = len(model.estimators_)
        except Exception:
            pass

        # Tree-specific attributes
        try:
            if hasattr(model, "max_depth"):
                result["max_depth"] = model.max_depth
            if hasattr(model, "n_features_in_"):
                result["n_features_in"] = model.n_features_in_
        except Exception:
            pass

        # Check if fitted
        try:
            # Common sklearn pattern for checking if fitted
            from sklearn.utils.validation import check_is_fitted

            check_is_fitted(model)
            result["is_fitted"] = True
        except Exception:
            result["is_fitted"] = False

        return result

    @staticmethod
    def extract_xgboost_info(model: Any) -> dict[str, Any]:
        """Extract metadata from an XGBoost model."""
        result = {"framework": "xgboost", "_auto_extracted": True}

        try:
            result["model_class"] = type(model).__name__
            result["architecture"] = "XGBoost"
        except Exception:
            pass

        # Get hyperparameters
        try:
            if hasattr(model, "get_params"):
                params = model.get_params()
                result["hyperparameters"] = {
                    k: v for k, v in params.items() if v is not None and isinstance(v, (str, int, float, bool))
                }
        except Exception as e:
            logger.debug(f"Error getting XGBoost params: {e}")

        # Booster info
        try:
            if hasattr(model, "get_booster"):
                booster = model.get_booster()
                if hasattr(booster, "num_trees"):
                    result["num_trees"] = booster.num_trees()
                if hasattr(booster, "num_features"):
                    result["num_features"] = booster.num_features()
            elif hasattr(model, "n_estimators"):
                result["n_estimators"] = model.n_estimators
        except Exception:
            pass

        # Feature importance
        try:
            if hasattr(model, "feature_importances_"):
                result["num_features"] = len(model.feature_importances_)
                result["has_feature_importances"] = True
        except Exception:
            pass

        # Best iteration (for early stopping)
        try:
            if hasattr(model, "best_iteration"):
                result["best_iteration"] = model.best_iteration
            if hasattr(model, "best_score"):
                result["best_score"] = model.best_score
        except Exception:
            pass

        return result

    @staticmethod
    def extract_lightgbm_info(model: Any) -> dict[str, Any]:
        """Extract metadata from a LightGBM model."""
        result = {"framework": "lightgbm", "_auto_extracted": True}

        try:
            result["model_class"] = type(model).__name__
            result["architecture"] = "LightGBM"
        except Exception:
            pass

        # Get hyperparameters
        try:
            if hasattr(model, "get_params"):
                params = model.get_params()
                result["hyperparameters"] = {
                    k: v for k, v in params.items() if v is not None and isinstance(v, (str, int, float, bool))
                }
        except Exception:
            pass

        # Booster info
        try:
            if hasattr(model, "booster_"):
                booster = model.booster_
                if hasattr(booster, "num_trees"):
                    result["num_trees"] = booster.num_trees()
            elif hasattr(model, "n_estimators"):
                result["n_estimators"] = model.n_estimators
        except Exception:
            pass

        # Feature importance
        try:
            if hasattr(model, "feature_importances_"):
                result["num_features"] = len(model.feature_importances_)
                result["has_feature_importances"] = True
        except Exception:
            pass

        # Best iteration
        try:
            if hasattr(model, "best_iteration_"):
                result["best_iteration"] = model.best_iteration_
            if hasattr(model, "best_score_"):
                result["best_score"] = model.best_score_
        except Exception:
            pass

        return result

    @staticmethod
    def extract_huggingface_info(model: Any) -> dict[str, Any]:
        """Extract metadata from a Hugging Face Transformers model."""
        result = {"framework": "huggingface", "_auto_extracted": True}

        try:
            result["model_class"] = type(model).__name__
            result["architecture"] = type(model).__name__
        except Exception:
            pass

        # Config info
        try:
            if hasattr(model, "config"):
                config = model.config
                result["model_type"] = getattr(config, "model_type", None)
                result["hidden_size"] = getattr(config, "hidden_size", None)
                result["num_attention_heads"] = getattr(config, "num_attention_heads", None)
                result["num_hidden_layers"] = getattr(config, "num_hidden_layers", None)
                result["vocab_size"] = getattr(config, "vocab_size", None)
                # Clean up None values
                result = {k: v for k, v in result.items() if v is not None}
        except Exception:
            pass

        # Parameter count
        try:
            if hasattr(model, "num_parameters"):
                result["parameters"] = model.num_parameters()
            elif hasattr(model, "parameters"):
                result["parameters"] = sum(p.numel() for p in model.parameters())
        except Exception:
            pass

        # Device
        try:
            if hasattr(model, "device"):
                result["device"] = str(model.device)
        except Exception:
            pass

        return result

    @staticmethod
    def extract_generic_info(model: Any) -> dict[str, Any]:
        """Extract basic metadata from any model type.

        This is the fallback for unknown/custom models.
        """
        result = {"framework": "custom", "_auto_extracted": True}

        try:
            result["model_class"] = type(model).__name__
            result["module"] = type(model).__module__
        except Exception:
            pass

        # Check for common model attributes
        try:
            # Fit/predict API (sklearn-like)
            result["has_fit"] = hasattr(model, "fit")
            result["has_predict"] = hasattr(model, "predict")
            result["has_transform"] = hasattr(model, "transform")

            # Parameters
            if hasattr(model, "get_params"):
                result["has_get_params"] = True

            # State dict (PyTorch-like)
            if hasattr(model, "state_dict"):
                result["has_state_dict"] = True
        except Exception:
            pass

        return result

    @staticmethod
    def extract_info(model: Any) -> dict[str, Any]:
        """Auto-detect framework and extract model metadata.

        This method is the main entry point for model metadata extraction.
        It is designed to NEVER fail - if extraction fails for any reason,
        it returns a minimal result with whatever could be extracted.

        Args:
            model: Any model object from any framework

        Returns:
            Dict with extracted metadata. Always includes:
            - framework: Detected framework name
            - _auto_extracted: Whether extraction succeeded
            - model_class: Class name of the model (if available)
        """
        # Handle None model
        if model is None:
            return {"framework": None, "_auto_extracted": False, "error": "Model is None"}

        # Detect framework
        framework = ModelInspector.detect_framework(model)

        # Extract based on framework
        try:
            if framework == "keras":
                return ModelInspector.extract_keras_info(model)
            elif framework == "tensorflow":
                # TensorFlow models that aren't Keras
                result = ModelInspector.extract_keras_info(model)
                result["framework"] = "tensorflow"
                return result
            elif framework == "pytorch":
                return ModelInspector.extract_pytorch_info(model)
            elif framework == "sklearn":
                return ModelInspector.extract_sklearn_info(model)
            elif framework == "xgboost":
                return ModelInspector.extract_xgboost_info(model)
            elif framework == "lightgbm":
                return ModelInspector.extract_lightgbm_info(model)
            elif framework == "catboost":
                # CatBoost is similar to XGBoost
                result = ModelInspector.extract_xgboost_info(model)
                result["framework"] = "catboost"
                return result
            elif framework == "huggingface":
                return ModelInspector.extract_huggingface_info(model)
            elif framework in ("jax", "onnx"):
                # Basic extraction for JAX/ONNX
                result = ModelInspector.extract_generic_info(model)
                result["framework"] = framework
                return result
            else:
                # Unknown or custom framework - use generic extraction
                return ModelInspector.extract_generic_info(model)

        except Exception as e:
            # If all else fails, return minimal info
            logger.debug(f"Error extracting model info: {e}")
            return {
                "framework": framework or "unknown",
                "model_class": type(model).__name__,
                "_auto_extracted": False,
                "_extraction_error": str(e),
            }

    @staticmethod
    def extract_training_history_from_callback(callback: Any) -> dict[str, list] | None:
        """Extract training history from a FlowyML callback or Keras History object."""
        try:
            # FlowyML callback
            if hasattr(callback, "get_training_history"):
                return callback.get_training_history()

            # Keras History object
            if hasattr(callback, "history"):
                history = callback.history
                if isinstance(history, dict):
                    # Add epochs if not present
                    if "epochs" not in history and history:
                        first_key = next(iter(history.keys()))
                        history["epochs"] = list(range(1, len(history[first_key]) + 1))
                    return history

            # Training history dict directly
            if isinstance(callback, dict) and any(isinstance(v, list) for v in callback.values()):
                return callback

        except Exception as e:
            logger.debug(f"Error extracting training history: {e}")

        return None


class Model(Asset):
    """Model asset with automatic metadata extraction and training history.

    The Model class automatically extracts metadata from various ML frameworks,
    reducing boilerplate code and improving UX. It also captures training history
    for visualization in the FlowyML dashboard.

    Supported frameworks:
        - Keras/TensorFlow: Auto-extracts layers, parameters, optimizer, loss
        - PyTorch: Auto-extracts modules, parameters, training mode
        - Scikit-learn: Auto-extracts hyperparameters, feature importance
        - XGBoost/LightGBM: Auto-extracts trees, hyperparameters

    Example:
        >>> # Minimal usage - properties auto-extracted!
        >>> model_asset = Model.create(
        ...     data=trained_keras_model,
        ...     name="my_model",
        ... )
        >>> print(model_asset.parameters)  # Auto-extracted
        >>> print(model_asset.framework)  # Auto-detected

        >>> # With FlowyML callback - training history auto-captured
        >>> callback = FlowymlKerasCallback(experiment_name="demo")
        >>> model.fit(X, y, callbacks=[callback])
        >>> model_asset = Model.create(
        ...     data=model,
        ...     name="trained_model",
        ...     flowyml_callback=callback,  # Auto-extracts training history!
        ... )
    """

    def __init__(
        self,
        name: str,
        version: str | None = None,
        data: Any = None,
        architecture: str | None = None,
        framework: str | None = None,
        input_shape: tuple | None = None,
        output_shape: tuple | None = None,
        trained_on: Asset | None = None,
        parent: Asset | None = None,
        tags: dict[str, str] | None = None,
        properties: dict[str, Any] | None = None,
        training_history: dict[str, list] | None = None,
        auto_extract: bool = True,
    ):
        """Initialize Model with automatic metadata extraction.

        Args:
            name: Model name
            version: Version string
            data: The model object (Keras, PyTorch, sklearn, etc.)
            architecture: Architecture name (auto-detected if not provided)
            framework: Framework name (auto-detected if not provided)
            input_shape: Input shape (auto-detected for Keras)
            output_shape: Output shape (auto-detected for Keras)
            trained_on: Dataset this model was trained on
            parent: Parent asset for lineage
            tags: Metadata tags
            properties: Additional properties (merged with auto-extracted)
            training_history: Training metrics per epoch
            auto_extract: Whether to auto-extract model metadata
        """
        # Initialize properties
        final_properties = properties.copy() if properties else {}

        # Auto-extract model metadata if enabled
        if auto_extract and data is not None:
            extracted = ModelInspector.extract_info(data)
            # Merge - user-provided values take precedence
            for key, value in extracted.items():
                if key not in final_properties:
                    final_properties[key] = value

            # Set framework from extracted if not provided
            if framework is None and "framework" in extracted:
                framework = extracted["framework"]

            # Set architecture from extracted if not provided
            if architecture is None and "architecture" in extracted:
                architecture = extracted["architecture"]

        super().__init__(
            name=name,
            version=version,
            data=data,
            parent=parent,
            tags=tags,
            properties=final_properties,
        )

        self.architecture = architecture
        self.framework = framework
        self.input_shape = input_shape
        self.output_shape = output_shape
        self.training_history = training_history

        # Track training dataset
        if trained_on:
            self.parents.append(trained_on)
            trained_on.children.append(self)

        # Add model-specific properties (explicit ones override extracted)
        if architecture:
            self.metadata.properties["architecture"] = architecture
        if framework:
            self.metadata.properties["framework"] = framework
        if input_shape:
            self.metadata.properties["input_shape"] = str(input_shape)
        if output_shape:
            self.metadata.properties["output_shape"] = str(output_shape)

    @classmethod
    def create(
        cls,
        data: Any,
        name: str | None = None,
        version: str | None = None,
        parent: "Asset | None" = None,
        flowyml_callback: Any = None,
        keras_history: Any = None,
        auto_extract: bool = True,
        **kwargs: Any,
    ) -> "Model":
        """Create a Model asset with automatic metadata extraction.

        This is the preferred way to create Model objects. Metadata is
        automatically extracted from the model, and training history can
        be captured from FlowyML callbacks.

        Args:
            data: The model object (Keras, PyTorch, sklearn, etc.)
            name: Asset name (auto-generated if not provided)
            version: Asset version
            parent: Parent asset for lineage
            flowyml_callback: FlowymlKerasCallback for auto-capturing training history
            keras_history: Keras History object from model.fit()
            auto_extract: Whether to auto-extract model metadata
            **kwargs: Additional parameters including:
                - training_history: Dict of training metrics per epoch
                - architecture: Model architecture name
                - framework: ML framework (keras, pytorch, etc.)
                - properties: Additional properties
                - tags: Metadata tags

        Returns:
            New Model instance with auto-extracted metadata

        Example:
            >>> # Simple usage - everything auto-extracted
            >>> model_asset = Model.create(data=model, name="my_model")

            >>> # With FlowyML callback
            >>> callback = FlowymlKerasCallback(experiment_name="demo")
            >>> model.fit(X, y, callbacks=[callback])
            >>> model_asset = Model.create(
            ...     data=model,
            ...     name="trained_model",
            ...     flowyml_callback=callback,
            ... )

            >>> # With Keras History
            >>> history = model.fit(X, y)
            >>> model_asset = Model.create(
            ...     data=model,
            ...     name="trained_model",
            ...     keras_history=history,
            ... )
        """
        from datetime import datetime

        asset_name = name or f"Model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Extract Model-specific parameters
        training_history = kwargs.pop("training_history", None)
        architecture = kwargs.pop("architecture", None)
        framework = kwargs.pop("framework", None)
        input_shape = kwargs.pop("input_shape", None)
        output_shape = kwargs.pop("output_shape", None)
        trained_on = kwargs.pop("trained_on", None)

        # Auto-extract training history from callback or history object
        if training_history is None:
            if flowyml_callback is not None:
                training_history = ModelInspector.extract_training_history_from_callback(
                    flowyml_callback,
                )
            elif keras_history is not None:
                training_history = ModelInspector.extract_training_history_from_callback(
                    keras_history,
                )

        # Extract tags and properties
        tags = kwargs.pop("tags", {})
        props = kwargs.pop("properties", {})
        # Merge remaining kwargs into properties
        props.update(kwargs)

        return cls(
            name=asset_name,
            version=version,
            data=data,
            architecture=architecture,
            framework=framework,
            input_shape=input_shape,
            output_shape=output_shape,
            trained_on=trained_on,
            parent=parent,
            tags=tags,
            properties=props,
            training_history=training_history,
            auto_extract=auto_extract,
        )

    @classmethod
    def from_keras(
        cls,
        model: Any,
        name: str | None = None,
        callback: Any = None,
        history: Any = None,
        **kwargs: Any,
    ) -> "Model":
        """Create a Model asset from a Keras model with full auto-extraction.

        Args:
            model: Keras model object
            name: Asset name
            callback: FlowymlKerasCallback for training history
            history: Keras History object from model.fit()
            **kwargs: Additional properties

        Returns:
            Model asset with auto-extracted Keras metadata
        """
        return cls.create(
            data=model,
            name=name,
            framework="keras",
            flowyml_callback=callback,
            keras_history=history,
            **kwargs,
        )

    @classmethod
    def from_pytorch(
        cls,
        model: Any,
        name: str | None = None,
        training_history: dict | None = None,
        **kwargs: Any,
    ) -> "Model":
        """Create a Model asset from a PyTorch model with full auto-extraction.

        Args:
            model: PyTorch model object (nn.Module)
            name: Asset name
            training_history: Training metrics dict
            **kwargs: Additional properties

        Returns:
            Model asset with auto-extracted PyTorch metadata
        """
        return cls.create(
            data=model,
            name=name,
            framework="pytorch",
            training_history=training_history,
            **kwargs,
        )

    @classmethod
    def from_sklearn(
        cls,
        model: Any,
        name: str | None = None,
        **kwargs: Any,
    ) -> "Model":
        """Create a Model asset from a scikit-learn model with full auto-extraction.

        Args:
            model: Scikit-learn model object
            name: Asset name
            **kwargs: Additional properties

        Returns:
            Model asset with auto-extracted sklearn metadata
        """
        return cls.create(
            data=model,
            name=name,
            framework="sklearn",
            **kwargs,
        )

    @property
    def parameters(self) -> int | None:
        """Get number of model parameters (auto-extracted)."""
        return self.metadata.properties.get("parameters") or self.metadata.properties.get("params")

    @property
    def trainable_parameters(self) -> int | None:
        """Get number of trainable parameters (auto-extracted)."""
        return self.metadata.properties.get("trainable_parameters")

    @property
    def num_layers(self) -> int | None:
        """Get number of layers (auto-extracted)."""
        return self.metadata.properties.get("num_layers")

    @property
    def layer_types(self) -> list[str] | None:
        """Get list of layer types (auto-extracted)."""
        return self.metadata.properties.get("layer_types")

    @property
    def optimizer(self) -> str | None:
        """Get optimizer name (auto-extracted from Keras)."""
        return self.metadata.properties.get("optimizer")

    @property
    def learning_rate(self) -> float | None:
        """Get learning rate (auto-extracted from Keras)."""
        return self.metadata.properties.get("learning_rate")

    @property
    def loss_function(self) -> str | None:
        """Get loss function (auto-extracted from Keras)."""
        return self.metadata.properties.get("loss_function")

    @property
    def metrics(self) -> list[str] | None:
        """Get metrics (auto-extracted from Keras)."""
        return self.metadata.properties.get("metrics")

    @property
    def hyperparameters(self) -> dict | None:
        """Get hyperparameters (auto-extracted from sklearn/xgboost)."""
        return self.metadata.properties.get("hyperparameters")

    def get_training_datasets(self):
        """Get all datasets this model was trained on."""
        from flowyml.assets.dataset import Dataset

        return [p for p in self.parents if isinstance(p, Dataset)]

    def get_parameters_count(self) -> int | None:
        """Get number of model parameters if available."""
        return self.parameters

    def get_architecture_info(self) -> dict[str, Any]:
        """Get architecture information."""
        return {
            "architecture": self.architecture,
            "framework": self.framework,
            "input_shape": self.input_shape,
            "output_shape": self.output_shape,
            "parameters": self.parameters,
            "trainable_parameters": self.trainable_parameters,
            "num_layers": self.num_layers,
            "layer_types": self.layer_types,
        }

    def get_training_info(self) -> dict[str, Any]:
        """Get training information."""
        result = {
            "optimizer": self.optimizer,
            "learning_rate": self.learning_rate,
            "loss_function": self.loss_function,
            "metrics": self.metrics,
        }

        if self.training_history:
            epochs = self.training_history.get("epochs", [])
            result["epochs_trained"] = len(epochs)

            # Get final metrics
            for key, values in self.training_history.items():
                if key != "epochs" and values:
                    result[f"final_{key}"] = values[-1]

        return {k: v for k, v in result.items() if v is not None}

    def __repr__(self) -> str:
        """String representation with key info."""
        parts = [f"Model(name='{self.name}'"]
        if self.framework:
            parts.append(f"framework='{self.framework}'")
        if self.parameters:
            parts.append(f"params={self.parameters:,}")
        if self.training_history:
            epochs = len(self.training_history.get("epochs", []))
            parts.append(f"epochs={epochs}")
        return ", ".join(parts) + ")"

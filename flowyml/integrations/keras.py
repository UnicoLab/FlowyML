"""Keras integration for flowyml."""

from pathlib import Path
from datetime import datetime
import uuid

try:
    from tensorflow import keras
except ImportError:
    try:
        import keras
    except ImportError:
        keras = None

from flowyml.tracking.experiment import Experiment
from flowyml.storage.metadata import SQLiteMetadataStore


class FlowymlKerasCallback(keras.callbacks.Callback if keras else object):
    """Keras callback for flowyml tracking with automatic training history collection.

    Automatically logs:
    - Training metrics (loss, accuracy, etc.) per epoch
    - Complete training history for visualization
    - Model checkpoints with training history attached
    - Model architecture
    - Training parameters

    Example:
        >>> from flowyml.integrations.keras import FlowymlKerasCallback
        >>> callback = FlowymlKerasCallback(experiment_name="my-experiment", project="my-project", auto_log_history=True)
        >>> model.fit(x_train, y_train, epochs=50, callbacks=[callback])
    """

    def __init__(
        self,
        experiment_name: str,
        run_name: str | None = None,
        project: str | None = None,
        log_model: bool = True,
        log_every_epoch: bool = True,
        auto_log_history: bool = True,
        metadata_store: SQLiteMetadataStore | None = None,
    ):
        """Args:
        experiment_name: Name of the experiment
        run_name: Optional run name (defaults to timestamp)
        project: Project name for organizing runs
        log_model: Whether to save the model as an artifact
        log_every_epoch: Whether to log metrics every epoch
        auto_log_history: Whether to automatically collect training history
        metadata_store: Optional metadata store override.
        """
        if keras is None:
            raise ImportError("Keras is not installed. Please install tensorflow or keras.")

        super().__init__()
        self.experiment_name = experiment_name
        self.run_name = run_name or datetime.now().strftime("run_%Y%m%d_%H%M%S")
        self.project = project
        self.log_model = log_model
        self.log_every_epoch = log_every_epoch
        self.auto_log_history = auto_log_history

        self.metadata_store = metadata_store or SQLiteMetadataStore()

        # Initialize experiment
        self.experiment = Experiment(experiment_name)

        # Track params
        self.params_logged = False

        # Training history accumulator
        self.training_history = {
            "epochs": [],
            "train_loss": [],
            "train_accuracy": [],
            "val_loss": [],
            "val_accuracy": [],
        }
        self.custom_metrics = set()

    def on_train_begin(self, logs=None) -> None:
        """Log initial parameters."""
        if not self.params_logged:
            params = {
                "optimizer": str(self.model.optimizer.get_config()),
                "loss": str(self.model.loss),
                "metrics": [str(m) for m in self.model.metrics_names],
                "epochs": self.params.get("epochs"),
                "batch_size": self.params.get("batch_size"),
                "samples": self.params.get("samples"),
            }

            # Log architecture
            model_json = self.model.to_json()

            self.metadata_store.log_experiment_run(
                experiment_id=self.experiment_name,
                run_id=self.run_name,
                parameters=params,
            )

            # Save architecture as artifact
            self.metadata_store.save_artifact(
                artifact_id=f"{self.run_name}_model_arch",
                metadata={
                    "name": "model_architecture",
                    "type": "json",
                    "run_id": self.run_name,
                    "project": self.project,
                    "value": model_json,
                    "created_at": datetime.now().isoformat(),
                },
            )

            self.params_logged = True

    def on_epoch_end(self, epoch, logs=None) -> None:
        """Log metrics at the end of each epoch and accumulate training history."""
        if logs:
            # Log metrics to DB (existing behavior)
            if self.log_every_epoch:
                for k, v in logs.items():
                    self.metadata_store.save_metric(
                        run_id=self.run_name,
                        name=k,
                        value=float(v),
                        step=epoch,
                    )

                # Update experiment run
                self.metadata_store.log_experiment_run(
                    experiment_id=self.experiment_name,
                    run_id=self.run_name,
                    metrics=logs,
                )

            # Accumulate training history (NEW)
            if self.auto_log_history:
                self.training_history["epochs"].append(epoch + 1)  # 1-indexed

                # Standard metrics
                if "loss" in logs:
                    self.training_history["train_loss"].append(float(logs["loss"]))
                if "accuracy" in logs or "acc" in logs:
                    acc_key = "accuracy" if "accuracy" in logs else "acc"
                    self.training_history["train_accuracy"].append(float(logs[acc_key]))
                if "val_loss" in logs:
                    self.training_history["val_loss"].append(float(logs["val_loss"]))
                if "val_accuracy" in logs or "val_acc" in logs:
                    val_acc_key = "val_accuracy" if "val_accuracy" in logs else "val_acc"
                    self.training_history["val_accuracy"].append(float(logs[val_acc_key]))

                # Custom metrics
                for metric_name, value in logs.items():
                    if metric_name not in ["loss", "accuracy", "acc", "val_loss", "val_accuracy", "val_acc"]:
                        if metric_name not in self.custom_metrics:
                            self.custom_metrics.add(metric_name)
                            self.training_history[metric_name] = []
                        self.training_history[metric_name].append(float(value))

    def on_train_end(self, logs=None) -> None:
        """Save model at the end of training with complete training history."""
        if self.log_model:
            # Create artifacts directory
            artifact_dir = Path(f".flowyml/artifacts/{self.run_name}")
            artifact_dir.mkdir(parents=True, exist_ok=True)

            model_path = artifact_dir / "model.keras"
            self.model.save(model_path)

            # Clean up empty history lists
            cleaned_history = {
                k: v
                for k, v in self.training_history.items()
                if v  # Only include non-empty lists
            }

            # Calculate final metrics
            final_metrics = {}
            if "train_loss" in cleaned_history and cleaned_history["train_loss"]:
                final_metrics["loss"] = cleaned_history["train_loss"][-1]
            if "train_accuracy" in cleaned_history and cleaned_history["train_accuracy"]:
                final_metrics["accuracy"] = cleaned_history["train_accuracy"][-1]

            # Save model artifact with training history
            artifact_id = str(uuid.uuid4())
            self.metadata_store.save_artifact(
                artifact_id=artifact_id,
                metadata={
                    "artifact_id": artifact_id,
                    "name": f"model-{self.run_name}",
                    "type": "model",
                    "run_id": self.run_name,
                    "project": self.project,
                    "path": str(model_path.resolve()),
                    "properties": {
                        "framework": "keras",
                        "epochs_trained": len(cleaned_history.get("epochs", [])),
                        "optimizer": str(self.model.optimizer.__class__.__name__),
                        **final_metrics,
                    },
                    "training_history": cleaned_history,  # NEW: UI will display this!
                    "created_at": datetime.now().isoformat(),
                },
            )

"""Keras integration for flowyml.

This module provides seamless integration between Keras and FlowyML,
enabling automatic tracking of training metrics, model artifacts, and
interactive visualization in the FlowyML dashboard.
"""

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

    This callback integrates Keras training with FlowyML's tracking and visualization
    system. It **automatically and dynamically** captures ALL metrics that Keras logs
    during training - no configuration needed!

    Features:
    - **Automatic metric capture**: Whatever metrics you compile your model with
      (loss, accuracy, mae, f1_score, custom metrics) are automatically tracked
    - **Dynamic chart generation**: The UI generates charts for all captured metrics
    - **Real-time updates**: Training progress is visible in the dashboard as it happens
    - **Zero configuration**: Just add the callback and everything works automatically

    Example:
        >>> from flowyml.integrations.keras import FlowymlKerasCallback
        >>>
        >>> # Create callback - that's all you need!
        >>> callback = FlowymlKerasCallback(
        ...     experiment_name="my-experiment",
        ...     project="my-project",
        ... )
        >>>
        >>> # Compile with any metrics you want - they'll all be tracked
        >>> model.compile(
        ...     optimizer="adam",
        ...     loss="mse",
        ...     metrics=["mae", "mape"],  # All automatically captured!
        ... )
        >>>
        >>> # Train with validation data - both train & val metrics captured
        >>> history = model.fit(x_train, y_train, validation_data=(x_val, y_val), epochs=50, callbacks=[callback])
        >>>
        >>> # Get training history for use in your step output
        >>> training_history = callback.get_training_history()

    The training metrics will be visible in the FlowyML dashboard at:
    - Run Details page → Training Metrics section
    - Model artifacts → Training History charts
    """

    def __init__(
        self,
        experiment_name: str,
        run_name: str | None = None,
        project: str | None = None,
        log_model: bool = True,
        log_every_epoch: bool = True,
        auto_log_history: bool = True,
        live_update_interval: int = 1,
        metadata_store: SQLiteMetadataStore | None = None,
    ):
        """Initialize the FlowyML Keras callback.

        Args:
            experiment_name: Name of the experiment for grouping runs.
            run_name: Optional run name (defaults to timestamp-based name).
            project: Project name for organizing runs in the dashboard.
            log_model: Whether to save the model as an artifact after training.
            log_every_epoch: Whether to log metrics to the database every epoch.
            auto_log_history: Whether to automatically collect training history
                for visualization. Highly recommended for dashboard charts.
            live_update_interval: How often (in epochs) to update the live
                training history artifact. Set to 1 for real-time updates.
            metadata_store: Optional metadata store override for custom storage.
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
        self.live_update_interval = live_update_interval

        self.metadata_store = metadata_store or SQLiteMetadataStore()

        # Initialize experiment
        self.experiment = Experiment(experiment_name)

        # Track params
        self.params_logged = False

        # Training history artifact ID (for live updates)
        self._history_artifact_id = f"{self.run_name}_training_history"

        # DYNAMIC training history - only epochs is pre-initialized
        # All other metrics are added dynamically as Keras logs them
        self._training_history = {"epochs": []}

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
        """Dynamically capture ALL metrics at the end of each epoch.

        This method automatically captures whatever metrics Keras logs,
        without requiring any configuration or hardcoded metric names.
        """
        if not logs:
            return

        # Log metrics to DB
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

        # Accumulate training history for visualization
        if self.auto_log_history:
            # Record epoch number (1-indexed for display)
            self._training_history["epochs"].append(epoch + 1)

            # DYNAMICALLY capture ALL metrics from Keras logs
            for metric_name, value in logs.items():
                # Normalize metric name for consistent display
                display_name = self._normalize_metric_name(metric_name)

                # Initialize list if this is a new metric
                if display_name not in self._training_history:
                    self._training_history[display_name] = []

                # Append the value
                self._training_history[display_name].append(float(value))

            # Save live training history artifact for real-time UI updates
            if (epoch + 1) % self.live_update_interval == 0:
                self._save_live_training_history()

    def _normalize_metric_name(self, name: str) -> str:
        """Normalize metric names for consistent display.

        Converts Keras metric names to user-friendly display names:
        - 'loss' -> 'train_loss'
        - 'val_loss' -> 'val_loss' (unchanged)
        - 'mae' -> 'train_mae'
        - 'val_mae' -> 'val_mae' (unchanged)
        - 'accuracy' -> 'train_accuracy'
        - 'acc' -> 'train_accuracy'
        """
        # Validation metrics (val_*) stay as-is
        if name.startswith("val_"):
            return name

        # Special case: 'acc' -> 'train_accuracy'
        if name == "acc":
            return "train_accuracy"

        # Training metrics: add 'train_' prefix for clarity
        if name == "loss":
            return "train_loss"

        # For other metrics (mae, accuracy, custom), add 'train_' prefix
        return f"train_{name}"

    def get_training_history(self) -> dict:
        """Get the accumulated training history for use in step outputs.

        This is the recommended way to include training history in your
        Model asset, ensuring it's linked to the pipeline run.

        Returns:
            dict: Training history with epochs and all captured metrics.
                  Only includes metrics that have data (non-empty lists).

        Example:
            >>> callback = FlowymlKerasCallback(...)
            >>> model.fit(..., callbacks=[callback])
            >>> history = callback.get_training_history()
            >>> return Model.create(
            ...     data=model,
            ...     name="my_model",
            ...     training_history=history,  # Automatically displayed in UI!
            ... )
        """
        # Return cleaned history (only non-empty metrics)
        return {k: v for k, v in self._training_history.items() if v and len(v) > 0}

    def _save_live_training_history(self) -> None:
        """Save current training history as an artifact for live UI updates."""
        cleaned_history = self.get_training_history()

        if not cleaned_history.get("epochs"):
            return  # Nothing to save yet

        # Calculate summary metrics dynamically
        summary_metrics = {}
        for key, values in cleaned_history.items():
            if key == "epochs" or not values:
                continue

            # For loss-like metrics (lower is better)
            if "loss" in key or "mae" in key or "mse" in key or "error" in key.lower():
                summary_metrics[f"final_{key}"] = values[-1]
                summary_metrics[f"best_{key}"] = min(values)
            # For accuracy-like metrics (higher is better)
            elif "accuracy" in key or "acc" in key or "f1" in key or "precision" in key or "recall" in key:
                summary_metrics[f"final_{key}"] = values[-1]
                summary_metrics[f"best_{key}"] = max(values)
            # For other metrics, just store final value
            else:
                summary_metrics[f"final_{key}"] = values[-1]

        # Save/update the training history artifact
        self.metadata_store.save_artifact(
            artifact_id=self._history_artifact_id,
            metadata={
                "artifact_id": self._history_artifact_id,
                "name": f"training-history-{self.experiment_name}",
                "type": "training_history",
                "run_id": self.run_name,
                "project": self.project,
                "properties": {
                    "experiment": self.experiment_name,
                    "epochs_completed": len(cleaned_history.get("epochs", [])),
                    "status": "training",
                    **summary_metrics,
                },
                "training_history": cleaned_history,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
        )

    def on_train_end(self, logs=None) -> None:
        """Save model and finalize training history at the end of training."""
        cleaned_history = self.get_training_history()

        # Calculate final metrics dynamically
        final_metrics = {}
        for key, values in cleaned_history.items():
            if key == "epochs" or not values:
                continue

            # For loss-like metrics
            if "loss" in key or "mae" in key or "mse" in key or "error" in key.lower():
                final_metrics[f"final_{key}"] = values[-1]
                final_metrics[f"best_{key}"] = min(values)
            # For accuracy-like metrics
            elif "accuracy" in key or "acc" in key or "f1" in key:
                final_metrics[f"final_{key}"] = values[-1]
                final_metrics[f"best_{key}"] = max(values)
            else:
                final_metrics[f"final_{key}"] = values[-1]

        # Update training history artifact with final status
        self.metadata_store.save_artifact(
            artifact_id=self._history_artifact_id,
            metadata={
                "artifact_id": self._history_artifact_id,
                "name": f"training-history-{self.experiment_name}",
                "type": "training_history",
                "run_id": self.run_name,
                "project": self.project,
                "properties": {
                    "experiment": self.experiment_name,
                    "epochs_completed": len(cleaned_history.get("epochs", [])),
                    "status": "completed",
                    **final_metrics,
                },
                "training_history": cleaned_history,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
        )

        # Save model artifact if enabled
        if self.log_model:
            # Create artifacts directory
            artifact_dir = Path(f".flowyml/artifacts/{self.run_name}")
            artifact_dir.mkdir(parents=True, exist_ok=True)

            model_path = artifact_dir / "model.keras"
            self.model.save(model_path)

            # Save model artifact with training history attached
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
                    "training_history": cleaned_history,
                    "created_at": datetime.now().isoformat(),
                },
            )

    # Expose training_history as property for backwards compatibility
    @property
    def training_history(self) -> dict:
        """Return the accumulated training history as a dictionary."""
        return self.get_training_history()

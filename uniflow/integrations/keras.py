"""
Keras integration for UniFlow.
"""

import os
import json
import warnings
from typing import Any, Dict, Optional, List
from datetime import datetime

try:
    from tensorflow import keras
except ImportError:
    try:
        import keras
    except ImportError:
        keras = None

from uniflow.tracking.experiment import Experiment
from uniflow.storage.metadata import SQLiteMetadataStore

class UniFlowKerasCallback(keras.callbacks.Callback if keras else object):
    """
    Keras callback for UniFlow tracking.
    
    Automatically logs:
    - Training metrics (loss, accuracy, etc.)
    - Model checkpoints (optional)
    - Model architecture
    - Training parameters
    """
    
    def __init__(
        self,
        experiment_name: str,
        run_name: Optional[str] = None,
        log_model: bool = True,
        log_every_epoch: bool = True,
        metadata_store: Optional[SQLiteMetadataStore] = None
    ):
        """
        Args:
            experiment_name: Name of the experiment
            run_name: Optional run name (defaults to timestamp)
            log_model: Whether to save the model as an artifact
            log_every_epoch: Whether to log metrics every epoch
            metadata_store: Optional metadata store override
        """
        if keras is None:
            raise ImportError("Keras is not installed. Please install tensorflow or keras.")
            
        super().__init__()
        self.experiment_name = experiment_name
        self.run_name = run_name or datetime.now().strftime("run_%Y%m%d_%H%M%S")
        self.log_model = log_model
        self.log_every_epoch = log_every_epoch
        
        self.metadata_store = metadata_store or SQLiteMetadataStore()
        
        # Initialize experiment
        self.experiment = Experiment(experiment_name)
        
        # Track params
        self.params_logged = False
        
    def on_train_begin(self, logs=None):
        """Log initial parameters."""
        if not self.params_logged:
            params = {
                'optimizer': str(self.model.optimizer.get_config()),
                'loss': str(self.model.loss),
                'metrics': [str(m) for m in self.model.metrics_names],
                'epochs': self.params.get('epochs'),
                'batch_size': self.params.get('batch_size'),
                'samples': self.params.get('samples')
            }
            
            # Log architecture
            model_json = self.model.to_json()
            
            self.metadata_store.log_experiment_run(
                experiment_id=self.experiment_name,
                run_id=self.run_name,
                parameters=params
            )
            
            # Save architecture as artifact
            self.metadata_store.save_artifact(
                artifact_id=f"{self.run_name}_model_arch",
                metadata={
                    'name': 'model_architecture',
                    'type': 'json',
                    'run_id': self.run_name,
                    'value': model_json,
                    'created_at': datetime.now().isoformat()
                }
            )
            
            self.params_logged = True

    def on_epoch_end(self, epoch, logs=None):
        """Log metrics at the end of each epoch."""
        if self.log_every_epoch and logs:
            # Log metrics to DB
            for k, v in logs.items():
                self.metadata_store.save_metric(
                    run_id=self.run_name,
                    name=k,
                    value=float(v),
                    step=epoch
                )
            
            # Update experiment run
            self.metadata_store.log_experiment_run(
                experiment_id=self.experiment_name,
                run_id=self.run_name,
                metrics=logs
            )

    def on_train_end(self, logs=None):
        """Save model at the end of training."""
        if self.log_model:
            # Create artifacts directory
            artifact_dir = f".uniflow/artifacts/{self.run_name}"
            os.makedirs(artifact_dir, exist_ok=True)
            
            model_path = f"{artifact_dir}/model.keras"
            self.model.save(model_path)
            
            self.metadata_store.save_artifact(
                artifact_id=f"{self.run_name}_model",
                metadata={
                    'name': 'trained_model',
                    'type': 'keras_model',
                    'run_id': self.run_name,
                    'path': os.path.abspath(model_path),
                    'created_at': datetime.now().isoformat()
                }
            )


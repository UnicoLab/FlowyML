"""
Experiment Tracking - Track ML experiments and compare results.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""
    name: str
    description: str
    tags: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'tags': self.tags,
            'parameters': self.parameters,
            'created_at': self.created_at.isoformat()
        }


class Experiment:
    """
    Experiment for tracking multiple pipeline runs.
    
    Example:
        >>> exp = Experiment(
        ...     name="baseline_training",
        ...     description="Baseline model training"
        ... )
        >>> exp.log_run(run_id, metrics={'accuracy': 0.95})
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        experiment_dir: str = ".flowy/experiments"
    ):
        self.name = name
        self.description = description
        self.config = ExperimentConfig(
            name=name,
            description=description,
            tags=tags or {},
            parameters=parameters or {}
        )
        
        # Storage
        self.experiment_dir = Path(experiment_dir) / name
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata store for UI
        from flowy.storage.metadata import SQLiteMetadataStore
        self.metadata_store = SQLiteMetadataStore()
        
        # Save experiment to DB
        self.metadata_store.save_experiment(
            experiment_id=self.name,
            name=self.name,
            description=self.description,
            tags=tags
        )
        
        # Runs
        self.runs: List[str] = []  # run IDs
        self.run_metrics: Dict[str, Dict[str, Any]] = {}
        
        self._load_experiment()
    
    def log_run(
        self,
        run_id: str,
        metrics: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Log a pipeline run to this experiment.
        
        Args:
            run_id: Run identifier
            metrics: Metrics from the run
            parameters: Parameters used in the run
        """
        if run_id not in self.runs:
            self.runs.append(run_id)
        
        self.run_metrics[run_id] = {
            'metrics': metrics or {},
            'parameters': parameters or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self._save_experiment()
        
        # Log to DB
        self.metadata_store.log_experiment_run(
            experiment_id=self.name,
            run_id=run_id,
            metrics=metrics,
            parameters=parameters
        )
    
    def get_run_metrics(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific run."""
        return self.run_metrics.get(run_id)
    
    def list_runs(self) -> List[str]:
        """List all runs in this experiment."""
        return self.runs
    
    def compare_runs(
        self,
        run_ids: Optional[List[str]] = None,
        metric: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare runs in this experiment.
        
        Args:
            run_ids: Specific runs to compare (or all if None)
            metric: Specific metric to compare (or all if None)
            
        Returns:
            Comparison results
        """
        runs_to_compare = run_ids or self.runs
        
        comparison = {
            'experiment': self.name,
            'runs': {}
        }
        
        for run_id in runs_to_compare:
            if run_id not in self.run_metrics:
                continue
            
            run_data = self.run_metrics[run_id]
            metrics = run_data.get('metrics', {})
            
            if metric:
                comparison['runs'][run_id] = {metric: metrics.get(metric)}
            else:
                comparison['runs'][run_id] = metrics
        
        return comparison
    
    def get_best_run(self, metric: str, maximize: bool = True) -> Optional[str]:
        """
        Get the best run based on a metric.
        
        Args:
            metric: Metric to optimize
            maximize: Whether to maximize (True) or minimize (False)
            
        Returns:
            Best run ID
        """
        best_run = None
        best_value = float('-inf') if maximize else float('inf')
        
        for run_id, run_data in self.run_metrics.items():
            metrics = run_data.get('metrics', {})
            value = metrics.get(metric)
            
            if value is None:
                continue
            
            if maximize and value > best_value:
                best_value = value
                best_run = run_id
            elif not maximize and value < best_value:
                best_value = value
                best_run = run_id
        
        return best_run
    
    def _save_experiment(self):
        """Save experiment data to disk."""
        experiment_file = self.experiment_dir / "experiment.json"
        
        data = {
            'config': self.config.to_dict(),
            'runs': self.runs,
            'run_metrics': self.run_metrics
        }
        
        with open(experiment_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_experiment(self):
        """Load experiment data from disk."""
        experiment_file = self.experiment_dir / "experiment.json"
        
        if not experiment_file.exists():
            return
        
        try:
            with open(experiment_file, 'r') as f:
                data = json.load(f)
            
            self.runs = data.get('runs', [])
            self.run_metrics = data.get('run_metrics', {})
            
        except Exception as e:
            print(f"Warning: Failed to load experiment: {e}")
    
    def __repr__(self) -> str:
        return f"Experiment(name='{self.name}', runs={len(self.runs)})"

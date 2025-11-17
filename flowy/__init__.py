"""
🌊 Flowy - Next-Generation ML Pipeline Framework

Flowy is a developer-first ML pipeline orchestration framework that combines
the simplicity of Metaflow with the power of ZenML and the elegance of 
asset-centric design.
"""

__version__ = "0.1.0"
__author__ = "Flowy Team"

# Core imports
from flowy.core.context import Context, context
from flowy.core.step import step, Step
from flowy.core.pipeline import Pipeline
from flowy.core.executor import Executor, LocalExecutor
from flowy.core.cache import CacheStrategy

# Asset imports
from flowy.assets.base import Asset
from flowy.assets.dataset import Dataset
from flowy.assets.model import Model
from flowy.assets.metrics import Metrics
from flowy.assets.artifact import Artifact
from flowy.assets.registry import AssetRegistry

# Stack imports
from flowy.stacks.base import Stack
from flowy.stacks.local import LocalStack

# Tracking imports
from flowy.tracking.experiment import Experiment
from flowy.tracking.runs import Run

__all__ = [
    # Core
    "Context",
    "context",
    "step",
    "Step",
    "Pipeline",
    "Executor",
    "LocalExecutor",
    "CacheStrategy",
    # Assets
    "Asset",
    "Dataset",
    "Model",
    "Metrics",
    "Artifact",
    "AssetRegistry",
    # Stacks
    "Stack",
    "LocalStack",
    # Tracking
    "Experiment",
    "Run",
]

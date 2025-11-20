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
from flowy.core.conditional import Condition, ConditionalBranch, Switch, when, unless
from flowy.core.parallel import ParallelExecutor, DataParallelExecutor, BatchExecutor, parallel_map
from flowy.core.error_handling import (
    CircuitBreaker,
    ExponentialBackoff,
    RetryConfig,
    FallbackHandler,
    retry,
    on_failure,
)

# Asset imports
from flowy.assets.base import Asset
from flowy.assets.dataset import Dataset
from flowy.assets.model import Model
from flowy.assets.metrics import Metrics
from flowy.assets.artifact import Artifact
from flowy.assets.featureset import FeatureSet
from flowy.assets.report import Report
from flowy.assets.registry import AssetRegistry

# Stack imports
from flowy.stacks.base import Stack
from flowy.stacks.local import LocalStack

# Tracking imports
from flowy.tracking.experiment import Experiment
from flowy.tracking.runs import Run

# Registry imports
from flowy.registry.model_registry import ModelRegistry, ModelVersion, ModelStage

# Storage imports (for advanced usage)
from flowy.storage import (
    ArtifactStore,
    LocalArtifactStore,
    MetadataStore,
    SQLiteMetadataStore,
    materializer_registry,
)

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
    # Conditional & Control Flow
    "Condition",
    "ConditionalBranch",
    "Switch",
    "when",
    "unless",
    # Parallel Execution
    "ParallelExecutor",
    "DataParallelExecutor",
    "BatchExecutor",
    "parallel_map",
    # Error Handling
    "CircuitBreaker",
    "ExponentialBackoff",
    "RetryConfig",
    "FallbackHandler",
    "retry",
    "on_failure",
    # Assets
    "Asset",
    "Dataset",
    "Model",
    "Metrics",
    "Artifact",
    "FeatureSet",
    "Report",
    "AssetRegistry",
    # Stacks
    "Stack",
    "LocalStack",
    # Tracking
    "Experiment",
    "Run",
    # Registry
    "ModelRegistry",
    "ModelVersion",
    "ModelStage",
    # Storage
    "ArtifactStore",
    "LocalArtifactStore",
    "MetadataStore",
    "SQLiteMetadataStore",
    "materializer_registry",
]

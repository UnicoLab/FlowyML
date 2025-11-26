"""
🌊 UniFlow - Next-Generation ML Pipeline Framework

UniFlow is a developer-first ML pipeline orchestration framework that combines
the simplicity of Metaflow with the power of ZenML and the elegance of 
asset-centric design.
"""

__version__ = "0.1.0"
__author__ = "UniFlow Team"

# Core imports
from uniflow.core.context import Context, context
from uniflow.core.step import step, Step
from uniflow.core.pipeline import Pipeline
from uniflow.core.executor import Executor, LocalExecutor
from uniflow.core.cache import CacheStrategy
from uniflow.core.conditional import Condition, ConditionalBranch, Switch, when, unless
from uniflow.core.parallel import ParallelExecutor, DataParallelExecutor, BatchExecutor, parallel_map
from uniflow.core.error_handling import (
    CircuitBreaker,
    ExponentialBackoff,
    RetryConfig,
    FallbackHandler,
    retry,
    on_failure,
)

# Asset imports
from uniflow.assets.base import Asset
from uniflow.assets.dataset import Dataset
from uniflow.assets.model import Model
from uniflow.assets.metrics import Metrics
from uniflow.assets.artifact import Artifact
from uniflow.assets.featureset import FeatureSet
from uniflow.assets.report import Report
from uniflow.assets.registry import AssetRegistry

# Stack imports
from uniflow.stacks.base import Stack
from uniflow.stacks.local import LocalStack

# Tracking imports
from uniflow.tracking.experiment import Experiment
from uniflow.tracking.runs import Run

# Registry imports
from uniflow.registry.model_registry import ModelRegistry, ModelVersion, ModelStage

# Storage imports (for advanced usage)
from uniflow.storage import (
    ArtifactStore,
    LocalArtifactStore,
    MetadataStore,
    SQLiteMetadataStore,
    materializer_registry,
)

# Monitoring & Integrations
from uniflow.monitoring.llm import trace_llm, tracer
from uniflow.monitoring.data import detect_drift, compute_stats
from uniflow.integrations.keras import UniFlowKerasCallback

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
    # Monitoring & Integrations
    "trace_llm",
    "tracer",
    "detect_drift",
    "compute_stats",
    "UniFlowKerasCallback",
]

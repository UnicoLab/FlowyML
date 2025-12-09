"""🌊 flowyml - Next-Generation ML Pipeline Framework.

flowyml is a developer-first ML pipeline orchestration framework that combines
the simplicity of Metaflow with the power of ZenML and the elegance of
asset-centric design.
"""

__version__ = "0.1.0"
__author__ = "flowyml Team"

# Core imports
from flowyml.core.context import Context, context
from flowyml.core.step import step, Step
from flowyml.core.pipeline import Pipeline
from flowyml.core.executor import Executor, LocalExecutor
from flowyml.core.cache import CacheStrategy
from flowyml.core.conditional import Condition, ConditionalBranch, Switch, when, unless, If
from flowyml.core.parallel import ParallelExecutor, DataParallelExecutor, BatchExecutor, parallel_map
from flowyml.core.error_handling import (
    CircuitBreaker,
    ExponentialBackoff,
    RetryConfig,
    FallbackHandler,
    retry,
    on_failure,
)

# Asset imports
from flowyml.assets.base import Asset
from flowyml.assets.dataset import Dataset
from flowyml.assets.model import Model
from flowyml.assets.metrics import Metrics
from flowyml.assets.artifact import Artifact
from flowyml.assets.featureset import FeatureSet
from flowyml.assets.report import Report
from flowyml.assets.registry import AssetRegistry

# Stack imports
from flowyml.stacks.base import Stack
from flowyml.stacks.local import LocalStack
from flowyml.stacks.components import ResourceConfig, DockerConfig

# Tracking imports
from flowyml.tracking.experiment import Experiment
from flowyml.tracking.runs import Run

# Registry imports
from flowyml.registry.model_registry import ModelRegistry, ModelVersion, ModelStage

# Storage imports (for advanced usage)
from flowyml.storage import (
    ArtifactStore,
    LocalArtifactStore,
    MetadataStore,
    SQLiteMetadataStore,
    materializer_registry,
)

# Monitoring & Integrations
from flowyml.monitoring.llm import trace_llm, tracer
from flowyml.monitoring.data import detect_drift, compute_stats
from flowyml.monitoring.notifications import (
    NotificationManager,
    configure_notifications,
    get_notifier,
    ConsoleNotifier,
    SlackNotifier,
    EmailNotifier,
)
from flowyml.integrations.keras import FlowymlKerasCallback

# Advanced Features
from flowyml.core.scheduler import PipelineScheduler
from flowyml.core.approval import approval, ApprovalStep
from flowyml.core.checkpoint import PipelineCheckpoint, checkpoint_enabled_pipeline
from flowyml.core.templates import create_from_template, list_templates, TEMPLATES
from flowyml.tracking.leaderboard import ModelLeaderboard, compare_runs
from flowyml.core.versioning import VersionedPipeline, PipelineVersion
from flowyml.core.project import Project, ProjectManager
from flowyml.core.advanced_cache import (
    ContentBasedCache,
    SharedCache,
    SmartCache,
    memoize,
)
from flowyml.utils.debug import (
    StepDebugger,
    PipelineDebugger,
    debug_step,
    trace_step,
    profile_step,
    inspect_step,
)
from flowyml.utils.performance import (
    LazyValue,
    lazy_property,
    IncrementalComputation,
    GPUResourceManager,
    optimize_dataframe,
    batch_iterator,
)
from flowyml.registry.pipeline_registry import pipeline_registry, register_pipeline

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
    "If",
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
    "ResourceConfig",
    "DockerConfig",
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
    "FlowymlKerasCallback",
    # Advanced Features
    "PipelineScheduler",
    "approval",
    "ApprovalStep",
    "PipelineCheckpoint",
    "checkpoint_enabled_pipeline",
    "create_from_template",
    "list_templates",
    "TEMPLATES",
    "ModelLeaderboard",
    "compare_runs",
    "NotificationManager",
    "configure_notifications",
    "get_notifier",
    "ConsoleNotifier",
    "SlackNotifier",
    "EmailNotifier",
    # Versioning & Projects
    "VersionedPipeline",
    "PipelineVersion",
    "Project",
    "ProjectManager",
    # Advanced Caching
    "ContentBasedCache",
    "SharedCache",
    "SmartCache",
    "memoize",
    # Debugging
    "StepDebugger",
    "PipelineDebugger",
    "debug_step",
    "trace_step",
    "profile_step",
    "inspect_step",
    # Performance
    "LazyValue",
    "lazy_property",
    "ParallelExecutor",
    "IncrementalComputation",
    "GPUResourceManager",
    "optimize_dataframe",
    "batch_iterator",
    # Registry
    "pipeline_registry",
    "register_pipeline",
]

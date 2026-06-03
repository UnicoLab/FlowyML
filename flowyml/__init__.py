"""🌊 flowyml - Next-Generation ML Pipeline Framework.

flowyml is a developer-first ML pipeline orchestration framework that combines
the simplicity of Metaflow with the power of ZenML and the elegance of
asset-centric design.
"""

__version__ = "1.10.0"
__author__ = "flowyml Team"

# Core imports
from flowyml.core.context import Context, context
from flowyml.core.step import step, Step, StepRegistry, get_registered_steps, clear_step_registry
from flowyml.core.pipeline import Pipeline
from flowyml.core.executor import Executor, LocalExecutor
from flowyml.core.cache import CacheStrategy
from flowyml.core.conditional import Condition, ConditionalBranch, Switch, when, unless, If
from flowyml.core.parallel import (
    ParallelExecutor,
    DataParallelExecutor,
    BatchExecutor,
    parallel_map,
)
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
from flowyml.assets.prompt import Prompt
from flowyml.assets.checkpoint import Checkpoint
from flowyml.assets.registry import AssetRegistry

# Stack imports
from flowyml.stacks.base import Stack
from flowyml.stacks.local import LocalStack
from flowyml.stacks.components import ResourceConfig, DockerConfig
from flowyml.stacks import use_stack

# Enterprise Stack imports (optional — gracefully degrade if deps missing)
import contextlib

with contextlib.suppress(ImportError):
    from flowyml.stacks.enterprise import (
        StackDefinition,
        EnterpriseStackRegistry,
        PolicyEngine,
        StackResolver,
    )

with contextlib.suppress(ImportError):
    from flowyml.core.image_builder import DockerImageBuilder

with contextlib.suppress(ImportError):
    from flowyml.core.image_policy import ImagePolicy, ImagePolicyValidator

with contextlib.suppress(ImportError):
    from flowyml.stacks.dockerhub import DockerHubContainerRegistry

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
from flowyml.core.materializers import (
    Materializer,
    materializer_registry as core_materializer_registry,
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

# GenAI Observability Integrations (all optional dependencies)
# -- Base layer (always available, no external deps) --
from flowyml.integrations.base import (
    BaseTracer,
    TraceSession,
    TraceSpan,
    log_embedding_call,
    log_llm_call,
    log_tool_call,
)
from flowyml.integrations.base import observe as observe_genai
from flowyml.integrations.base import trace as trace_genai
from flowyml.integrations.generic import span

import contextlib

# -- LangGraph / LangChain (optional) --
with contextlib.suppress(ImportError):
    from flowyml.integrations.langgraph import (
        FlowyMLCallbackHandler,
        instrument as instrument_graph,
        observe,
        trace_graph,
    )

with contextlib.suppress(ImportError):
    from flowyml.integrations.langchain import (
        instrument_chain,
        observe_chain,
        trace_chain,
    )

# -- OpenAI (optional) --
with contextlib.suppress(ImportError):
    from flowyml.integrations.openai_integration import (
        TracedOpenAI,
        patch_openai,
        trace_openai,
    )

# Advanced Features
from flowyml.core.scheduler import PipelineScheduler
from flowyml.core.approval import approval, ApprovalStep
from flowyml.core.checkpoint import PipelineCheckpoint, checkpoint_enabled_pipeline
from flowyml.core.templates import create_from_template, list_templates, TEMPLATES
from flowyml.tracking.leaderboard import ModelLeaderboard, compare_runs
from flowyml.core.versioning import VersionedPipeline, PipelineVersion, PipelineSnapshot, freeze_pipeline
from flowyml.core.map_task import map_task, MapTaskStep, MapTaskResult
from flowyml.core.dynamic import dynamic, DynamicStep
from flowyml.core.subpipeline import SubPipelineStep, sub_pipeline
from flowyml.storage.catalog import ArtifactCatalog, CatalogBackend, LocalCatalogBackend
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

# Evaluation Framework
from flowyml.evals import (
    evaluate,
    evaluate_traces,
    EvalResult,
    EvalDataset,
    EvalSuite,
    EvalRun,
    EvalAssert,
    EvalStep,
    EvalSchedule,
    JudgeArena,
    TraceBridge,
    Scorer,
    ScorerFeedback,
    make_judge,
    make_scorer,
    get_scorer,
)

__all__ = [
    # Core
    "Context",
    "context",
    "step",
    "Step",
    "StepRegistry",
    "get_registered_steps",
    "clear_step_registry",
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
    "Prompt",
    "Checkpoint",
    "AssetRegistry",
    # Stacks
    "Stack",
    "LocalStack",
    "ResourceConfig",
    "DockerConfig",
    "use_stack",
    # Enterprise Stacks (when available)
    "StackDefinition",
    "EnterpriseStackRegistry",
    "PolicyEngine",
    "StackResolver",
    # Docker Image Builder (when available)
    "DockerImageBuilder",
    "ImagePolicy",
    "ImagePolicyValidator",
    "DockerHubContainerRegistry",
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
    "Materializer",
    "core_materializer_registry",
    # Monitoring & Integrations
    "trace_llm",
    "tracer",
    "detect_drift",
    "compute_stats",
    "FlowymlKerasCallback",
    # GenAI Observability (base — always available)
    "BaseTracer",
    "TraceSession",
    "TraceSpan",
    "trace_genai",
    "observe_genai",
    "log_llm_call",
    "log_tool_call",
    "log_embedding_call",
    "span",
    # GenAI Observability (LangGraph/LangChain — optional)
    "FlowyMLCallbackHandler",
    "trace_graph",
    "observe",
    "instrument_graph",
    "trace_chain",
    "observe_chain",
    "instrument_chain",
    # GenAI Observability (OpenAI — optional)
    "TracedOpenAI",
    "patch_openai",
    "trace_openai",
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
    "PipelineSnapshot",
    "freeze_pipeline",
    "Project",
    "ProjectManager",
    # Map Tasks & Dynamic Workflows
    "map_task",
    "MapTaskStep",
    "MapTaskResult",
    "dynamic",
    "DynamicStep",
    "SubPipelineStep",
    "sub_pipeline",
    # Artifact Catalog
    "ArtifactCatalog",
    "CatalogBackend",
    "LocalCatalogBackend",
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
    # Evaluations
    "evaluate",
    "evaluate_traces",
    "EvalResult",
    "EvalDataset",
    "EvalSuite",
    "EvalRun",
    "EvalAssert",
    "EvalStep",
    "EvalSchedule",
    "JudgeArena",
    "TraceBridge",
    "Scorer",
    "ScorerFeedback",
    "make_judge",
    "make_scorer",
    "get_scorer",
]

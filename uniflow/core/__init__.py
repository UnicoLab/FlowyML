"""Core pipeline execution components."""

from uniflow.core.context import Context, context
from uniflow.core.step import step, Step
from uniflow.core.pipeline import Pipeline
from uniflow.core.executor import Executor, LocalExecutor
from uniflow.core.cache import CacheStrategy
from uniflow.core.conditional import Condition, ConditionalBranch, Switch, when, unless
from uniflow.core.parallel import (
    ParallelExecutor,
    DataParallelExecutor,
    BatchExecutor,
    parallel_map,
    distribute_across_gpus,
)
from uniflow.core.error_handling import (
    CircuitBreaker,
    ExponentialBackoff,
    RetryConfig,
    FallbackHandler,
    retry,
    on_failure,
)
from uniflow.core.resources import (
    ResourceRequirements,
    GPUConfig,
    NodeAffinity,
    resources,
)

__all__ = [
    # Context
    "Context",
    "context",
    # Steps & Pipelines
    "step",
    "Step",
    "Pipeline",
    # Execution
    "Executor",
    "LocalExecutor",
    # Caching
    "CacheStrategy",
    # Conditional Execution
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
    "distribute_across_gpus",
    # Error Handling
    "CircuitBreaker",
    "ExponentialBackoff",
    "RetryConfig",
    "FallbackHandler",
    "retry",
    "on_failure",
    # Resources
    "ResourceRequirements",
    "GPUConfig",
    "NodeAffinity",
    "resources",
]

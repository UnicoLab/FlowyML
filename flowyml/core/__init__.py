"""Core pipeline execution components."""

from flowyml.core.context import Context, context
from flowyml.core.step import step, Step
from flowyml.core.pipeline import Pipeline
from flowyml.core.executor import Executor, LocalExecutor
from flowyml.core.cache import CacheStrategy
from flowyml.core.conditional import Condition, ConditionalBranch, Switch, when, unless
from flowyml.core.parallel import (
    ParallelExecutor,
    DataParallelExecutor,
    BatchExecutor,
    parallel_map,
    distribute_across_gpus,
)
from flowyml.core.error_handling import (
    CircuitBreaker,
    ExponentialBackoff,
    RetryConfig,
    FallbackHandler,
    retry,
    on_failure,
)
from flowyml.core.resources import (
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

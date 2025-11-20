"""Core pipeline execution components."""

from flowy.core.context import Context, context
from flowy.core.step import step, Step
from flowy.core.pipeline import Pipeline
from flowy.core.executor import Executor, LocalExecutor
from flowy.core.cache import CacheStrategy
from flowy.core.conditional import Condition, ConditionalBranch, Switch, when, unless
from flowy.core.parallel import (
    ParallelExecutor,
    DataParallelExecutor,
    BatchExecutor,
    parallel_map,
    distribute_across_gpus,
)
from flowy.core.error_handling import (
    CircuitBreaker,
    ExponentialBackoff,
    RetryConfig,
    FallbackHandler,
    retry,
    on_failure,
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
]
